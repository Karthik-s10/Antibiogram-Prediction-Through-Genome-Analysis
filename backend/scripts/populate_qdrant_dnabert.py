"""
Script to populate Qdrant vector database with DNABERT genome embeddings.
"""
import sys
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from preprocessing.data_preprocessor import DataPreprocessor
from preprocessing.dnabert_processor import DNABERTProcessor
from services.qdrant_service import QdrantService
from services.embedding_service import EmbeddingService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def populate_qdrant_dnabert(phenotype_file: str, kmer_file: str, rosetta_file: str, k: int = 6):
    logger.info("Initializing Qdrant Service...")
    qdrant_service = QdrantService()
    if not qdrant_service.client:
        logger.error("Qdrant client not available! Check your .env configuration.")
        return

    logger.info("Loading files into memory...")
    with open(kmer_file, 'rb') as f:
        kmer_content = f.read()
    
    logger.info("Initializing DNABERT Processor...")
    processor = DNABERTProcessor(k=k, max_length=512)
    genome_to_genes = processor.parse_gene_sequences_from_kmer(kmer_content)
    
    logger.info("Mapping Phenotype Data...")
    preprocessor = DataPreprocessor(rosetta_file=rosetta_file)
    id_mapping = preprocessor.load_id_mapping()
    mapped_pheno_df = preprocessor.load_and_map_phenotypes(phenotype_file, id_mapping)
    
    phenotype_df = mapped_pheno_df[["Genome ID", "Assembly Accession", "Antibiotic", "Resistant Phenotype"]].copy()
    try:
        assembly_metadata = getattr(preprocessor, "assembly_metadata", {}) or {}
    except Exception as e:
        logger.warning(f"Failed to load assembly metadata: {e}")
        assembly_metadata = {}
        
    phenotype_df = phenotype_df.rename(
        columns={
            "Genome ID": "genome_id",
            "Assembly Accession": "assembly_accession",
            "Antibiotic": "antibiotic",
            "Resistant Phenotype": "phenotype",
        }
    )
    
    # Debug print the columns
    logger.info(f"Columns before processor: {list(phenotype_df.columns)}")
    
    # Hard fallback to populate a dummy column if the inner join failed entirely to prevent crash
    if 'genome_id' not in phenotype_df.columns:
        logger.error("CRITICAL: 'genome_id' missing from joined phenotype sheet!")
        if len(phenotype_df.columns) > 0:
            logger.info(f"Fallback: renaming first col '{phenotype_df.columns[0]}' to 'genome_id'")
            phenotype_df = phenotype_df.rename(columns={phenotype_df.columns[0]: 'genome_id'})
        else:
            logger.error("Phenotype DF is entirely empty! Initializing empty 'genome_id'")
            phenotype_df['genome_id'] = []

    if 'antibiotic' not in phenotype_df.columns:
        phenotype_df['antibiotic'] = ''
        
    gene_df = processor.create_gene_dataset(genome_to_genes, phenotype_df)
    unique_genome_ids = gene_df['genome_id'].unique().tolist()
    
    if len(unique_genome_ids) > 3204:
        logger.info(f"Limiting to exactly 3204 genomes as requested (down from {len(unique_genome_ids)})")
        unique_genome_ids = unique_genome_ids[:3204]
        
    logger.info(f"Preparing sequences for {len(unique_genome_ids)} genomes...")
    
    embedding_service = EmbeddingService(device="cpu")
    
    aligned_genome_ids = []
    full_sequences = []
    metadata_list = []
    
    skipped_existing = 0
    for genome_id in unique_genome_ids:
        if qdrant_service.genome_exists(genome_id):
            skipped_existing += 1
            continue
            
        genes_for_genome = genome_to_genes.get(genome_id)
        if not genes_for_genome:
            continue
            
        full_sequence = ''.join(genes_for_genome)
        aligned_genome_ids.append(genome_id)
        full_sequences.append(full_sequence)
        
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
        
        metadata_list.append({
            'model_type': 'transformer_dnabert',
            'k': k,
            'resistance_profile': resistance_profile,
            'n_genes': len(gene_df[gene_df['genome_id'] == genome_id]),
            'species': species_name,
            'organism_name': extra_meta.get('organism_name'),
            'genome_name': extra_meta.get('genome_name'),
            'strain': strain,
        })
        
    logger.info(f"Skipped {skipped_existing} genomes already in Qdrant.")
        
    if aligned_genome_ids:
        logger.info(f"Generating DNABERT embeddings for {len(aligned_genome_ids)} missing sequences...")
        embeddings_list = embedding_service.embed_sequences(full_sequences, batch_size=8)
        embeddings = [np.array(vec, dtype=np.float32) for vec in embeddings_list]
        
        genomes_to_insert = aligned_genome_ids
        embeddings_to_insert = embeddings
        metadata_to_insert = metadata_list
        
        if genomes_to_insert:
            logger.info(f"Uploading {len(genomes_to_insert)} DNABERT embeddings to Qdrant...")
            embeddings_array = np.vstack(embeddings_to_insert).astype(np.float32)
            inserted_count = qdrant_service.batch_insert_embeddings(
                genome_ids=genomes_to_insert,
                embeddings=embeddings_array,
                metadata_list=metadata_to_insert,
            )
            logger.info(f"✅ Successfully inserted {inserted_count} genomes! (Skipped {skipped_existing} existing)")
        else:
            logger.info(f"✅ All {len(aligned_genome_ids)} genomes already exist in Qdrant! Skipping insertion.")
    else:
        logger.warning("No aligned sequences found.")

def main():
    parser = argparse.ArgumentParser(description="Populate Qdrant with DNABERT vectors.")
    parser.add_argument("--phenotype-file", type=str, default="DATA/BVBRC_genome_amr.txt")
    parser.add_argument("--kmer-file", type=str, default="DATA/SIGNIFICANT_DNA_KMERS_BACTERIA")
    parser.add_argument("--rosetta-file", type=str, default="DATA/BVBRC_genome.txt")
    parser.add_argument("--k", type=int, default=6, help="K-mer size for DNABERT (usually 6)")
    
    args = parser.parse_args()
    
    # Assume the script is run from either repo root or backend/ and resolve robustly
    current_cwd = Path.cwd()
    if current_cwd.name == 'backend':
        base_dir = current_cwd.parent
    else:
        base_dir = current_cwd
    phenotype_path = base_dir / args.phenotype_file if not Path(args.phenotype_file).is_absolute() else Path(args.phenotype_file)
    kmer_path = base_dir / args.kmer_file if not Path(args.kmer_file).is_absolute() else Path(args.kmer_file)
    rosetta_path = base_dir / args.rosetta_file if not Path(args.rosetta_file).is_absolute() else Path(args.rosetta_file)
    
    populate_qdrant_dnabert(str(phenotype_path), str(kmer_path), str(rosetta_path), args.k)

if __name__ == "__main__":
    main()
