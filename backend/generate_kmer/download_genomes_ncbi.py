"""
Download genome FASTA files from NCBI Datasets API.

This script mirrors the behavior of download_genomes.py (BV-BRC version), but
uses NCBI Datasets instead:

- Reads BVBRC_genome_amr.txt to get phenotype data
- Deduplicates at the Taxon ID level (one genome per species)
- For each Taxon ID, finds a representative assembly via NCBI Datasets
- Downloads the genome FASTA via NCBI Datasets /genome/download endpoint
- Saves FASTA as {taxon_id}.fna in the output directory
- Uses ThreadPoolExecutor for parallel downloads

Requirements:
    pip install pandas tqdm requests

NCBI API key:
    - Pass via --ncbi-api-key argument, or
    - Set NCBI_API_KEY environment variable

Usage (test with 10 taxa):
    python download_genomes_ncbi.py \
        --phenotype ../../DATA/BVBRC_genome_amr.txt \
        --output-dir ncbi_genomes_by_taxon_test10 \
        --max-taxa 10 \
        --max-workers 10
"""

import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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
    def tqdm(iterable, **kwargs):
        return iterable

try:
    import requests
except ImportError:
    logger.error("requests is required. Install with: pip install requests")
    raise


NCBI_DATASETS_BASE_URL = "https://api.ncbi.nlm.nih.gov/datasets/v2alpha"


def load_unique_taxa(phenotype_file: Path) -> pd.DataFrame:
    """Load phenotype file and extract unique taxa.

    - Deduplicate at the Taxon ID level
    - Keep one representative Genome ID / Genome Name per Taxon ID
    """
    logger.info(f"Loading phenotype file: {phenotype_file}")

    df = pd.read_csv(phenotype_file, sep="\t", dtype=str, low_memory=False)

    # Clean up column values (remove quotes, whitespace)
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip().str.replace('"', '')

    required_cols = ["Taxon ID", "Genome ID", "Genome Name"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. Available: {df.columns.tolist()}"
        )

    taxa = df[required_cols].dropna()
    taxa["Taxon ID"] = taxa["Taxon ID"].str.strip().str.replace('"', '')
    taxa["Genome ID"] = taxa["Genome ID"].str.strip().str.replace('"', '')

    # One representative row per Taxon ID
    taxa_unique = taxa.drop_duplicates(subset=["Taxon ID"])

    logger.info(
        f"Found {len(taxa_unique):,} unique taxa (Taxon IDs), "
        "using one representative Genome ID per taxon"
    )

    return taxa_unique


def get_best_assembly_for_taxon(
    taxon_id: str,
    api_key: Optional[str] = None,
    timeout: int = 60,
) -> Optional[str]:
    """Query NCBI Datasets to get a representative assembly accession for a taxon.

    Strategy:
    - Use /genome/dataset_report with taxons=[taxon_id]
    - Filter to RefSeq, complete genomes, non-atypical
    - Pick the first assembly accession from the results
    """
    url = f"{NCBI_DATASETS_BASE_URL}/genome/dataset_report"

    # Build request body
    request_data = {
        "taxons": [taxon_id],
        "filters": {
            "source_database": ["RefSeq"],
            "assembly_level": ["Complete Genome"],
            "exclude_paired_reports": True,
            "exclude_atypical": True,
        },
        "returned_content": "COMPLETE",
        "page_size": 5,
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if api_key:
        headers["api-key"] = api_key

    try:
        resp = requests.post(url, json=request_data, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            logger.warning(
                f"Taxon {taxon_id}: dataset_report HTTP {resp.status_code}: {resp.text[:200]}"
            )
            return None

        data = resp.json()

        # Normalize to a list of assembly reports
        reports: List[dict] = []
        if isinstance(data, dict):
            if "reports" in data and isinstance(data["reports"], list):
                reports = data["reports"]
            elif "assemblies" in data and isinstance(data["assemblies"], list):
                reports = data["assemblies"]
            elif "assemblies_by_taxid" in data:
                assemblies_data = list((data.get("assemblies_by_taxid") or {}).values())
                for tax_data in assemblies_data:
                    reports.extend(tax_data.get("assemblies", []))
            elif "assemblies_by_accession" in data:
                reports = list((data.get("assemblies_by_accession") or {}).values())

        if not reports:
            logger.warning(f"Taxon {taxon_id}: no assemblies found in dataset_report")
            return None

        # Pick the first assembly with a valid accession
        for rep in reports:
            accession = (
                rep.get("accession")
                or rep.get("current_accession")
                or rep.get("assembly_info", {}).get("assembly_accession")
            )
            if accession:
                return accession

        logger.warning(f"Taxon {taxon_id}: assemblies found but no accession field")
        return None

    except Exception as e:
        logger.warning(f"Taxon {taxon_id}: error in dataset_report: {e}")
        return None


def download_genome_from_ncbi(
    taxon_id: str,
    assembly_accession: str,
    output_dir: Path,
    api_key: Optional[str] = None,
    retry_count: int = 3,
) -> Tuple[bool, str]:
    """Download genome FASTA for a given assembly accession via NCBI Datasets.

    - Uses POST /genome/download
    - Saves FASTA as {taxon_id}.fna in output_dir
    - Handles ZIP responses by extracting the best FASTA file
    """
    import io
    import zipfile

    taxon_id_str = str(taxon_id).strip()
    if not taxon_id_str or taxon_id_str.lower() == "nan":
        return False, f"Invalid taxon_id: {taxon_id}"

    output_file = output_dir / f"{taxon_id_str}.fna"

    # Skip if already exists
    if output_file.exists() and output_file.stat().st_size > 0:
        return True, "Already exists"

    url = f"{NCBI_DATASETS_BASE_URL}/genome/download"

    request_data = {
        "accessions": [assembly_accession],
        "include_annotation_type": ["GENOME_FASTA"],
        "filename": f"{assembly_accession}_genome.fasta",
        "format": "fasta",
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/zip, text/plain, application/octet-stream",
    }
    if api_key:
        headers["api-key"] = api_key

    last_error = None

    for attempt in range(retry_count):
        try:
            resp = requests.post(
                url,
                json=request_data,
                headers=headers,
                timeout=120,
            )
            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                if attempt < retry_count - 1:
                    time.sleep(2)
                    continue
                break

            content_type = resp.headers.get("content-type", "")

            # If ZIP, extract FASTA
            if "zip" in content_type.lower():
                try:
                    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                        fasta_candidates = [
                            name
                            for name in zf.namelist()
                            if name.endswith(".fasta")
                            or name.endswith(".fa")
                            or name.endswith(".fna")
                            or "genomic.fna" in name
                        ]
                        if not fasta_candidates:
                            last_error = "ZIP has no FASTA files"
                            continue

                        # Just pick the first candidate
                        fasta_name = sorted(fasta_candidates)[0]
                        with zf.open(fasta_name) as f_in, open(
                            output_file, "wb"
                        ) as f_out:
                            f_out.write(f_in.read())
                except Exception as ze:
                    last_error = f"ZIP error: {ze}"
                    if attempt < retry_count - 1:
                        time.sleep(2)
                        continue
                    break
            else:
                # Assume direct FASTA/plain text
                with open(output_file, "wb") as f_out:
                    f_out.write(resp.content)

            if output_file.exists() and output_file.stat().st_size > 0:
                return True, "Downloaded"
            else:
                last_error = "Downloaded but file is empty"
                try:
                    output_file.unlink()
                except OSError:
                    pass
                if attempt < retry_count - 1:
                    time.sleep(2)
                    continue
                break

        except Exception as e:
            last_error = str(e)
            if attempt < retry_count - 1:
                time.sleep(2)
                continue
            break

    if last_error is None:
        last_error = "Unknown error"

    return False, f"Failed after {retry_count} attempts: {last_error[:200]}"


def main():
    parser = argparse.ArgumentParser(
        description="Download genomes from NCBI Datasets (one per Taxon ID)"
    )
    parser.add_argument(
        "--phenotype",
        type=Path,
        required=True,
        help="Path to phenotype file (BVBRC_genome_amr.txt)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("ncbi_genomes_by_taxon"),
        help="Directory to save FASTA files",
    )
    parser.add_argument(
        "--max-taxa",
        type=int,
        default=0,
        help="Maximum number of taxa to download (0 = all)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Delay between downloads in seconds (per worker)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum number of parallel download workers (default: 10)",
    )
    parser.add_argument(
        "--ncbi-api-key",
        type=str,
        default=None,
        help="NCBI API key (overrides NCBI_API_KEY env var)",
    )

    args = parser.parse_args()

    api_key = args.ncbi_api_key or os.environ.get("NCBI_API_KEY")
    if not api_key:
        logger.warning(
            "No NCBI API key provided. You may hit rate limits. "
            "Set NCBI_API_KEY env var or use --ncbi-api-key."
        )

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Load unique taxa
    taxa_df = load_unique_taxa(args.phenotype)

    if args.max_taxa > 0:
        taxa_df = taxa_df.head(args.max_taxa)
        logger.info(f"Limited to {args.max_taxa} taxa")

    taxon_ids: List[str] = list(taxa_df["Taxon ID"].dropna().unique())
    total_taxa = len(taxon_ids)

    logger.info(f"Starting download for {total_taxa:,} taxa (one genome per Taxon ID)...")
    logger.info(f"Output directory: {args.output_dir.resolve()}")

    success_count = 0
    skip_count = 0
    fail_count = 0
    failed_ids: List[Tuple[str, str]] = []

    # Cache Taxon ID -> assembly accession so we don't re-query in case of retries
    assembly_cache: Dict[str, Optional[str]] = {}

    def download_single(taxon_id: str) -> Tuple[str, bool, str]:
        # Look up assembly accession
        if taxon_id not in assembly_cache:
            assembly = get_best_assembly_for_taxon(taxon_id, api_key=api_key)
            assembly_cache[taxon_id] = assembly
        else:
            assembly = assembly_cache[taxon_id]

        if not assembly:
            return taxon_id, False, "No assembly accession found via NCBI Datasets"

        ok, msg = download_genome_from_ncbi(
            taxon_id,
            assembly,
            args.output_dir,
            api_key=api_key,
        )

        if args.delay > 0:
            time.sleep(args.delay)

        return taxon_id, ok, msg

    # Parallel download
    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as executor:
        futures = {executor.submit(download_single, tid): tid for tid in taxon_ids}

        for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading"):
            taxon_id, ok, msg = future.result()

            if ok:
                if msg == "Already exists":
                    skip_count += 1
                else:
                    success_count += 1
            else:
                fail_count += 1
                failed_ids.append((taxon_id, msg))

            processed = success_count + skip_count + fail_count
            remaining = total_taxa - processed
            logger.info(
                f"Progress: {processed}/{total_taxa} completed ({remaining} remaining)"
            )

    # Summary
    logger.info("=" * 50)
    logger.info("Download Summary (NCBI):")
    logger.info(f"  Successfully downloaded: {success_count:,}")
    logger.info(f"  Already existed (skipped): {skip_count:,}")
    logger.info(f"  Failed: {fail_count:,}")
    logger.info(f"  Total FASTA files: {success_count + skip_count:,}")

    if failed_ids:
        failed_file = args.output_dir / "failed_downloads.txt"
        with open(failed_file, "w") as f:
            f.write("taxon_id\terror\n")
            for tid, msg in failed_ids:
                f.write(f"{tid}\t{msg}\n")
        logger.info(f"  Failed IDs saved to: {failed_file}")

    logger.info("=" * 50)


if __name__ == "__main__":
    main()
