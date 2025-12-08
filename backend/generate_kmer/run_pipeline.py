"""
Complete pipeline to generate a tailored k-mer dataset from phenotype data.

This script orchestrates:
1. Reading phenotype file to get unique genomes
2. Downloading FASTA files from BV-BRC FTP
3. Running KMC3 to count k-mers
4. Calculating probabilities and saving output

Usage:
    python run_pipeline.py \
        --phenotype ../DATA/BVBRC_genome_amr.txt \
        --output-dir pipeline_output \
        --k 21 \
        --max-genomes 0
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def run_step(description: str, cmd: list, cwd: Path = None) -> bool:
    """Run a command and return success status."""
    logger.info(f"Starting: {description}")
    logger.info(f"Command: {' '.join(str(c) for c in cmd)}")
    
    try:
        result = subprocess.run(
            [str(c) for c in cmd],
            cwd=cwd,
            check=True
        )
        logger.info(f"Completed: {description}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed: {description}")
        logger.error(f"Exit code: {e.returncode}")
        return False
    except FileNotFoundError as e:
        logger.error(f"Command not found: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Complete pipeline to generate tailored k-mer dataset"
    )
    parser.add_argument(
        "--phenotype",
        type=Path,
        required=True,
        help="Path to phenotype file (BVBRC_genome_amr.txt)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("pipeline_output"),
        help="Output directory for all pipeline files"
    )
    parser.add_argument(
        "--k",
        type=int,
        default=21,
        help="K-mer length (default: 21)"
    )
    parser.add_argument(
        "--max-genomes",
        type=int,
        default=0,
        help="Maximum genomes to process (0 = all)"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download step (use existing FASTA files)"
    )
    parser.add_argument(
        "--download-delay",
        type=float,
        default=0.1,
        help="Delay between downloads in seconds"
    )
    parser.add_argument(
        "--min-probability",
        type=float,
        default=0.0,
        help="Minimum k-mer probability to include"
    )
    
    args = parser.parse_args()
    
    # Validate phenotype file
    if not args.phenotype.exists():
        logger.error(f"Phenotype file not found: {args.phenotype}")
        return 1
    
    # Create output directory structure
    args.output_dir.mkdir(parents=True, exist_ok=True)
    genomes_dir = args.output_dir / "genomes"
    genomes_dir.mkdir(exist_ok=True)
    
    # Determine output file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = args.output_dir / f"kmer_dataset_k{args.k}_{timestamp}.txt"
    
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.resolve()
    
    logger.info("=" * 60)
    logger.info("K-mer Generation Pipeline")
    logger.info("=" * 60)
    logger.info(f"Phenotype file: {args.phenotype.resolve()}")
    logger.info(f"Output directory: {args.output_dir.resolve()}")
    logger.info(f"K-mer length: {args.k}")
    logger.info(f"Max genomes: {args.max_genomes if args.max_genomes > 0 else 'all'}")
    logger.info("=" * 60)
    
    # Step 1: Download genomes (unless skipped)
    if not args.skip_download:
        logger.info("\n" + "=" * 40)
        logger.info("STEP 1: Downloading genomes from BV-BRC")
        logger.info("=" * 40)
        
        download_cmd = [
            sys.executable,
            script_dir / "download_genomes.py",
            "--phenotype", args.phenotype,
            "--output-dir", genomes_dir,
            "--delay", str(args.download_delay),
        ]
        
        if args.max_genomes > 0:
            download_cmd.extend(["--max-genomes", str(args.max_genomes)])
        
        if not run_step("Download genomes", download_cmd):
            logger.warning("Download step had errors, continuing with available files...")
    else:
        logger.info("\n" + "=" * 40)
        logger.info("STEP 1: Skipping download (using existing files)")
        logger.info("=" * 40)
    
    # Check we have some FASTA files
    fasta_count = len(list(genomes_dir.glob("*.fna")))
    if fasta_count == 0:
        logger.error(f"No FASTA files found in {genomes_dir}")
        logger.error("Download step may have failed, or --skip-download was used without existing files")
        return 1
    
    logger.info(f"Found {fasta_count:,} FASTA files to process")
    
    # Step 2: Generate k-mers
    logger.info("\n" + "=" * 40)
    logger.info("STEP 2: Generating k-mers with KMC3")
    logger.info("=" * 40)
    
    kmer_cmd = [
        sys.executable,
        script_dir / "generate_kmers.py",
        "--phenotype", args.phenotype,
        "--genomes-dir", genomes_dir,
        "--output", output_file,
        "--k", str(args.k),
        "--min-probability", str(args.min_probability),
    ]
    
    if args.max_genomes > 0:
        kmer_cmd.extend(["--max-genomes", str(args.max_genomes)])
    
    if not run_step("Generate k-mers", kmer_cmd):
        logger.error("K-mer generation failed!")
        return 1
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 60)
    
    if output_file.exists():
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        
        # Count lines (rough k-mer count)
        with open(output_file, "r") as f:
            line_count = sum(1 for _ in f)
        
        logger.info(f"Output file: {output_file}")
        logger.info(f"File size: {file_size_mb:.2f} MB")
        logger.info(f"Total k-mer entries: {line_count:,}")
        
        # Show sample
        logger.info("\nSample output (first 5 lines):")
        with open(output_file, "r") as f:
            for i, line in enumerate(f):
                if i >= 5:
                    break
                logger.info(f"  {line.rstrip()}")
    
    logger.info("=" * 60)
    logger.info("Next steps:")
    logger.info(f"  1. Copy {output_file.name} to your DATA folder")
    logger.info("  2. Update training configuration to use the new k-mer file")
    logger.info("  3. Run training with Taxon ID as the genome identifier")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
