"""
Script to populate Qdrant vector database with DNABERT bindings directly from raw FASTA 
files, effectively bypassing the KMC3 k-mer extraction pipeline.
"""
import sys
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import argparse
from tqdm import tqdm

# Add backend to path so imports resolve correctly
sys.path.insert(0, str(Path(__file__).parent.parent))

from preprocessing.data_preprocessor import DataPreprocessor
from services.qdrant_service import QdrantService
from services.embedding_service import EmbeddingService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def populate_qdrant_from_fasta(fasta_dir: str, phenotype_file: str, rosetta_file: str):
    logger.info("Initializing Qdrant Service...")
    qdrant_service = QdrantService()
    if not qdrant_service.client:
        logger.error("Qdrant client not available! Check your .env configuration.")
        return

    logger.info("Mapping Phenotype Data...")
    preprocessor = DataPreprocessor(rosetta_file=rosetta_file)
    id_mapping = preprocessor.load_id_mapping()
    mapped_pheno_df = preprocessor.load_and_map_phenotypes(phenotype_file, id_mapping)
    
    phenotype_df = mapped_pheno_df[["Assembly Accession", "Antibiotic", "Resistant Phenotype"]].copy()
    try:
        assembly_metadata = getattr(preprocessor, "assembly_metadata", {}) or {}
    except Exception as e:
        logger.warning(f"Failed to load assembly metadata: {e}")
        assembly_metadata = {}
        
    phenotype_df = phenotype_df.rename(
        columns={
            "Assembly Accession": "genome_id",
            "Antibiotic": "antibiotic",
            "Resistant Phenotype": "phenotype",
        }
    )

    fasta_path = Path(fasta_dir)
    fasta_files = list(fasta_path.glob("*.fna"))
    
    if not fasta_files:
        logger.error(f"No .fna files found in {fasta_dir}")
        return

    logger.info(f"Found {len(fasta_files)} FASTA files to process.")
    
    # We force CPU for DNABERT generation to match the exact same pipeline used
    # prior to training to avoid GPU OOM crashes or contention
    embedding_service = EmbeddingService(device="cpu")
    
    batch_size = 8
    genomes_to_insert = []
    embeddings_to_insert = []
    metadata_to_insert = []
    skipped_existing = 0
    inserted_count_total = 0
    
    # Process and upload in batches to avoid holding thousands of massive vectors in RAM
    for idx, fasta_file in enumerate(tqdm(fasta_files, desc="Embedding FASTAs")):
        genome_id = fasta_file.stem  # e.g., '1004310.3' from '1004310.3.fna'
        
        # We need to test if the Qdrant DB already has this ID to avoid wasted compute
        if qdrant_service.genome_exists(genome_id):
            skipped_existing += 1
            continue

        try:
            # Generate the 768-dim sliding window embedding across the entire genome
            embedding = embedding_service.embed_fasta_file(str(fasta_file))
            if not any(embedding): # catches [0.0]*768 edge cases
                logger.warning(f"Failed to extract valid embedding for {genome_id}, skipping.")
                continue
                
            genomes_to_insert.append(genome_id)
            embeddings_to_insert.append(np.array(embedding, dtype=np.float32))
            
            # Map up the resistance profile
            genome_phenotypes = phenotype_df[phenotype_df['genome_id'] == genome_id]
            resistance_profile = {}
            for _, row in genome_phenotypes.iterrows():
                antibiotic = row.get('antibiotic', '')
                phenotype = row.get('phenotype', '')
                if antibiotic and not pd.isna(phenotype):
                    resistance_profile[antibiotic] = str(phenotype)
                    
            extra_meta = assembly_metadata.get(genome_id, {})
            species_name = extra_meta.get('organism_name') or extra_meta.get('genome_name')
            strain = extra_meta.get('strain')
            
            metadata_to_insert.append({
                'model_type': 'transformer_dnabert',
                'source': 'direct_fasta', # Denotes that this bypassed KMC
                'resistance_profile': resistance_profile,
                'species': species_name,
                'organism_name': extra_meta.get('organism_name'),
                'genome_name': extra_meta.get('genome_name'),
                'strain': strain,
            })
            
            # Batch upload every 8 vectors
            if len(genomes_to_insert) >= batch_size:
                embeddings_array = np.vstack(embeddings_to_insert).astype(np.float32)
                inserted = qdrant_service.batch_insert_embeddings(
                    genome_ids=genomes_to_insert,
                    embeddings=embeddings_array,
                    metadata_list=metadata_to_insert,
                )
                inserted_count_total += inserted
                
                # Clear batch
                genomes_to_insert = []
                embeddings_to_insert = []
                metadata_to_insert = []

        except Exception as e:
            logger.error(f"Error processing {genome_id}: {e}")
            continue
            
    # Upload any remaining in the final partial batch
    if genomes_to_insert:
        embeddings_array = np.vstack(embeddings_to_insert).astype(np.float32)
        inserted = qdrant_service.batch_insert_embeddings(
            genome_ids=genomes_to_insert,
            embeddings=embeddings_array,
            metadata_list=metadata_to_insert,
        )
        inserted_count_total += inserted
        
    logger.info(f"✅ Finished! Uploaded {inserted_count_total} new genome vectors. (Skipped {skipped_existing} existing)")


def main():
    parser = argparse.ArgumentParser(description="Populate Qdrant directly from FASTA files.")
    parser.add_argument("--fasta-dir", type=str, default="downloaded_genomes", help="Directory with .fna files")
    parser.add_argument("--phenotype-file", type=str, default="DATA/BVBRC_genome_amr.txt")
    parser.add_argument("--rosetta-file", type=str, default="DATA/BVBRC_genome.txt")
    
    args = parser.parse_args()
    
    # Path resolution based on execution context
    current_cwd = Path.cwd()
    if current_cwd.name == 'backend':
        base_dir = current_cwd.parent
    else:
        base_dir = current_cwd
        
    fasta_path = base_dir / "backend" / args.fasta_dir if not Path(args.fasta_dir).is_absolute() and "backend" not in args.fasta_dir else Path(args.fasta_dir)
    phenotype_path = base_dir / args.phenotype_file if not Path(args.phenotype_file).is_absolute() else Path(args.phenotype_file)
    rosetta_path = base_dir / args.rosetta_file if not Path(args.rosetta_file).is_absolute() else Path(args.rosetta_file)
    
    populate_qdrant_from_fasta(str(fasta_path), str(phenotype_path), str(rosetta_path))

if __name__ == "__main__":
    main()
