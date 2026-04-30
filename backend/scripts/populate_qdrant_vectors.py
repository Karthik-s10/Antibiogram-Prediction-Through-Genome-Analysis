"""
Script to populate Qdrant vector database with genome embeddings without training a model.

This script parses the k-mer files and phenotype files using the standard DataPreprocessor,
generates the 768-dimensional embeddings using PCA (identical to the training jobs),
and inserts them into the Qdrant DB.
"""

import sys
import logging
from pathlib import Path
import numpy as np
import argparse

# Add backend to path so imports resolve correctly
sys.path.insert(0, str(Path(__file__).parent.parent))

from preprocessing.data_preprocessor import DataPreprocessor
from services.qdrant_service import QdrantService
from jobs.training_job import _generate_embeddings_from_features

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def populate_qdrant(phenotype_file: str, kmer_file: str, rosetta_file: str):
    logger.info("Initializing Qdrant Service...")
    qdrant_service = QdrantService()
    if not qdrant_service.client:
        logger.error("Qdrant client not available! Check your .env configuration.")
        return

    logger.info("Step 1: Parsing Data (this may take a minute for large files)...")
    preprocessor = DataPreprocessor(rosetta_file=rosetta_file)
    X_final, Y_final, _summary = preprocessor.preprocess_data(
        phenotype_file=phenotype_file,
        kmer_file=kmer_file,
        use_cache=False,
        save_cache=False,
        use_taxon_id=True
    )
    
    aligned_genome_ids = list(X_final.index)
    antibiotic_names = list(Y_final.columns)
    
    logger.info(f"Parsed {len(aligned_genome_ids)} genomes across {len(antibiotic_names)} antibiotics.")

    logger.info("Step 2: Generating Embeddings via PCA algorithm...")
    X_aligned_np = X_final.values.astype("float32")
    # Impute NaNs BEFORE PCA — sklearn's PCA cannot handle NaN natively
    nan_mask = np.isnan(X_aligned_np)
    if nan_mask.any():
        col_means = np.nanmean(X_aligned_np, axis=0)
        col_means = np.where(np.isnan(col_means), 0.0, col_means)
        inds = np.where(nan_mask)
        X_aligned_np[inds] = np.take(col_means, inds[1])
        logger.info(f"  Imputed {nan_mask.sum()} NaN values in feature matrix before PCA.")
    embeddings = _generate_embeddings_from_features(X_aligned_np, target_dim=768)

    # Safety: clean any residual NaNs/Infs to prevent Qdrant serialization errors
    embeddings = np.nan_to_num(embeddings, nan=0.0, posinf=0.0, neginf=0.0)

    assembly_metadata = getattr(preprocessor, "assembly_metadata", {}) or {}

    logger.info("Step 3: Checking which genomes already exist in Qdrant (bulk scroll)...")
    existing_point_ids = qdrant_service.get_all_existing_ids()
    logger.info(f"  → {len(existing_point_ids)} points already in Qdrant. Will skip those.")

    genomes_to_insert = []
    embeddings_to_insert = []
    metadata_to_insert = []
    skipped_existing = 0


    for genome_idx, genome_id in enumerate(aligned_genome_ids):
        point_id = qdrant_service._stable_point_id(genome_id)
        if point_id in existing_point_ids:
            skipped_existing += 1
            continue

        # Compile resistance profile JSON format
        resistance_profile = {}
        for i, ab in enumerate(antibiotic_names):
            label = Y_final.values[genome_idx, i]
            if not np.isnan(label) and label != -1:
                res_map = {0: 'S', 1: 'I', 2: 'R'}
                resistance_profile[ab] = res_map.get(int(label), 'Unknown')

        extra_meta = assembly_metadata.get(genome_id, {})
        species_name = extra_meta.get("organism_name") or extra_meta.get("genome_name")

        metadata_list = {
            'model_type': 'database_seed',
            'resistance_profile': resistance_profile,
            'n_antibiotics': len(antibiotic_names),
            'species': species_name,
            'organism_name': extra_meta.get('organism_name'),
            'genome_name': extra_meta.get('genome_name'),
            'strain': extra_meta.get('strain')
        }

        genomes_to_insert.append(genome_id)
        embeddings_to_insert.append(embeddings[genome_idx])
        metadata_to_insert.append(metadata_list)

    if genomes_to_insert:
        logger.info(f"Step 4: Uploading {len(genomes_to_insert)} new embeddings to Qdrant cluster... (skipping {skipped_existing} already-uploaded)")
        embeddings_array = np.vstack(embeddings_to_insert).astype(np.float32)
        inserted_count = qdrant_service.batch_insert_embeddings(
            genome_ids=genomes_to_insert,
            embeddings=embeddings_array,
            metadata_list=metadata_to_insert
        )
        logger.info(f"✅ Successfully inserted {inserted_count} new genomes into Qdrant! (Skipped {skipped_existing} existing ones)")
    else:
        logger.info(f"✅ All {len(aligned_genome_ids)} genomes already exist in Qdrant! Nothing to insert.")
        

def main():
    parser = argparse.ArgumentParser(description="Populate Qdrant with genome vectors.")
    parser.add_argument("--phenotype-file", type=str, default="DATA/BVBRC_genome_amr.txt", help="Path to BVBRC AMR phenotypes file (relative to project root or absolute)")
    parser.add_argument("--kmer-file", type=str, default="DATA/kmer_dataset_taxon_k10_p1e-5_all.txt", help="Path to k-mers file (relative to project root or absolute)")
    parser.add_argument("--rosetta-file", type=str, default="DATA/BVBRC_genome.txt", help="Path to Rosetta mapping file (relative to project root or absolute)")

    args = parser.parse_args()

    # Resolve relative paths from cwd (project root), not from the script directory
    def resolve(p: str) -> Path:
        pp = Path(p)
        return pp if pp.is_absolute() else Path.cwd() / pp

    phenotype_path = resolve(args.phenotype_file)
    kmer_path = resolve(args.kmer_file)
    rosetta_path = resolve(args.rosetta_file)

    populate_qdrant(str(phenotype_path), str(kmer_path), str(rosetta_path))

if __name__ == "__main__":
    main()
