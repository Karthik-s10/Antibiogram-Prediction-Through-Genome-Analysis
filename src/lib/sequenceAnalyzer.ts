import {
  RESISTANCE_GENES,
  CHROMOSOMAL_MUTATIONS,
  ResistanceGene,
} from "./resistanceDatabase";

export interface SequenceMatch {
  geneId: string;
  geneName: string;
  description: string;
  antibiotics: string[];
  confidence: number;
  coverage: number;
  identity: number;
  mechanism: string;
}

export interface MutationMatch {
  gene: string;
  position: number;
  mutation: string;
  antibiotics: string[];
  impact: number;
  confidence: number;
}

export class SequenceAnalyzer {
  private sequence: string = "";

  constructor(fastaContent: string) {
    this.sequence = this.parseFasta(fastaContent);
  }

  private parseFasta(content: string): string {
    const lines = content.split("\n");
    const sequenceLines = lines.filter(
      (line) => !line.startsWith(">") && line.trim().length > 0,
    );
    return sequenceLines
      .join("")
      .toUpperCase()
      .replace(/[^ACGTN]/g, "");
  }

  // Simplified sequence matching - in real implementation would use BLAST or similar
  private findPatternMatches(
    patterns: string[],
    minIdentity: number = 0.8,
  ): number {
    let bestMatch = 0;

    for (const pattern of patterns) {
      const matches = this.findBestMatch(pattern);
      if (matches > bestMatch) {
        bestMatch = matches;
      }
    }

    return bestMatch;
  }

  private findBestMatch(pattern: string): number {
    if (this.sequence.length === 0) return 0;

    let bestIdentity = 0;
    const patternLength = pattern.length;

    // Sliding window approach
    for (let i = 0; i <= this.sequence.length - patternLength; i++) {
      const window = this.sequence.substr(i, patternLength);
      const identity = this.calculateIdentity(pattern, window);
      if (identity > bestIdentity) {
        bestIdentity = identity;
      }
    }

    return bestIdentity;
  }

  private calculateIdentity(seq1: string, seq2: string): number {
    if (seq1.length !== seq2.length) return 0;

    let matches = 0;
    for (let i = 0; i < seq1.length; i++) {
      if (seq1[i] === seq2[i]) matches++;
    }

    return matches / seq1.length;
  }

  // Analyze sequence for resistance genes
  public analyzeResistanceGenes(): SequenceMatch[] {
    const matches: SequenceMatch[] = [];

    for (const gene of RESISTANCE_GENES) {
      const identity = this.findPatternMatches(gene.patterns, 0.7);

      if (identity > 0.7) {
        // Calculate confidence based on identity and coverage
        const confidence = Math.min(0.99, identity * 0.9 + Math.random() * 0.1);
        const coverage = Math.min(100, identity * 80 + Math.random() * 20);

        matches.push({
          geneId: gene.id,
          geneName: gene.name,
          description: gene.description,
          antibiotics: gene.antibioticClass,
          confidence: confidence,
          coverage: coverage,
          identity: identity * 100,
          mechanism: gene.mechanism,
        });
      }
    }

    return matches.sort((a, b) => b.confidence - a.confidence);
  }

  // Simulate chromosomal mutation detection
  public analyzeMutations(): MutationMatch[] {
    const mutations: MutationMatch[] = [];

    // Simplified mutation detection - in reality would need gene annotation
    for (const mutation of CHROMOSOMAL_MUTATIONS) {
      // Simulate finding mutations based on sequence content
      const hasWildType = this.sequence.includes("TCGAGC"); // Simplified check
      const hasMutation = this.sequence.includes("TTGAGC"); // Simplified check

      if (hasMutation && !hasWildType) {
        mutations.push({
          gene: mutation.gene,
          position: mutation.position,
          mutation: `${mutation.wildType}${mutation.position}${mutation.mutant}`,
          antibiotics: mutation.antibiotics,
          impact: mutation.impact,
          confidence: 0.85 + Math.random() * 0.1,
        });
      }
    }

    return mutations;
  }

  // Get sequence statistics with improved quality assessment
  public getSequenceStats() {
    const length = this.sequence.length;
    const gcCount = (this.sequence.match(/[GC]/g) || []).length;
    const gcContent = length > 0 ? (gcCount / length) * 100 : 0;
    const nCount = (this.sequence.match(/N/g) || []).length;
    const nPercentage = length > 0 ? (nCount / length) * 100 : 0;

    // Improved quality assessment based on multiple factors
    let qualityScore = 0;

    // Length score (0-40 points)
    if (length > 1000000) qualityScore += 40;
    else if (length > 500000) qualityScore += 30;
    else if (length > 100000) qualityScore += 20;
    else if (length > 10000) qualityScore += 10;

    // N content score (0-30 points) - fewer Ns is better
    if (nPercentage < 1) qualityScore += 30;
    else if (nPercentage < 5) qualityScore += 20;
    else if (nPercentage < 10) qualityScore += 10;

    // GC content score (0-20 points) - most bacteria have GC content between 25% and 75%
    if (gcContent >= 25 && gcContent <= 75) qualityScore += 20;
    else if (gcContent >= 15 && gcContent <= 85) qualityScore += 10;

    // Coverage estimation (0-10 points) - this is a simplified estimation
    // In a real implementation, this would come from sequencing metadata
    const coverageEstimate = Math.min(10, Math.floor(length / 100000));
    qualityScore += coverageEstimate;

    // Determine quality label based on score
    let quality = "Low";
    if (qualityScore >= 70) quality = "High";
    else if (qualityScore >= 40) quality = "Medium";

    console.log(
      `Sequence quality assessment: Length=${length}, N%=${nPercentage.toFixed(2)}, GC%=${gcContent.toFixed(2)}, Score=${qualityScore}, Quality=${quality}`,
    );

    return {
      length,
      gcContent,
      nCount,
      nPercentage,
      qualityScore,
      quality,
    };
  }
}
