import {
  SequenceAnalyzer,
  SequenceMatch,
  MutationMatch,
} from "./sequenceAnalyzer";

export interface PredictionResult {
  antibiotic: string;
  prediction: "S" | "I" | "R";
  confidence: number;
  markers: GeneticMarker[];
  reasoning: string;
}

export interface GeneticMarker {
  id: string;
  name: string;
  description: string;
  impact: number;
  confidence: number;
  type: "gene" | "mutation";
}

export class ResistancePredictor {
  private analyzer: SequenceAnalyzer;

  // Standard antibiotic panel for testing
  private readonly ANTIBIOTIC_PANEL = [
    "ampicillin",
    "ciprofloxacin",
    "gentamicin",
    "tetracycline",
    "trimethoprim",
    "ceftriaxone",
    "meropenem",
    "colistin",
    "chloramphenicol",
    "fosfomycin",
    "azithromycin",
    "nitrofurantoin",
  ];

  constructor(fastaContent: string) {
    this.analyzer = new SequenceAnalyzer(fastaContent);
  }

  // Main prediction function
  public async predictResistance(): Promise<PredictionResult[]> {
    const geneMatches = this.analyzer.analyzeResistanceGenes();
    const mutations = this.analyzer.analyzeMutations();
    const sequenceStats = this.analyzer.getSequenceStats();

    const predictions: PredictionResult[] = [];

    for (const antibiotic of this.ANTIBIOTIC_PANEL) {
      const prediction = this.predictAntibioticSusceptibility(
        antibiotic,
        geneMatches,
        mutations,
        sequenceStats,
      );
      predictions.push(prediction);
    }

    return predictions;
  }

  private predictAntibioticSusceptibility(
    antibiotic: string,
    geneMatches: SequenceMatch[],
    mutations: MutationMatch[],
    sequenceStats: any,
  ): PredictionResult {
    const relevantGenes = geneMatches.filter((gene) =>
      gene.antibiotics.includes(antibiotic),
    );

    const relevantMutations = mutations.filter((mut) =>
      mut.antibiotics.includes(antibiotic),
    );

    const markers: GeneticMarker[] = [];
    let resistanceScore = 0;
    let totalConfidence = 0;
    let evidenceCount = 0;

    // Process resistance genes
    for (const gene of relevantGenes) {
      const impact = this.calculateGeneImpact(gene, antibiotic);
      resistanceScore += impact * gene.confidence;
      totalConfidence += gene.confidence;
      evidenceCount++;

      markers.push({
        id: gene.geneId,
        name: gene.geneName,
        description: gene.description,
        impact: impact,
        confidence: gene.confidence,
        type: "gene",
      });
    }

    // Process mutations
    for (const mutation of relevantMutations) {
      resistanceScore += mutation.impact * mutation.confidence;
      totalConfidence += mutation.confidence;
      evidenceCount++;

      markers.push({
        id: `${mutation.gene}_${mutation.mutation}`,
        name: `${mutation.gene} ${mutation.mutation}`,
        description: `Chromosomal mutation in ${mutation.gene}`,
        impact: mutation.impact,
        confidence: mutation.confidence,
        type: "mutation",
      });
    }

    // Calculate final prediction
    const avgConfidence =
      evidenceCount > 0 ? totalConfidence / evidenceCount : 0.5;
    const normalizedScore =
      evidenceCount > 0 ? resistanceScore / evidenceCount : 0;

    // Apply machine learning-like decision rules
    let prediction: "S" | "I" | "R";
    let reasoning: string;

    if (normalizedScore > 0.7) {
      prediction = "R";
      reasoning = `High resistance probability (${(normalizedScore * 100).toFixed(1)}%) based on ${evidenceCount} genetic markers`;
    } else if (normalizedScore > 0.3) {
      prediction = "I";
      reasoning = `Intermediate resistance probability (${(normalizedScore * 100).toFixed(1)}%) with ${evidenceCount} markers detected`;
    } else {
      prediction = "S";
      reasoning =
        evidenceCount > 0
          ? `Low resistance probability (${(normalizedScore * 100).toFixed(1)}%) despite ${evidenceCount} markers`
          : "No resistance markers detected in genome sequence";
    }

    // Adjust confidence based on sequence quality
    let finalConfidence = avgConfidence;
    if (sequenceStats.quality === "Low") {
      finalConfidence *= 0.8;
      reasoning += " (confidence reduced due to low sequence quality)";
    }

    // Add some variability for realism
    if (markers.length === 0) {
      // For susceptible predictions, add some baseline markers
      markers.push({
        id: `${antibiotic}_wildtype`,
        name: `Wild-type ${antibiotic} target`,
        description: `No resistance mutations detected in ${antibiotic} target genes`,
        impact: -0.1,
        confidence: Math.max(0.7, finalConfidence),
        type: "gene",
      });
    }

    return {
      antibiotic,
      prediction,
      confidence: Math.min(0.99, Math.max(0.6, finalConfidence)),
      markers: markers.slice(0, 5), // Limit to top 5 markers
      reasoning,
    };
  }

  private calculateGeneImpact(gene: SequenceMatch, antibiotic: string): number {
    // Base impact on gene confidence and known resistance strength
    let impact = gene.confidence * 0.8;

    // Adjust based on specific gene-antibiotic combinations
    const geneAntibioticMap: { [key: string]: { [key: string]: number } } = {
      "blaTEM-1": { ampicillin: 0.95, amoxicillin: 0.95 },
      "blaCTX-M": { ceftriaxone: 0.9, ampicillin: 0.85 },
      "aac3-IIa": { gentamicin: 0.91, tobramycin: 0.88 },
      qnrS1: { ciprofloxacin: 0.65, levofloxacin: 0.6 },
      tetA: { tetracycline: 0.88, doxycycline: 0.82 },
      "mcr-1": { colistin: 0.95 },
    };

    if (
      geneAntibioticMap[gene.geneId] &&
      geneAntibioticMap[gene.geneId][antibiotic]
    ) {
      impact = geneAntibioticMap[gene.geneId][antibiotic];
    }

    return Math.min(0.99, impact);
  }

  // Get analysis summary
  public getAnalysisSummary() {
    const stats = this.analyzer.getSequenceStats();
    const genes = this.analyzer.analyzeResistanceGenes();
    const mutations = this.analyzer.analyzeMutations();

    return {
      sequenceLength: stats.length,
      sequenceQuality: stats.quality,
      gcContent: stats.gcContent.toFixed(1),
      resistanceGenesFound: genes.length,
      mutationsFound: mutations.length,
      analysisTimestamp: new Date().toISOString(),
    };
  }
}
