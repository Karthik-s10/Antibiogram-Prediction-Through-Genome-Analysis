/**
 * Parser for k-mer data in the format:
 * GCA_000002515.1 Bacteria 10 ACCCCGCGCG 1.43e-07 9.83e-03 GCA_000002515.1 Bacteria 10 ACCGCCGCCG 1.43e-07 9.83e-03
 */

export interface KmerEntry {
  genomeId: string;
  taxonomy: string;
  kmerSize: number;
  kmerSequence: string;
  value1: number;
  value2: number;
}

export interface KmerData {
  [genomeId: string]: {
    kmers: Map<string, number>;
    taxonomy: string;
    kmerSize: number;
  };
}

/**
 * Parse k-mer data from a string
 * @param data Raw k-mer data string
 * @returns Parsed k-mer data
 */
export function parseKmerData(data: string): KmerData {
  const lines = data.trim().split('\n');
  const kmerData: KmerData = {};

  for (const line of lines) {
    const entries = line.trim().split(/\s+/);
    
    // Process entries in groups of 6 (genomeId, taxonomy, kmerSize, kmerSequence, value1, value2)
    for (let i = 0; i < entries.length; i += 6) {
      if (i + 5 >= entries.length) break;
      
      const genomeId = entries[i];
      const taxonomy = entries[i + 1];
      const kmerSize = parseInt(entries[i + 2]);
      const kmerSequence = entries[i + 3];
      const value1 = parseFloat(entries[i + 4]);
      const value2 = parseFloat(entries[i + 5]);
      
      if (!kmerData[genomeId]) {
        kmerData[genomeId] = {
          kmers: new Map<string, number>(),
          taxonomy,
          kmerSize
        };
      }
      
      // Use value2 as the k-mer count/importance
      kmerData[genomeId].kmers.set(kmerSequence, value2);
    }
  }
  
  return kmerData;
}

/**
 * Convert k-mer data to a feature matrix
 * @param kmerData Parsed k-mer data
 * @returns Feature matrix and feature names
 */
export function kmerDataToFeatureMatrix(kmerData: KmerData): {
  featureMatrix: number[][];
  featureNames: string[];
  genomeIds: string[];
} {
  // Collect all unique k-mers
  const uniqueKmers = new Set<string>();
  Object.values(kmerData).forEach(data => {
    data.kmers.forEach((_, kmer) => uniqueKmers.add(kmer));
  });
  
  const featureNames = Array.from(uniqueKmers);
  const genomeIds = Object.keys(kmerData);
  
  // Create feature matrix
  const featureMatrix = genomeIds.map(genomeId => {
    const genome = kmerData[genomeId];
    return featureNames.map(kmer => genome.kmers.get(kmer) || 0);
  });
  
  return { featureMatrix, featureNames, genomeIds };
}

/**
 * Extract k-mers from a DNA sequence
 * @param sequence DNA sequence
 * @param k K-mer size
 * @returns Map of k-mers to their counts
 */
export function extractKmersFromSequence(sequence: string, k: number): Map<string, number> {
  const kmers = new Map<string, number>();
  
  for (let i = 0; i <= sequence.length - k; i++) {
    const kmer = sequence.substring(i, i + k);
    // Only count valid DNA k-mers (containing only A, C, G, T)
    if (/^[ACGT]+$/.test(kmer)) {
      kmers.set(kmer, (kmers.get(kmer) || 0) + 1);
    }
  }
  
  return kmers;
}