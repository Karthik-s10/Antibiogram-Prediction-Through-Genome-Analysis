#!/usr/bin/env python3
"""
Check what species are in the dataset
"""
from collections import defaultdict

file_path = "DATA/kmer_dataset_taxon_k10_p1e-5_all.txt"
species_set = set()
species_examples = defaultdict(list)

with open(file_path, 'r') as f:
    for line_num, line in enumerate(f, 1):
        parts = line.strip().split()
        if len(parts) >= 2:
            species = parts[1]
            species_set.add(species)
            if len(species_examples[species]) < 5:
                species_examples[species].append(line_num)

print(f"Total unique species: {len(species_set)}")
print("\nSpecies found:")
for species in sorted(species_set):
    print(f"  - {species}")
    print(f"    Example lines: {species_examples[species][:3]}")
