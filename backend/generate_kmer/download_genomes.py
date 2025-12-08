"""
Download genome FASTA files from BV-BRC FTP server.

Uses PATRIC Genome IDs from the phenotype file to download exact genome sequences.
FTP URL pattern: ftp://ftp.bvbrc.org/genomes/{GENOME_ID}/{GENOME_ID}.fna

Usage:
    python download_genomes.py \
        --phenotype ../DATA/BVBRC_genome_amr.txt \
        --output-dir downloaded_genomes \
        --max-genomes 100
"""

import argparse
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from ftplib import FTP_TLS, error_perm
from pathlib import Path
from typing import List, Tuple
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

try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm not installed
    def tqdm(iterable, **kwargs):
        return iterable


def load_unique_genomes(phenotype_file: Path) -> pd.DataFrame:
    """Load phenotype file and extract unique genomes.

    We deduplicate at the *Taxon ID* level so that:
    - Each **Taxon ID** (species) is only processed once, even if it has many
      Genome IDs / isolates and many phenotype rows.
    - For each Taxon ID, we keep a single representative Genome ID to download
      from BV-BRC.

    Args:
        phenotype_file: Path to BVBRC_genome_amr.txt

    Returns:
        DataFrame with one representative Genome ID per Taxon ID
    """
    logger.info(f"Loading phenotype file: {phenotype_file}")
    
    df = pd.read_csv(phenotype_file, sep="\t", dtype=str, low_memory=False)
    
    # Clean up column values (remove quotes)
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip().str.replace('"', '')
    
    # Get required columns
    required_cols = ["Taxon ID", "Genome ID", "Genome Name"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}. Available: {df.columns.tolist()}")
    
    # Extract unique genomes (one row per Taxon ID, with a representative Genome ID)
    unique_genomes = df[required_cols].dropna()
    unique_genomes["Genome ID"] = unique_genomes["Genome ID"].str.strip().str.replace('"', '')
    unique_genomes["Taxon ID"] = unique_genomes["Taxon ID"].str.strip().str.replace('"', '')
    # Drop duplicates by Taxon ID, keeping the first Genome ID seen for each taxon
    unique_genomes = unique_genomes.drop_duplicates(subset=["Taxon ID"])

    logger.info(
        f"Found {len(unique_genomes):,} unique taxa (Taxon IDs), "
        "using one representative Genome ID per taxon"
    )

    return unique_genomes


def download_genome(genome_id: str, output_dir: Path, retry_count: int = 3) -> Tuple[bool, str]:
    """
    Download a single genome FASTA from BV-BRC via FTPS (FTP + TLS).
    
    Args:
        genome_id: PATRIC Genome ID (e.g., "562.144628")
        output_dir: Directory to save the file
        retry_count: Number of retries on failure
        
    Returns:
        Tuple of (success, message)
    """
    # Clean the genome ID
    clean_id = genome_id.strip().replace('"', '')
    
    # Skip if looks invalid
    if not clean_id or clean_id == "nan" or "." not in clean_id:
        return False, f"Invalid genome ID: {genome_id}"
    
    # Remote FTPS path components
    remote_dir = f"/genomes/{clean_id}"
    remote_file = f"{clean_id}.fna"
    output_file = output_dir / f"{clean_id}.fna"

    # Skip if already exists
    if output_file.exists() and output_file.stat().st_size > 0:
        return True, "Already exists"

    # Try to download with retries (new FTPS connection per attempt)
    last_error = None
    for attempt in range(retry_count):
        ftps = None
        try:
            ftps = FTP_TLS()
            # Connect to BV-BRC FTP with explicit TLS (control channel protection)
            ftps.connect("ftp.bvbrc.org", 21, timeout=60)
            ftps.auth()  # upgrade control channel to TLS
            ftps.prot_p()  # protect data channel
            ftps.login()  # anonymous login

            # Change to genome directory and retrieve .fna
            ftps.cwd(remote_dir)
            with open(output_file, "wb") as f:
                ftps.retrbinary(f"RETR {remote_file}", f.write)

            # Verify file was downloaded
            if output_file.exists() and output_file.stat().st_size > 0:
                return True, "Downloaded"
            else:
                last_error = "Downloaded but file is empty"
                # Remove empty file if created
                try:
                    output_file.unlink()
                except OSError:
                    pass
        except error_perm as e:
            # Permanent FTP error (e.g., 550 file not found) – don't bother retrying
            last_error = str(e)[:100]
            break
        except Exception as e:
            last_error = str(e)[:100]
            if attempt < retry_count - 1:
                time.sleep(1)  # Wait before retry
                continue
        finally:
            try:
                if ftps is not None:
                    ftps.quit()
            except Exception:
                pass

    if last_error is None:
        last_error = "Unknown error"

    return False, f"Failed after {retry_count} attempts: {last_error}"
    
    return False, "Unknown error"


def main():
    parser = argparse.ArgumentParser(description="Download genomes from BV-BRC FTP")
    parser.add_argument(
        "--phenotype",
        type=Path,
        required=True,
        help="Path to phenotype file (BVBRC_genome_amr.txt)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("downloaded_genomes"),
        help="Directory to save FASTA files"
    )
    parser.add_argument(
        "--max-genomes",
        type=int,
        default=0,
        help="Maximum number of genomes to download (0 = all)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Delay between downloads in seconds (be polite to server)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum number of parallel download workers (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load unique genomes
    unique_genomes = load_unique_genomes(args.phenotype)
    
    # Limit if requested
    if args.max_genomes > 0:
        unique_genomes = unique_genomes.head(args.max_genomes)
        logger.info(f"Limited to {args.max_genomes} genomes")
    
    # Build list of Genome IDs to download (one per taxon / representative genome)
    genome_ids: List[str] = list(unique_genomes["Genome ID"].dropna().unique())
    total_genomes = len(genome_ids)

    logger.info(f"Starting download of {total_genomes:,} genomes (one per Taxon ID)...")
    logger.info(f"Output directory: {args.output_dir.resolve()}")

    success_count = 0
    skip_count = 0
    fail_count = 0
    failed_ids: List[Tuple[str, str]] = []

    def download_single(genome_id: str) -> Tuple[str, bool, str]:
        """Wrapper for parallel download of a single genome ID."""
        success, message = download_genome(genome_id, args.output_dir)
        # Optional per-download delay to avoid hammering the server too hard
        if args.delay > 0:
            time.sleep(args.delay)
        return genome_id, success, message

    # Parallel download using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as executor:
        futures = {executor.submit(download_single, gid): gid for gid in genome_ids}

        for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading"):
            genome_id, success, message = future.result()

            if success:
                if message == "Already exists":
                    skip_count += 1
                else:
                    success_count += 1
            else:
                fail_count += 1
                failed_ids.append((genome_id, message))

            # Explicit progress logging: how many done and how many left
            processed = success_count + skip_count + fail_count
            remaining = total_genomes - processed
            logger.info(
                f"Progress: {processed}/{total_genomes} completed "
                f"({remaining} remaining)"
            )
    
    # Summary
    logger.info("=" * 50)
    logger.info("Download Summary:")
    logger.info(f"  Successfully downloaded: {success_count:,}")
    logger.info(f"  Already existed (skipped): {skip_count:,}")
    logger.info(f"  Failed: {fail_count:,}")
    logger.info(f"  Total FASTA files: {success_count + skip_count:,}")
    
    if failed_ids:
        # Save failed IDs to file
        failed_file = args.output_dir / "failed_downloads.txt"
        with open(failed_file, "w") as f:
            f.write("genome_id\terror\n")
            for gid, msg in failed_ids:
                f.write(f"{gid}\t{msg}\n")
        logger.info(f"  Failed IDs saved to: {failed_file}")
    
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
