import collections
from pathlib import Path

"""
Analyze k-mer file to determine k value distribution per genome.

Expected k-mer TSV format per line (no header):
    genome_id\tdomain\tk\tkmer_sequence\tprob1\tprob2

This script:
- Streams the file line by line (no full load into memory)
- Records the first k value seen per genome_id (e.g., GCA_...)
- At the end, prints:
    - Total unique genome_ids
    - For each k, how many genome_ids use that k

Usage (from project root):

    python scripts/analyze_kmer_k_values.py \
        --kmer-file DATA/SIGNIFICANT_DNA_KMERS_BACTERIA

"""

import argparse


def analyze_k_values(kmer_path: Path) -> None:
    if not kmer_path.is_file():
        raise FileNotFoundError(f"K-mer file not found: {kmer_path}")

    genome_to_k = {}
    # We only need the first k per genome; use a dict and never overwrite

    with kmer_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) < 3:
                # Unexpected line; skip
                continue

            genome_id = parts[0]
            k_str = parts[2]

            # Only record k once per genome_id
            if genome_id in genome_to_k:
                continue

            try:
                k_val = int(k_str)
            except ValueError:
                # If k is not an int, skip this line
                continue

            genome_to_k[genome_id] = k_val

    # Now count how many genomes per k
    k_counts = collections.Counter(genome_to_k.values())

    print(f"Analyzed file: {kmer_path}")
    print(f"Total unique genome IDs: {len(genome_to_k)}")
    print()
    print("k value distribution (k -> number of genomes):")
    for k_val in sorted(k_counts.keys()):
        print(f"k = {k_val}: {k_counts[k_val]} genomes")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze k values per genome from a k-mer TSV file.",
    )
    parser.add_argument(
        "--kmer-file",
        type=str,
        required=True,
        help="Path to SIGNIFICANT_DNA_KMERS_BACTERIA or another k-mer TSV.",
    )

    args = parser.parse_args()
    kmer_path = Path(args.kmer_file)
    analyze_k_values(kmer_path)


if __name__ == "__main__":
    main()
