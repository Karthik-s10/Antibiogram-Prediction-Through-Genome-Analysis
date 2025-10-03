/**
 * Feature engineering module for genomic data
 * Converts FASTA sequences into numerical feature matrices
 */

export interface KmerFeatures {
  featureMatrix: number[][];
  featureNames: string[];
  sampleIds: string[];
}

export interface FeatureEngineeringOptions {
  kmerSize: number;
  maxFeatures?: number;
  normalization?: 'none' | 'l1' | 'l2';
  includeReverseComplement?: boolean;
}

export class FeatureEngineering {
  private options: FeatureEngineeringOptions;
  private kmerDictionary: Map<string, number> = new Map();
  
  constructor(options?: Partial<FeatureEngineeringOptions>) {
    this.options = {
      kmerSize: 5,
      maxFeatures: 10000,
      normalization: 'l2',
      includeReverseComplement: true,
      ...options
    };
  }
  
  /**
   * Extract k-mer features from a collection of FASTA sequences
   * @param fastaContents - Array of FASTA file contents
   * @param sampleIds - Array of sample IDs corresponding to the FASTA files
   */
  public extractKmerFeatures(
    fastaContents: string[],
    sampleIds: string[]
  ): KmerFeatures {
    console.log(`Extracting ${this.options.kmerSize}-mer features from ${fastaContents.length} sequences`);
    
    // Step 1: Parse FASTA files and extract sequences
    const sequences = fastaContents.map(this.parseFasta);
    
    // Step 2: Build k-mer dictionary from all sequences
    this.buildKmerDictionary(sequences);
    
    // Step 3: Convert sequences to feature vectors
    const featureMatrix = this.sequencesToFeatureMatrix(sequences);
    
    // Step 4: Apply normalization if specified
    const normalizedMatrix = this.normalizeFeatureMatrix(featureMatrix);
    
    // Convert dictionary to array of feature names
    const featureNames = Array.from(this.kmerDictionary.keys());
    
    return {
      featureMatrix: normalizedMatrix,
      featureNames,
      sampleIds
    };
  }
  
  /**
   * Extract k-mer features from a single FASTA sequence
   * @param fastaContent - FASTA file content
   */
  public extractSingleSequenceFeatures(fastaContent: string): number[] {
    const sequence = this.parseFasta(fastaContent);
    
    // If dictionary is empty, we can't extract features properly
    if (this.kmerDictionary.size === 0) {
      throw new Error("K-mer dictionary not built. Call extractKmerFeatures first or load a pre-built dictionary.");
    }
    
    // Extract k-mers and build feature vector
    const featureVector = this.sequenceToFeatureVector(sequence);
    
    // Apply normalization
    return this.normalizeFeatureVector(featureVector);
  }
  
  /**
   * Save the k-mer dictionary to be used later
   * @returns Serialized k-mer dictionary
   */
  public saveKmerDictionary(): string {
    return JSON.stringify(Array.from(this.kmerDictionary.entries()));
  }
  
  /**
   * Load a pre-built k-mer dictionary
   * @param serializedDictionary - Serialized k-mer dictionary
   */
  public loadKmerDictionary(serializedDictionary: string): void {
    const entries = JSON.parse(serializedDictionary) as [string, number][];
    this.kmerDictionary = new Map(entries);
    console.log(`Loaded k-mer dictionary with ${this.kmerDictionary.size} features`);
  }
  
  /**
   * Parse FASTA content and extract the sequence
   * @param fastaContent - FASTA file content
   */
  private parseFasta(fastaContent: string): string {
    const lines = fastaContent.split('\n');
    const sequenceLines = lines.filter(line => !line.startsWith('>') && line.trim().length > 0);
    return sequenceLines.join('').toUpperCase();
  }
  
  /**
   * Build k-mer dictionary from a collection of sequences
   * @param sequences - Array of DNA sequences
   */
  private buildKmerDictionary(sequences: string[]): void {
    const kmerCounts = new Map<string, number>();
    const k = this.options.kmerSize;
    
    // Count k-mers across all sequences
    for (const sequence of sequences) {
      for (let i = 0; i <= sequence.length - k; i++) {
        const kmer = sequence.substring(i, i + k);
        
        // Skip k-mers with non-ACGT characters
        if (/^[ACGT]+$/.test(kmer)) {
          kmerCounts.set(kmer, (kmerCounts.get(kmer) || 0) + 1);
          
          // Include reverse complement if specified
          if (this.options.includeReverseComplement) {
            const revComp = this.getReverseComplement(kmer);
            kmerCounts.set(revComp, (kmerCounts.get(revComp) || 0) + 1);
          }
        }
      }
    }
    
    // Sort k-mers by frequency and take top maxFeatures
    const sortedKmers = Array.from(kmerCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, this.options.maxFeatures)
      .map(entry => entry[0]);
    
    // Build dictionary mapping k-mers to indices
    this.kmerDictionary.clear();
    sortedKmers.forEach((kmer, index) => {
      this.kmerDictionary.set(kmer, index);
    });
    
    console.log(`Built k-mer dictionary with ${this.kmerDictionary.size} features`);
  }
  
  /**
   * Convert a collection of sequences to a feature matrix
   * @param sequences - Array of DNA sequences
   */
  private sequencesToFeatureMatrix(sequences: string[]): number[][] {
    return sequences.map(sequence => this.sequenceToFeatureVector(sequence));
  }
  
  /**
   * Convert a single sequence to a feature vector
   * @param sequence - DNA sequence
   */
  private sequenceToFeatureVector(sequence: string): number[] {
    const k = this.options.kmerSize;
    const featureVector = new Array(this.kmerDictionary.size).fill(0);
    
    // Count k-mers in the sequence
    for (let i = 0; i <= sequence.length - k; i++) {
      const kmer = sequence.substring(i, i + k);
      
      // Skip k-mers with non-ACGT characters
      if (/^[ACGT]+$/.test(kmer)) {
        const index = this.kmerDictionary.get(kmer);
        if (index !== undefined) {
          featureVector[index]++;
        }
        
        // Include reverse complement if specified
        if (this.options.includeReverseComplement) {
          const revComp = this.getReverseComplement(kmer);
          const revIndex = this.kmerDictionary.get(revComp);
          if (revIndex !== undefined) {
            featureVector[revIndex]++;
          }
        }
      }
    }
    
    return featureVector;
  }
  
  /**
   * Normalize the feature matrix based on the specified normalization method
   * @param featureMatrix - Matrix of feature vectors
   */
  private normalizeFeatureMatrix(featureMatrix: number[][]): number[][] {
    return featureMatrix.map(vector => this.normalizeFeatureVector(vector));
  }
  
  /**
   * Normalize a feature vector based on the specified normalization method
   * @param featureVector - Feature vector to normalize
   */
  private normalizeFeatureVector(featureVector: number[]): number[] {
    switch (this.options.normalization) {
      case 'l1':
        // L1 normalization (sum of absolute values = 1)
        const l1Norm = featureVector.reduce((sum, val) => sum + Math.abs(val), 0);
        return l1Norm > 0 ? featureVector.map(val => val / l1Norm) : featureVector;
        
      case 'l2':
        // L2 normalization (Euclidean norm = 1)
        const l2Norm = Math.sqrt(featureVector.reduce((sum, val) => sum + val * val, 0));
        return l2Norm > 0 ? featureVector.map(val => val / l2Norm) : featureVector;
        
      case 'none':
      default:
        // No normalization
        return featureVector;
    }
  }
  
  /**
   * Get the reverse complement of a DNA sequence
   * @param sequence - DNA sequence
   */
  private getReverseComplement(sequence: string): string {
    const complementMap: Record<string, string> = {
      'A': 'T',
      'C': 'G',
      'G': 'C',
      'T': 'A'
    };
    
    return sequence
      .split('')
      .reverse()
      .map(base => complementMap[base] || base)
      .join('');
  }
}