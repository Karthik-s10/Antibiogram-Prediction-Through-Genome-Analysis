#!/usr/bin/env python3
"""
Count unique bacterial species in k-mer dataset
"""
from collections import defaultdict

file_path = "DATA/kmer_dataset_taxon_k10_p1e-5_all.txt"
species_set = set()
species_count = defaultdict(int)
total_lines = 0

try:
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if line_num > 10:  # Just check first 10 lines to understand format
                break
            parts = line.strip().split()
            if len(parts) >= 2:
                species = parts[1]
                species_set.add(species)
                species_count[species] += 1
                total_lines += 1
                print(f"Line {line_num}: {parts[:3]}... Species: {species}")
    
    print(f"\nFirst 10 lines analysis:")
    print(f"Total lines processed: {total_lines}")
    print(f"Unique species found: {len(species_set)}")
    print(f"Species counts: {dict(species_count)}")
    
    # Now process the whole file to get all species
    print("\nProcessing entire file...")
    species_set = set()
    line_count = 0
    
    with open(file_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                species = parts[1]
                species_set.add(species)
                line_count += 1
                if line_count % 100000 == 0:
                    print(f"Processed {line_count} lines...")
    
    print(f"\nFinal Results:")
    print(f"Total lines in dataset: {line_count}")
    print(f"Total unique species: {len(species_set)}")
    
except Exception as e:
    print(f"Error: {e}")
