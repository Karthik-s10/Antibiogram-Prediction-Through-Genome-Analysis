#!/usr/bin/env python3
"""
Count actual bacterial species from BVBRC genome mapping
"""
import re
from collections import defaultdict, Counter

file_path = "DATA/BVBRC_genome.txt"
species_list = []
genus_counts = Counter()
species_counts = Counter()

print("Parsing BVBRC genome file for species information...")

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line_num, line in enumerate(f, 1):
        # Look for species names in quotes
        # Pattern: "Escherichia coli" or "Staphylococcus aureus"
        species_match = re.search(r'"([A-Z][a-z]+ [a-z]+)"', line)
        if species_match:
            species = species_match.group(1)
            species_list.append(species)
            
            # Extract genus (first word)
            genus = species.split()[0]
            genus_counts[genus] += 1
            species_counts[species] += 1
            
            if len(species_counts) <= 20:  # Show first 20 examples
                print(f"Found: {species}")

print(f"\nTotal unique species found: {len(species_counts)}")
print(f"Total unique genera: {len(genus_counts)}")

print(f"\nTop 30 most common species:")
for species, count in species_counts.most_common(30):
    print(f"  {count:6d} - {species}")

print(f"\nTop 15 most common genera:")
for genus, count in genus_counts.most_common(15):
    print(f"  {count:6d} - {genus} (multiple species)")

# Check for common pathogens
common_pathogens = [
    "Escherichia coli", "Staphylococcus aureus", "Klebsiella pneumoniae",
    "Pseudomonas aeruginosa", "Acinetobacter baumannii", "Enterococcus faecalis",
    "Streptococcus pneumoniae", "Salmonella enterica", "Mycobacterium tuberculosis"
]

print(f"\nCommon clinically relevant pathogens found:")
for pathogen in common_pathogens:
    if pathogen in species_counts:
        print(f"  ✓ {pathogen}: {species_counts[pathogen]} genomes")
    else:
        print(f"  ✗ {pathogen}: Not found")
