import { FeatureEngineering, KmerFeatures, FeatureEngineeringOptions } from './featureEngineering';
import { XGBoostModel, XGBoostParameters, ModelTrainingResult } from './xgboostModel';
import { TransformerModel, TransformerParameters } from './transformerModel';

export interface TrainingData {
  genomeFiles: string[];  // FASTA content
  sampleIds: string[];
  phenotypes: string[];   // Antibiotic resistance labels (S, I, R)
  antibioticName: string;
}

export interface ModelEvaluationResult {
  modelName: string;
  trainingResult: ModelTrainingResult;
  modelParameters: any;
  featureEngineeringOptions: FeatureEngineeringOptions;
  timestamp: string;
}

export interface TrainingPipelineOptions {
  featureEngineeringOptions?: Partial<FeatureEngineeringOptions>;
  xgboostParameters?: Partial<XGBoostParameters>;
  transformerParameters?: Partial<TransformerParameters>;
  validationSplit?: number;
  randomSeed?: number;
}

export class ModelTrainingPipeline {
  private featureEngineering: FeatureEngineering;
  private xgboostModel: XGBoostModel;
  private transformerModel: TransformerModel;
  private options: TrainingPipelineOptions;
  
  constructor(options?: TrainingPipelineOptions) {
    this.options = {
      validationSplit: 0.2,
      randomSeed: 42,
      ...options
    };
    
    this.featureEngineering = new FeatureEngineering(options?.featureEngineeringOptions);
    this.xgboostModel = new XGBoostModel(options?.xgboostParameters);
    this.transformerModel = new TransformerModel(options?.transformerParameters);
  }
  
  /**
   * Run the complete training pipeline
   * @param trainingData - Training data including genomes and phenotypes
   */
  public async runTrainingPipeline(trainingData: TrainingData): Promise<ModelEvaluationResult[]> {
    console.log(`Starting training pipeline for ${trainingData.antibioticName}`);
    console.log(`Training data: ${trainingData.genomeFiles.length} samples`);
    
    // Step 1: Feature Engineering
    const features = this.featureEngineering.extractKmerFeatures(
      trainingData.genomeFiles,
      trainingData.sampleIds
    );
    
    // Step 2: Split data into training and validation sets
    const { trainFeatures, trainLabels, valFeatures, valLabels } = 
      this.splitTrainingData(features.featureMatrix, trainingData.phenotypes);
    
    console.log(`Training set: ${trainFeatures.length} samples`);
    console.log(`Validation set: ${valFeatures.length} samples`);
    
    // Step 3: Train both models in parallel
    const [xgboostResult, transformerResult] = await Promise.all([
      this.trainXGBoost(trainFeatures, trainLabels),
      this.trainTransformer(trainFeatures, trainLabels)
    ]);
    
    // Step 4: Evaluate models and select the best one
    const results: ModelEvaluationResult[] = [
      {
        modelName: 'XGBoost',
        trainingResult: xgboostResult,
        modelParameters: this.options.xgboostParameters || {},
        featureEngineeringOptions: this.featureEngineering['options'],
        timestamp: new Date().toISOString()
      },
      {
        modelName: 'Transformer',
        trainingResult: transformerResult,
        modelParameters: this.options.transformerParameters || {},
        featureEngineeringOptions: this.featureEngineering['options'],
        timestamp: new Date().toISOString()
      }
    ];
    
    // Sort by accuracy (descending)
    results.sort((a, b) => b.trainingResult.accuracy - a.trainingResult.accuracy);
    
    console.log(`Best model: ${results[0].modelName} with accuracy ${results[0].trainingResult.accuracy.toFixed(4)}`);
    
    return results;
  }
  
  /**
   * Save the best model based on evaluation results
   * @param results - Model evaluation results
   * @param outputPath - Path to save the model
   */
  public saveBestModel(results: ModelEvaluationResult[], outputPath: string): void {
    if (results.length === 0) {
      throw new Error("No model evaluation results provided");
    }
    
    // Select the best model based on accuracy
    const bestResult = results[0];
    
    if (bestResult.modelName === 'XGBoost') {
      this.xgboostModel.saveModel(`${outputPath}/xgboost_model.pkl`);
    } else {
      this.transformerModel.saveModel(`${outputPath}/transformer_model.pkl`);
    }
    
    // Save feature engineering dictionary for future use
    const kmerDictionary = this.featureEngineering.saveKmerDictionary();
    console.log(`K-mer dictionary saved with ${kmerDictionary.length} characters`);
    
    // Save model metadata
    const metadata = {
      modelName: bestResult.modelName,
      accuracy: bestResult.trainingResult.accuracy,
      f1Score: bestResult.trainingResult.f1Score,
      trainedAt: bestResult.timestamp,
      featureEngineeringOptions: bestResult.featureEngineeringOptions
    };
    
    console.log(`Model metadata: ${JSON.stringify(metadata, null, 2)}`);
    console.log(`Best model saved to ${outputPath}`);
  }
  
  /**
   * Train the XGBoost model
   * @param features - Training features
   * @param labels - Training labels
   */
  private async trainXGBoost(features: number[][], labels: string[]): Promise<ModelTrainingResult> {
    console.log('Training XGBoost model...');
    return this.xgboostModel.train(features, labels, this.options.validationSplit);
  }
  
  /**
   * Train the Transformer model
   * @param features - Training features
   * @param labels - Training labels
   */
  private async trainTransformer(features: number[][], labels: string[]): Promise<ModelTrainingResult> {
    console.log('Training Transformer model...');
    return this.transformerModel.train(features, labels, this.options.validationSplit);
  }
  
  /**
   * Split data into training and validation sets
   * @param features - Feature matrix
   * @param labels - Labels
   */
  private splitTrainingData(features: number[][], labels: string[]) {
    const validationSize = Math.floor(features.length * (this.options.validationSplit || 0.2));
    const indices = this.shuffleArray([...Array(features.length).keys()]);
    
    const trainIndices = indices.slice(validationSize);
    const valIndices = indices.slice(0, validationSize);
    
    const trainFeatures = trainIndices.map(i => features[i]);
    const trainLabels = trainIndices.map(i => labels[i]);
    const valFeatures = valIndices.map(i => features[i]);
    const valLabels = valIndices.map(i => labels[i]);
    
    return { trainFeatures, trainLabels, valFeatures, valLabels };
  }
  
  /**
   * Shuffle an array using Fisher-Yates algorithm
   * @param array - Array to shuffle
   */
  private shuffleArray<T>(array: T[]): T[] {
    const result = [...array];
    const seed = this.options.randomSeed || 42;
    let m = result.length;
    
    // Fisher-Yates shuffle with seeded random
    while (m) {
      // Generate seeded random number
      const seedRandom = this.seededRandom(seed + m);
      const i = Math.floor(seedRandom * m--);
      [result[m], result[i]] = [result[i], result[m]];
    }
    
    return result;
  }
  
  /**
   * Simple seeded random number generator
   * @param seed - Random seed
   */
  private seededRandom(seed: number): number {
    const x = Math.sin(seed) * 10000;
    return x - Math.floor(x);
  }
}