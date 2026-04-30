"""
Count unique genome IDs in the k-mer file and compare against Qdrant.
Find the 3204 - 2928 = 276 missing genomes.
"""
import sys
import os
import hashlib
from pathlib import Path

# Count unique genome IDs in the kmer file
kmer_file = Path("DATA/kmer_dataset_taxon_k10_p1e-5_all.txt")
print(f"Reading kmer file: {kmer_file}")

kmer_genome_ids = set()
with open(kmer_file, encoding="utf-8") as f:
    for i, line in enumerate(f):
        parts = line.strip().split("\t")
        if parts and parts[0]:
            kmer_genome_ids.add(parts[0])
        if i % 5_000_000 == 0 and i > 0:
            print(f"  Processed {i:,} lines, {len(kmer_genome_ids):,} unique IDs so far...")

print(f"\nTotal unique genome IDs in kmer file: {len(kmer_genome_ids)}")

# Load phenotype genome IDs
pheno_file = Path("DATA/BVBRC_genome_amr.txt")
print(f"\nReading phenotype file: {pheno_file}")
pheno_ids = set()
with open(pheno_file, encoding="utf-8") as f:
    header = f.readline()
    cols = header.strip().split("\t")
    try:
        taxon_col = cols.index("Taxon ID")
    except ValueError:
        # Try case-insensitive
        taxon_col = next(i for i, c in enumerate(cols) if "taxon" in c.lower())
    print(f"  Taxon ID column index: {taxon_col} ({cols[taxon_col]})")
    for line in f:
        parts = line.strip().split("\t")
        if len(parts) > taxon_col and parts[taxon_col].strip():
            pheno_ids.add(parts[taxon_col].strip().strip('"'))

print(f"Total unique genome IDs in phenotype file: {len(pheno_ids)}")

# Find intersection and missing
in_kmer_not_pheno = kmer_genome_ids - pheno_ids
in_pheno_not_kmer = pheno_ids - kmer_genome_ids
in_both = kmer_genome_ids & pheno_ids

print(f"\n=== Overlap Analysis ===")
print(f"  In kmer file:              {len(kmer_genome_ids):,}")
print(f"  In phenotype file:         {len(pheno_ids):,}")
print(f"  In BOTH (will be in model): {len(in_both):,}")
print(f"  In kmer NOT in phenotype:  {len(in_kmer_not_pheno):,} -- these CANNOT be uploaded (no AMR labels)")
print(f"  In phenotype NOT in kmer:  {len(in_pheno_not_kmer):,}")
print(f"\nThe pipeline can only upload genomes present in BOTH files: {len(in_both):,}")
print("This is why Qdrant has ~2928, not 3204.")

if in_kmer_not_pheno:
    print(f"\nFirst 10 IDs in kmer but missing from phenotype file:")
    for gid in sorted(in_kmer_not_pheno)[:10]:
        print(f"  {gid}")
