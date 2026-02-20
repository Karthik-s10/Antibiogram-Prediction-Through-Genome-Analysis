#!/usr/bin/env python3
"""
Check the exact structure of the k-mer dataset
"""
from collections import defaultdict

file_path = "DATA/kmer_dataset_taxon_k10_p1e-5_all.txt"
unique_genomes = set()
genome_to_kmers = defaultdict(list)

print("Analyzing k-mer dataset structure...")

with open(file_path, 'r') as f:
    for line_num, line in enumerate(f, 1):
        parts = line.strip().split()
        if len(parts) >= 2:
            genome_id = parts[0]
            species = parts[1]
            kmer = parts[3] if len(parts) > 3 else "N/A"
            
            unique_genomes.add(genome_id)
            genome_to_kmers[genome_id].append(kmer)
            
            if len(unique_genomes) <= 10:
                print(f"Line {line_num}: Genome={genome_id}, Species={species}, K-mer={kmer}")

# Check how many k-mers per genome
sample_genome = list(unique_genomes)[0] if unique_genomes else None
if sample_genome:
    kmers_for_genome = genome_to_kmers[sample_genome]
    print(f"\nSample genome {sample_genome} has {len(kmers_for_genome)} k-mers")
    print(f"First 10 k-mers: {kmers_for_genome[:10]}")

print(f"\nStructure Analysis:")
print(f"Total unique genome IDs: {len(unique_genomes)}")
print(f"Total k-mer entries: {sum(len(kmers) for kmers in genome_to_kmers.values())}")
print(f"Average k-mers per genome: {sum(len(kmers) for kmers in genome_to_kmers.values()) / len(unique_genomes) if unique_genomes else 0}")

# Now let's check if these genome IDs exist in BVBRC file
print("\nChecking if these genome IDs exist in BVBRC mapping...")
bvbrc_file = "DATA/BVBRC_genome.txt"
found_genomes = 0

with open(bvbrc_file, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if str(unique_genomes.__iter__().__next__()) in line:  # Check first few genome IDs
            found_genomes += 1
            if found_genomes >= 10:
                break

print(f"Found {found_genomes} genome IDs in BVBRC file (checked first 10)")
