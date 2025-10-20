import { XGBoostAMRModel, ModelTrainingResult as XGBoostResult } from '../models/xgboostModel';
import { DNABERTModel, ModelTrainingResult as DNABERTResult } from '../models/dnabertModel';
import { QdrantService, GenomeEmbedding } from '../services/qdrantService';
import { parseKmerData, kmerDataToFeatureMatrix, extractKmersFromSequence } from '../parsers/kmerParser';
import { parsePhenotypeData, phenotypeDataToLabels, phenotypeDataToMultiClassLabels } from '../parsers/phenotypeParser';

export interface TrainingPipelineOptions {
  xgboostKmerSize: number;
  dnabertKmerSize: number;
  dnabertModelName: string;
  targetAntibiotic: string;
  validationSplit?: number;
  qdrantConfig?: {
    url: string;
    apiKey?: string;
    collectionName: string;
  };
}

export interface TrainingResult {
  xgboost: XGBoostResult;
  dnabert: DNABERTResult;
  bestModel: 'xgboost' | 'dnabert';
  featureCount: number;
  sampleCount: number;
  targetAntibiotic: string;
}

export class AMRTrainingPipeline {
  private options: TrainingPipelineOptions;
  private xgboostModel: XGBoostAMRModel;
  private dnabertModel: DNABERTModel;
  private qdrantService: QdrantService | null = null;
  
  constructor(options: TrainingPipelineOptions) {
    this.options = {
      validationSplit: 0.2,
      ...options
    };
    
    // Initialize models
    this.xgboostModel = new XGBoostAMRModel();
    this.dnabertModel = new DNABERTModel({
      modelName: options.dnabertModelName,
      kmerSize: options.dnabertKmerSize
    });
    
    // Initialize Qdrant service if config provided
    if (options.qdrantConfig) {
      this.qdrantService = new QdrantService(options.qdrantConfig);
    }
  }
  
  /**
   * Run the complete training pipeline
   * @param kmerData Raw k-mer data
   * @param phenotypeData Raw phenotype data
   * @returns Training results
   */
  async runTrainingPipeline(
    kmerData: string,
    phenotypeData: string
  ): Promise<TrainingResult> {
    console.log('Starting AMR training pipeline');
    
    // Parse input data
    console.log('Parsing k-mer data...');
    const parsedKmerData = parseKmerData(kmerData);
    
    console.log('Parsing phenotype data...');
    const parsedPhenotypeData = parsePhenotypeData(phenotypeData);
    
    // Convert to feature matrix
    console.log('Converting k-mer data to feature matrix...');
    const { featureMatrix, featureNames, genomeIds } = kmerDataToFeatureMatrix(parsedKmerData);
    
    // Get labels for target antibiotic
    console.log(`Getting labels for ${this.options.targetAntibiotic}...`);
    const binaryLabels = phenotypeDataToLabels(
      parsedPhenotypeData,
      genomeIds,
      this.options.targetAntibiotic
    );
    
    const multiClassLabels = phenotypeDataToMultiClassLabels(
      parsedPhenotypeData,
      genomeIds,
      this.options.targetAntibiotic
    );
    
    // Split data for validation
    const { trainIndices, valIndices } = this.splitData(
      binaryLabels,
      this.options.validationSplit || 0.2
    );
    
    console.log(`Training set: ${trainIndices.length} samples`);
    console.log(`Validation set: ${valIndices.length} samples`);
    
    // Train XGBoost model
    console.log('Training XGBoost model...');
    const xgboostResult = await this.xgboostModel.train(
      featureMatrix,
      binaryLabels,
      featureNames
    );
    
    // Train DNABERT model (simplified for this example)
    console.log('Training DNABERT model...');
    // In a real implementation, we would extract gene sequences and fine-tune DNABERT
    // For this example, we'll use mock results
    const dnabertResult: DNABERTResult = {
      accuracy: 0.94,
      precision: 0.92,
      recall: 0.95,
      f1Score: 0.93,
      confusionMatrix: [[45, 5], [3, 47]]
    };
    
    // Determine the best model
    const bestModel = dnabertResult.f1Score > xgboostResult.f1Score ? 'dnabert' : 'xgboost';
    
    // Store embeddings in Qdrant if configured
    if (this.qdrantService) {
      await this.storeGenomeEmbeddings(
        parsedKmerData,
        multiClassLabels,
        genomeIds
      );
    }
    
    return {
      xgboost: xgboostResult,
      dnabert: dnabertResult,
      bestModel,
      featureCount: featureNames.length,
      sampleCount: genomeIds.length,
      targetAntibiotic: this.options.targetAntibiotic
    };
  }
  
  /**
   * Make predictions for a new genome
   * @param fastaContent FASTA content of the genome
   * @returns Prediction results
   */
  async predictGenome(fastaContent: string): Promise<{
    prediction: 'R' | 'S' | 'I';
    confidence: number;
    model: 'xgboost' | 'dnabert';
    similarGenomes?: {
      genomeId: string;
      score: number;
      prediction: 'R' | 'S' | 'I' | '';
    }[];
  }> {
    // Extract k-mers from the FASTA sequence
    const sequence = fastaContent.split('\n')
      .filter(line => !line.startsWith('>'))
      .join('');
    
    // Extract k-mers for XGBoost
    const kmers = extractKmersFromSequence(sequence, this.options.xgboostKmerSize);
    
    // Convert to feature vector
    // In a real implementation, we would need to align with the training features
    // For this example, we'll use a simplified approach
    const featureVector = Array(1000).fill(0); // Placeholder
    
    // Make prediction with XGBoost
    const xgboostPrediction = await this.xgboostModel.predict([featureVector]);
    
    // Extract gene sequences for DNABERT
    const geneSequences = this.dnabertModel.extractGeneSequences(fastaContent);
    
    // Make prediction with DNABERT
    const dnabertPrediction = await this.dnabertModel.predictGenome(geneSequences);
    
    // Combine predictions (in a real implementation, use the best model)
    const prediction = xgboostPrediction[0] === 1 || dnabertPrediction === 1 ? 'R' : 'S';
    const confidence = 0.92; // Placeholder
    
    // Find similar genomes if Qdrant is configured
    let similarGenomes;
    if (this.qdrantService) {
      // Create embedding for the new genome
      // In a real implementation, this would be a proper embedding
      const embedding = Array(100).fill(0).map(() => Math.random()); // Placeholder
      
      // Search for similar genomes
      const results = await this.qdrantService.searchSimilarGenomes(embedding, 5);
      
      similarGenomes = results.map(result => ({
        genomeId: result.genomeId,
        score: result.score,
        prediction: result.metadata.antibioticResistance?.[this.options.targetAntibiotic] || ''
      }));
    }
    
    return {
      prediction,
      confidence,
      model: 'xgboost', // Placeholder
      similarGenomes
    };
  }
  
  /**
   * Store genome embeddings in Qdrant
   * @param kmerData Parsed k-mer data
   * @param labels Antibiotic resistance labels
   * @param genomeIds Genome IDs
   */
  private async storeGenomeEmbeddings(
    kmerData: any,
    labels: string[],
    genomeIds: string[]
  ): Promise<void> {
    if (!this.qdrantService) return;
    
    console.log('Storing genome embeddings in Qdrant...');
    
    // Initialize Qdrant collection
    await this.qdrantService.initialize(100); // Embedding size
    
    // Create embeddings for each genome
    const embeddings: GenomeEmbedding[] = genomeIds.map((genomeId, index) => {
      // In a real implementation, this would be a proper embedding
      // For this example, we'll use random vectors
      const embedding = Array(100).fill(0).map(() => Math.random());
      
      return {
        genomeId,
        embedding,
        metadata: {
          taxonomy: kmerData[genomeId]?.taxonomy || 'Unknown',
          antibioticResistance: {
            [this.options.targetAntibiotic]: labels[index] as 'R' | 'S' | 'I' | ''
          }
        }
      };
    });
    
    // Store embeddings
    await this.qdrantService.storeEmbeddings(embeddings);
  }
  
  /**
   * Split data into training and validation sets
   * @param labels Labels array
   * @param validationSplit Validation split ratio
   * @returns Training and validation indices
   */
  private splitData(labels: number[], validationSplit: number): {
    trainIndices: number[];
    valIndices: number[];
  } {
    // Get indices of valid samples (with known labels)
    const validIndices = labels
      .map((label, index) => label !== -1 ? index : -1)
      .filter(index => index !== -1);
    
    // Shuffle indices
    const shuffledIndices = this.shuffleArray(validIndices);
    
    // Split into training and validation sets
    const splitIndex = Math.floor(shuffledIndices.length * (1 - validationSplit));
    const trainIndices = shuffledIndices.slice(0, splitIndex);
    const valIndices = shuffledIndices.slice(splitIndex);
    
    return { trainIndices, valIndices };
  }
  
  /**
   * Shuffle an array
   * @param array Array to shuffle
   * @returns Shuffled array
   */
  private shuffleArray<T>(array: T[]): T[] {
    const result = [...array];
    for (let i = result.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [result[i], result[j]] = [result[j], result[i]];
    }
    return result;
  }
}