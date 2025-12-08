"""
Generate k-mer dataset from downloaded FASTA files using KMC3.

This script:
1. Reads the phenotype file to get Taxon ID mapping
2. Runs KMC3 on each FASTA file to count k-mers
3. Calculates k-mer probabilities
4. Outputs in the format: taxon_id  Bacteria  k  kmer_sequence  probability

Usage:
    python generate_kmers.py \
        --phenotype ../DATA/BVBRC_genome_amr.txt \
        --genomes-dir downloaded_genomes \
        --output kmer_dataset.txt \
        --k 21
"""

import argparse
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging
import shutil

KMC_CMD = os.environ.get("KMC_CMD", "kmc")
KMC_TOOLS_CMD = os.environ.get("KMC_TOOLS_CMD", "kmc_tools")

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

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable


def check_kmc_installed() -> bool:
    """Check if KMC3 tools are available in PATH."""
    try:
        result = subprocess.run(
            [KMC_CMD, "-h"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def load_genome_metadata(phenotype_file: Path) -> Dict[str, Tuple[str, str]]:
    """
    Load mapping from Genome ID to (Taxon ID, Genome Name).
    
    Args:
        phenotype_file: Path to BVBRC_genome_amr.txt
        
    Returns:
        Dict mapping Genome ID -> (Taxon ID, Genome Name)
    """
    logger.info(f"Loading genome metadata from: {phenotype_file}")
    
    df = pd.read_csv(phenotype_file, sep="\t", dtype=str, low_memory=False)
    
    # Clean up values
    for col in ["Taxon ID", "Genome ID", "Genome Name"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('"', '')
    
    # Build mapping
    metadata = {}
    for _, row in df[["Taxon ID", "Genome ID", "Genome Name"]].drop_duplicates().iterrows():
        genome_id = row["Genome ID"]
        taxon_id = row["Taxon ID"]
        genome_name = row["Genome Name"]
        metadata[genome_id] = (taxon_id, genome_name)
    
    logger.info(f"Loaded metadata for {len(metadata):,} genomes")
    return metadata


def run_kmc(fasta_file: Path, k: int, temp_dir: Path) -> Optional[Path]:
    """
    Run KMC3 to count k-mers in a FASTA file.
    
    Args:
        fasta_file: Path to input FASTA file
        k: K-mer length
        temp_dir: Temporary directory for KMC
        
    Returns:
        Path to KMC output dump file, or None if failed
    """
    genome_id = fasta_file.stem
    kmc_db = temp_dir / f"{genome_id}_kmc"
    dump_file = temp_dir / f"{genome_id}_kmers.txt"
    
    try:
        # Step 1: Count k-mers
        # -k{k}: k-mer length
        # -ci1: minimum count = 1 (include all k-mers)
        # -fm: FASTA multi-line input
        # -cs65535: max count value
        cmd_count = [
            KMC_CMD,
            f"-k{k}",
            "-ci1",
            "-fm",
            "-cs65535",
            str(fasta_file),
            str(kmc_db),
            str(temp_dir)
        ]
        
        result = subprocess.run(
            cmd_count,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout per genome
        )
        
        if result.returncode != 0:
            logger.warning(f"KMC count failed for {genome_id}: {result.stderr[:200]}")
            return None
        
        # Step 2: Dump k-mers to text
        cmd_dump = [
            KMC_TOOLS_CMD,
            "transform",
            str(kmc_db),
            "dump",
            str(dump_file)
        ]
        
        result = subprocess.run(
            cmd_dump,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.warning(f"KMC dump failed for {genome_id}: {result.stderr[:200]}")
            return None
        
        # Clean up KMC database files
        for ext in [".kmc_pre", ".kmc_suf"]:
            db_file = Path(str(kmc_db) + ext)
            if db_file.exists():
                db_file.unlink()
        
        return dump_file
        
    except subprocess.TimeoutExpired:
        logger.warning(f"KMC timed out for {genome_id}")
        return None
    except Exception as e:
        logger.warning(f"KMC error for {genome_id}: {e}")
        return None


def process_kmer_dump(
    dump_file: Path,
    taxon_id: str,
    k: int,
    output_file,
    min_probability: float = 0.0
) -> int:
    """Process KMC dump file and write k-mers with probabilities.

    This implementation avoids loading the whole dump file into a DataFrame.
    Instead it streams the file line-by-line in two passes:
    1) First pass computes the total k-mer count.
    2) Second pass computes probabilities and writes filtered k-mers.
    """

    # First pass: compute total count
    total_kmers = 0
    try:
        with open(dump_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                try:
                    count = int(parts[1])
                except ValueError:
                    continue
                total_kmers += count
    except Exception as e:
        logger.warning(f"Failed to read dump file {dump_file} for total count: {e}")
        return 0

    if total_kmers == 0:
        return 0

    # Second pass: compute probabilities and write
    n_written = 0
    try:
        with open(dump_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                kmer = parts[0]
                try:
                    count = int(parts[1])
                except ValueError:
                    continue

                probability = count / total_kmers
                if probability >= min_probability:
                    # Format: taxon_id  Bacteria  k  kmer_sequence  probability
                    output_file.write(
                        f"{taxon_id}\tBacteria\t{k}\t{kmer}\t{probability:.6e}\n"
                    )
                    n_written += 1
    except Exception as e:
        logger.warning(f"Failed to process dump file {dump_file}: {e}")
        return n_written

    return n_written


def main():
    parser = argparse.ArgumentParser(description="Generate k-mer dataset from FASTA files")
    parser.add_argument(
        "--phenotype",
        type=Path,
        required=True,
        help="Path to phenotype file (for Taxon ID mapping)"
    )
    parser.add_argument(
        "--id-type",
        type=str,
        choices=["genome", "taxon"],
        default="genome",
        help=(
            "How to interpret FASTA filenames: 'genome' (Genome ID, default, "
            "use phenotype metadata to map to Taxon ID) or 'taxon' (filename "
            "stem is the Taxon ID directly, e.g. NCBI pipeline)."
        ),
    )
    parser.add_argument(
        "--genomes-dir",
        type=Path,
        required=True,
        help="Directory containing downloaded FASTA files"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("kmer_dataset.txt"),
        help="Output k-mer dataset file"
    )
    parser.add_argument(
        "--k",
        type=int,
        default=21,
        help="K-mer length (default: 21)"
    )
    parser.add_argument(
        "--min-probability",
        type=float,
        default=0.0,
        help="Minimum k-mer probability to include (default: 0 = all)"
    )
    parser.add_argument(
        "--max-genomes",
        type=int,
        default=0,
        help="Maximum number of genomes to process (0 = all)"
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep temporary KMC files (for debugging)"
    )
    
    args = parser.parse_args()
    
    # Check KMC is installed
    if not check_kmc_installed():
        logger.error("KMC3 is not installed or not in PATH!")
        logger.error("Install with: conda install -c bioconda kmc")
        logger.error("Or download from: https://github.com/refresh-bio/KMC/releases")
        return 1
    
    # Check genomes directory exists
    if not args.genomes_dir.exists():
        logger.error(f"Genomes directory not found: {args.genomes_dir}")
        return 1
    
    # Find FASTA files
    fasta_files = list(args.genomes_dir.glob("*.fna"))
    if not fasta_files:
        fasta_files = list(args.genomes_dir.glob("*.fasta"))
    if not fasta_files:
        fasta_files = list(args.genomes_dir.glob("*.fa"))
    
    if not fasta_files:
        logger.error(f"No FASTA files found in {args.genomes_dir}")
        return 1
    
    logger.info(f"Found {len(fasta_files):,} FASTA files")
    
    # Limit if requested
    if args.max_genomes > 0:
        fasta_files = fasta_files[:args.max_genomes]
        logger.info(f"Limited to {args.max_genomes} genomes")
    
    # Load metadata (only needed when filenames are Genome IDs)
    metadata = {}
    if args.id_type == "genome":
        metadata = load_genome_metadata(args.phenotype)
    else:
        logger.info("Using FASTA filenames as Taxon IDs directly (id-type='taxon')")
    
    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp(prefix="kmc_"))
    logger.info(f"Using temp directory: {temp_dir}")
    
    # Process each genome
    success_count = 0
    fail_count = 0
    total_kmers = 0
    
    try:
        total_genomes = len(fasta_files)
        start_time = time.time()
        with open(args.output, "w") as out_f:
            # No header - matches original format
            
            for idx, fasta_file in enumerate(tqdm(fasta_files, desc="Processing genomes"), start=1):
                genome_id = fasta_file.stem
                genome_start = time.time()
                logger.info(
                    f"[{idx}/{total_genomes}] Processing FASTA {fasta_file.name} (genome_id={genome_id})"
                )

                # Determine taxon_id based on id_type
                if args.id_type == "genome":
                    # Map Genome ID -> Taxon ID using phenotype metadata
                    if genome_id not in metadata:
                        logger.warning(f"No metadata for genome {genome_id}, skipping")
                        fail_count += 1
                        continue

                    taxon_id, genome_name = metadata[genome_id]
                else:
                    # In 'taxon' mode, the FASTA basename is the Taxon ID directly
                    taxon_id = genome_id
                
                # Run KMC
                dump_file = run_kmc(fasta_file, args.k, temp_dir)
                
                if dump_file is None:
                    fail_count += 1
                    continue
                
                # Process and write k-mers
                n_kmers = process_kmer_dump(
                    dump_file,
                    taxon_id,
                    args.k,
                    out_f,
                    args.min_probability
                )
                
                if n_kmers > 0:
                    success_count += 1
                    total_kmers += n_kmers
                else:
                    fail_count += 1

                genome_elapsed = time.time() - genome_start
                total_elapsed = time.time() - start_time
                remaining = total_genomes - idx
                avg_per_genome = total_elapsed / idx if idx > 0 else 0.0
                eta_seconds = remaining * avg_per_genome
                logger.info(
                    f"[{idx}/{total_genomes}] Completed {fasta_file.name} in {genome_elapsed:.1f}s; "
                    f"elapsed {total_elapsed/60:.1f} min, {remaining} genomes remaining, "
                    f"ETA {eta_seconds/60:.1f} min"
                )
                
                # Clean up dump file
                if dump_file.exists():
                    dump_file.unlink()
        
        # Summary
        logger.info("=" * 50)
        logger.info("K-mer Generation Summary:")
        logger.info(f"  Genomes processed successfully: {success_count:,}")
        logger.info(f"  Genomes failed: {fail_count:,}")
        logger.info(f"  Total k-mers written: {total_kmers:,}")
        logger.info(f"  Output file: {args.output.resolve()}")
        logger.info(f"  Output size: {args.output.stat().st_size / (1024*1024):.2f} MB")
        logger.info("=" * 50)
        
    finally:
        # Clean up temp directory
        if not args.keep_temp and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    return 0


if __name__ == "__main__":
    exit(main())
