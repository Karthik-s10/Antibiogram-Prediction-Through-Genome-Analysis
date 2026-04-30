import pandas as pd
import time

print("Loading SIGNIFICANT...")
t0 = time.time()
df = pd.read_csv('e:/Antibiogram-Prediction-Through-Genome-Analysis/DATA/SIGNIFICANT_DNA_KMERS_BACTERIA', sep='\t', usecols=[0], header=None)
print('Unique Genomes in SIGNIFICANT_DNA_KMERS:', df[0].nunique(), "Time:", time.time() - t0)

print("\nLoading kmer_dataset...")
t1 = time.time()
df2 = pd.read_csv('e:/Antibiogram-Prediction-Through-Genome-Analysis/DATA/kmer_dataset_taxon_k10_p1e-5_all.txt', sep='\t', usecols=[0], header=None)
print('Unique taxons in kmer_dataset_taxon_k10:', df2[0].nunique(), "Time:", time.time() - t1)
