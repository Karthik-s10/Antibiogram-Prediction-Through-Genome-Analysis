"""
Estimate the size of the k-mer dataset that will be generated.

This script analyzes the phenotype file to show:
- Number of unique genomes to download
- Estimated download size
- Estimated k-mer count (based on typical genome sizes)

Usage:
    python estimate_dataset.py --phenotype ../DATA/BVBRC_genome_amr.txt
"""

import argparse
from pathlib import Path
from collections import Counter
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

try:
    import pandas as pd
except ImportError:
    logger.error("pandas is required. Install with: pip install pandas")
    raise


def main():
    parser = argparse.ArgumentParser(description="Estimate k-mer dataset size")
    parser.add_argument(
        "--phenotype",
        type=Path,
        required=True,
        help="Path to phenotype file (BVBRC_genome_amr.txt)"
    )
    parser.add_argument(
        "--k",
        type=int,
        default=21,
        help="K-mer length (default: 21)"
    )
    
    args = parser.parse_args()
    
    if not args.phenotype.exists():
        logger.error(f"Phenotype file not found: {args.phenotype}")
        return 1
    
    logger.info(f"Analyzing phenotype file: {args.phenotype}")
    
    # Load phenotype data
    df = pd.read_csv(args.phenotype, sep="\t", dtype=str, low_memory=False)
    
    # Clean columns
    for col in ["Taxon ID", "Genome ID", "Genome Name"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('"', '')
    
    # Get unique genomes
    unique_genomes = df[["Taxon ID", "Genome ID", "Genome Name"]].drop_duplicates().dropna()
    
    # Count by species (Taxon ID)
    taxon_counts = Counter(unique_genomes["Taxon ID"])
    
    # Typical bacterial genome sizes (in base pairs)
    # E. coli: ~5 million bp
    # M. tuberculosis: ~4.4 million bp
    # S. aureus: ~2.8 million bp
    # Average: ~4 million bp
    AVG_GENOME_SIZE_BP = 4_000_000
    
    # Estimate k-mers per genome
    # For a genome of length L, there are approximately (L - k + 1) k-mers
    # But many are duplicates, so unique count is typically 60-80% of total
    est_kmers_per_genome = int((AVG_GENOME_SIZE_BP - args.k + 1) * 0.7)
    
    # Typical FASTA file size (compressed genome is ~1-2 MB)
    AVG_FASTA_SIZE_MB = 1.5
    
    logger.info("=" * 60)
    logger.info("DATASET ESTIMATION")
    logger.info("=" * 60)
    
    logger.info(f"\n--- Phenotype Data ---")
    logger.info(f"Total phenotype records: {len(df):,}")
    logger.info(f"Unique genomes (Genome IDs): {len(unique_genomes):,}")
    logger.info(f"Unique species (Taxon IDs): {len(taxon_counts):,}")
    
    # Top species
    logger.info(f"\n--- Top 10 Species by Genome Count ---")
    for taxon_id, count in taxon_counts.most_common(10):
        # Try to get a genome name for this taxon
        sample_name = unique_genomes[unique_genomes["Taxon ID"] == taxon_id]["Genome Name"].iloc[0]
        species = sample_name.split(" strain")[0] if " strain" in sample_name else sample_name[:50]
        logger.info(f"  Taxon {taxon_id}: {count:,} genomes ({species})")
    
    n_genomes = len(unique_genomes)
    
    logger.info(f"\n--- Download Estimates ---")
    logger.info(f"FASTA files to download: {n_genomes:,}")
    logger.info(f"Estimated download size: {n_genomes * AVG_FASTA_SIZE_MB:.1f} MB ({n_genomes * AVG_FASTA_SIZE_MB / 1024:.2f} GB)")
    logger.info(f"Estimated download time (1 MB/s): {n_genomes * AVG_FASTA_SIZE_MB / 60:.1f} minutes")
    
    logger.info(f"\n--- K-mer Estimates (k={args.k}) ---")
    total_est_kmers = n_genomes * est_kmers_per_genome
    logger.info(f"Estimated unique k-mers per genome: ~{est_kmers_per_genome:,}")
    logger.info(f"Estimated total k-mer entries: ~{total_est_kmers:,}")
    
    # Estimate output file size
    # Each line: "taxon_id\tBacteria\t21\tKMER_SEQUENCE\tPROBABILITY\n"
    # Approx: 6 + 1 + 8 + 1 + 2 + 1 + 21 + 1 + 10 + 1 = ~52 bytes per line
    est_output_size_mb = (total_est_kmers * 52) / (1024 * 1024)
    est_output_size_gb = est_output_size_mb / 1024
    
    logger.info(f"Estimated output file size: {est_output_size_mb:.0f} MB ({est_output_size_gb:.2f} GB)")
    
    logger.info(f"\n--- Processing Time Estimates ---")
    # KMC3 processes ~1 genome per second on average hardware
    est_kmc_time_min = n_genomes / 60
    logger.info(f"Estimated KMC processing time: ~{est_kmc_time_min:.0f} minutes ({est_kmc_time_min/60:.1f} hours)")
    
    logger.info("=" * 60)
    
    # Recommendations
    logger.info("\n--- Recommendations ---")
    
    if n_genomes > 10000:
        logger.info("⚠️  Large dataset! Consider:")
        logger.info("   - Running on a server with more disk space")
        logger.info("   - Using --max-genomes to test with a subset first")
        logger.info("   - Ensure you have at least {:.1f} GB free disk space".format(
            (n_genomes * AVG_FASTA_SIZE_MB + est_output_size_mb) / 1024
        ))
    elif n_genomes > 1000:
        logger.info("📊 Medium dataset. Should be manageable on a workstation.")
        logger.info(f"   Estimated total time: {(n_genomes * 1.5 / 60 + est_kmc_time_min):.0f} minutes")
    else:
        logger.info("✅ Small dataset. Should complete quickly.")
    
    logger.info("\nTo run with a test subset first:")
    logger.info(f"  python run_pipeline.py --phenotype {args.phenotype} --max-genomes 10 --k {args.k}")
    
    logger.info("\nTo run the full pipeline:")
    logger.info(f"  python run_pipeline.py --phenotype {args.phenotype} --k {args.k}")
    
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
