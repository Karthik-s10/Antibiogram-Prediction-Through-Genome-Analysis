#!/usr/bin/env python3
"""
Analyze bacterial species in k-mer dataset
"""
import pandas as pd
from collections import Counter

# Read the dataset
file_path = "DATA/kmer_dataset_taxon_k10_p1e-5_all.txt"

try:
    # Try with space separator first
    df = pd.read_csv(file_path, sep=r'\s+', header=None, engine='python',
                     names=['genome_id', 'species', 'k', 'kmer', 'frequency'])
    
    print(f"Dataset shape: {df.shape}")
    print(f"\nColumns: {df.columns.tolist()}")
    print(f"\nFirst few rows:")
    print(df.head())
    
    # Count unique species
    species_counts = df['species'].value_counts()
    
    print(f"\nTotal unique species: {len(species_counts)}")
    print(f"\nSpecies distribution:")
    print(species_counts)
    
    # Show top 20 most common species
    print(f"\nTop 20 most common species:")
    print(species_counts.head(20))
    
except Exception as e:
    print(f"Error reading file: {e}")
    print("Trying different parsing...")
    
    # Try with different separator
    try:
        with open(file_path, 'r') as f:
            first_line = f.readline().strip()
            print(f"First line: {first_line}")
            
        # Try tab-separated
        df = pd.read_csv(file_path, sep='\t', header=None,
                         names=['genome_id', 'species', 'k', 'kmer', 'frequency'])
        
        species_counts = df['species'].value_counts()
        print(f"\nTotal unique species: {len(species_counts)}")
        print(f"\nTop 20 species:")
        print(species_counts.head(20))
        
    except Exception as e2:
        print(f"Error with tab separation: {e2}")
