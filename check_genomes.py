#!/usr/bin/env python3
"""
Check unique genome IDs in the dataset
"""
from collections import defaultdict

file_path = "DATA/kmer_dataset_taxon_k10_p1e-5_all.txt"
genome_ids = set()
genome_id_examples = defaultdict(list)

print("Checking first 50 lines for genome IDs...")
with open(file_path, 'r') as f:
    for line_num, line in enumerate(f, 1):
        if line_num > 50:
            break
        parts = line.strip().split()
        if len(parts) >= 1:
            genome_id = parts[0]
            genome_ids.add(genome_id)
            if len(genome_id_examples[genome_id]) < 3:
                genome_id_examples[genome_id].append(line_num)
                print(f"Line {line_num}: Genome ID = {genome_id}")

print(f"\nUnique genome IDs in first 50 lines: {len(genome_ids)}")
print("Sample genome IDs:")
for gid in sorted(list(genome_ids)[:10]):
    print(f"  - {gid}")

# Now check unique genome IDs in entire dataset
print("\nCounting all unique genome IDs...")
genome_ids = set()
count = 0
with open(file_path, 'r') as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) >= 1:
            genome_id = parts[0]
            genome_ids.add(genome_id)
            count += 1
            if count % 1000000 == 0:
                print(f"Processed {count} lines, found {len(genome_ids)} unique genomes...")

print(f"\nFinal Results:")
print(f"Total lines: {count}")
print(f"Total unique genome IDs: {len(genome_ids)}")
