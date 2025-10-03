import React, { useState, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { 
  FileUp, 
  Database, 
  Dna, 
  Braces, 
  BarChart, 
  CheckCircle, 
  AlertCircle,
  Layers,
  Cpu,
  Brain,
  Save
} from "lucide-react";

interface MLPipelineProps {
  onTrainingComplete?: (results: any) => void;
}

const MLPipeline: React.FC<MLPipelineProps> = ({ 
  onTrainingComplete = () => {} 
}) => {
  const [activeTab, setActiveTab] = useState("data-upload");
  const [genomeFiles, setGenomeFiles] = useState<File[]>([]);
  const [phenotypeFile, setPhenotypeFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState("");
  const [error, setError] = useState("");
  const [trainingResults, setTrainingResults] = useState<any>(null);
  
  const genomeInputRef = useRef<HTMLInputElement>(null);
  const phenotypeInputRef = useRef<HTMLInputElement>(null);
  
  // Handle genome files selection
  const handleGenomeFilesSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      setGenomeFiles(files);
    }
  };
  
  // Handle phenotype file selection
  const handlePhenotypeFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setPhenotypeFile(e.target.files[0]);
    }
  };
  
  // Trigger file input click
  const handleBrowseGenomesClick = () => {
    if (genomeInputRef.current) {
      genomeInputRef.current.click();
    }
  };
  
  // Trigger phenotype file input click
  const handleBrowsePhenotypeClick = () => {
    if (phenotypeInputRef.current) {
      phenotypeInputRef.current.click();
    }
  };
  
  // Start the training pipeline
  const handleStartTraining = async () => {
    if (genomeFiles.length === 0 || !phenotypeFile) {
      setError("Please upload both genome files and phenotype data");
      return;
    }
    
    setIsProcessing(true);
    setError("");
    setProgress(0);
    
    try {
      // Simulate the training pipeline steps
      await simulateFeatureEngineering();
      await simulateModelTraining();
      await simulateModelEvaluation();
      
      // Generate mock training results
      const mockResults = generateMockTrainingResults();
      setTrainingResults(mockResults);
      onTrainingComplete(mockResults);
      
      // Move to results tab
      setActiveTab("results");
    } catch (err) {
      setError(`Error during training: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Simulate feature engineering step
  const simulateFeatureEngineering = async () => {
    setCurrentStep("Feature Engineering");
    
    for (let i = 0; i <= 30; i++) {
      setProgress(i);
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  };
  
  // Simulate model training step
  const simulateModelTraining = async () => {
    setCurrentStep("Model Training");
    
    for (let i = 31; i <= 80; i++) {
      setProgress(i);
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  };
  
  // Simulate model evaluation step
  const simulateModelEvaluation = async () => {
    setCurrentStep("Model Evaluation");
    
    for (let i = 81; i <= 100; i++) {
      setProgress(i);
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  };
  
  // Generate mock training results
  const generateMockTrainingResults = () => {
    return {
      xgboost: {
        accuracy: 0.92,
        f1Score: 0.89,
        jaccardScore: 0.85,
        trainTime: 45.2,
        featureImportance: [
          { feature: "kmer_ACGTA", importance: 0.58 },
          { feature: "kmer_TCGAT", importance: 0.42 },
          { feature: "kmer_GCTAT", importance: 0.37 },
          { feature: "kmer_ATGCA", importance: 0.31 },
          { feature: "kmer_CGATA", importance: 0.28 }
        ]
      },
      transformer: {
        accuracy: 0.94,
        f1Score: 0.91,
        jaccardScore: 0.88,
        trainTime: 128.7,
        attentionScores: [0.62, 0.58, 0.47, 0.39, 0.31]
      },
      bestModel: "transformer",
      modelSize: 8.7, // MB
      trainingTime: 173.9, // seconds
      timestamp: new Date().toISOString()
    };
  };
  
  return (
    <Card className="w-full max-w-4xl mx-auto bg-white shadow-lg">
      <CardHeader className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
        <CardTitle className="text-2xl flex items-center">
          <Brain className="mr-2 h-6 w-6" />
          ML Pipeline for Antibiogram Prediction
        </CardTitle>
        <CardDescription className="text-blue-100">
          Train and evaluate machine learning models for predicting antibiotic resistance
        </CardDescription>
      </CardHeader>
      
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid grid-cols-3 w-full">
          <TabsTrigger value="data-upload" disabled={isProcessing}>
            <Database className="mr-2 h-4 w-4" />
            Data Upload
          </TabsTrigger>
          <TabsTrigger value="training" disabled={isProcessing || genomeFiles.length === 0 || !phenotypeFile}>
            <Cpu className="mr-2 h-4 w-4" />
            Training
          </TabsTrigger>
          <TabsTrigger value="results" disabled={!trainingResults}>
            <BarChart className="mr-2 h-4 w-4" />
            Results
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="data-upload" className="p-6">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium flex items-center">
                <Dna className="mr-2 h-5 w-5 text-blue-500" />
                Genome Files (FASTA)
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Upload multiple bacterial genome files in FASTA format (.fasta or .fa)
              </p>
              
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
                <input
                  type="file"
                  ref={genomeInputRef}
                  className="hidden"
                  accept=".fasta,.fa"
                  multiple
                  onChange={handleGenomeFilesSelect}
                />
                
                <div className="flex flex-col items-center justify-center space-y-4">
                  <div className="p-3 rounded-full bg-blue-100">
                    <FileUp className="h-8 w-8 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-lg font-medium">
                      Drag and drop genome files here
                    </p>
                    <p className="text-sm text-gray-500 mt-1">or</p>
                    <Button
                      onClick={handleBrowseGenomesClick}
                      className="mt-2"
                      variant="outline"
                    >
                      Browse Files
                    </Button>
                  </div>
                </div>
              </div>
              
              {genomeFiles.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-medium text-gray-700">
                    {genomeFiles.length} genome files selected
                  </p>
                  <div className="mt-2 max-h-32 overflow-y-auto">
                    {genomeFiles.map((file, index) => (
                      <div key={index} className="flex items-center py-1">
                        <Dna className="h-4 w-4 text-blue-500 mr-2" />
                        <span className="text-sm">{file.name}</span>
                        <Badge className="ml-2 bg-blue-100 text-blue-800 text-xs">
                          {(file.size / 1024).toFixed(1)} KB
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            
            <Separator />
            
            <div>
              <h3 className="text-lg font-medium flex items-center">
                <Braces className="mr-2 h-5 w-5 text-purple-500" />
                Phenotype Data (CSV)
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Upload a CSV file containing antibiotic resistance phenotypes for the genomes
              </p>
              
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-purple-400 transition-colors">
                <input
                  type="file"
                  ref={phenotypeInputRef}
                  className="hidden"
                  accept=".csv"
                  onChange={handlePhenotypeFileSelect}
                />
                
                <div className="flex flex-col items-center justify-center space-y-4">
                  <div className="p-3 rounded-full bg-purple-100">
                    <Database className="h-8 w-8 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-lg font-medium">
                      Drag and drop phenotype CSV file here
                    </p>
                    <p className="text-sm text-gray-500 mt-1">or</p>
                    <Button
                      onClick={handleBrowsePhenotypeClick}
                      className="mt-2"
                      variant="outline"
                    >
                      Browse Files
                    </Button>
                  </div>
                </div>
              </div>
              
              {phenotypeFile && (
                <div className="mt-4 flex items-center">
                  <Database className="h-4 w-4 text-purple-500 mr-2" />
                  <span className="text-sm font-medium">{phenotypeFile.name}</span>
                  <Badge className="ml-2 bg-purple-100 text-purple-800 text-xs">
                    {(phenotypeFile.size / 1024).toFixed(1)} KB
                  </Badge>
                </div>
              )}
            </div>
            
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            <div className="flex justify-end">
              <Button
                onClick={() => setActiveTab("training")}
                disabled={genomeFiles.length === 0 || !phenotypeFile}
              >
                Next: Configure Training
              </Button>
            </div>
          </div>
        </TabsContent>
        
        <TabsContent value="training" className="p-6">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium flex items-center">
                <Layers className="mr-2 h-5 w-5 text-blue-500" />
                Feature Engineering
              </h3>
              
              <div className="grid grid-cols-2 gap-4 mt-4">
                <div>
                  <Label htmlFor="kmer-size">K-mer Size</Label>
                  <Input id="kmer-size" type="number" defaultValue="5" min="3" max="10" />
                  <p className="text-xs text-gray-500 mt-1">
                    Length of k-mer sequences to extract (3-10)
                  </p>
                </div>
                
                <div>
                  <Label htmlFor="max-features">Max Features</Label>
                  <Input id="max-features" type="number" defaultValue="10000" min="1000" max="100000" />
                  <p className="text-xs text-gray-500 mt-1">
                    Maximum number of features to use
                  </p>
                </div>
              </div>
            </div>
            
            <Separator />
            
            <div className="grid grid-cols-2 gap-6">
              <div>
                <h3 className="text-lg font-medium flex items-center">
                  <Cpu className="mr-2 h-5 w-5 text-green-500" />
                  XGBoost Parameters
                </h3>
                
                <div className="space-y-3 mt-4">
                  <div>
                    <Label htmlFor="learning-rate">Learning Rate</Label>
                    <Input id="learning-rate" type="number" defaultValue="0.1" min="0.01" max="1" step="0.01" />
                  </div>
                  
                  <div>
                    <Label htmlFor="max-depth">Max Depth</Label>
                    <Input id="max-depth" type="number" defaultValue="6" min="3" max="15" />
                  </div>
                  
                  <div>
                    <Label htmlFor="n-estimators">Number of Estimators</Label>
                    <Input id="n-estimators" type="number" defaultValue="100" min="50" max="500" />
                  </div>
                </div>
              </div>
              
              <div>
                <h3 className="text-lg font-medium flex items-center">
                  <Brain className="mr-2 h-5 w-5 text-purple-500" />
                  Transformer Parameters
                </h3>
                
                <div className="space-y-3 mt-4">
                  <div>
                    <Label htmlFor="num-layers">Number of Layers</Label>
                    <Input id="num-layers" type="number" defaultValue="4" min="2" max="12" />
                  </div>
                  
                  <div>
                    <Label htmlFor="num-heads">Number of Attention Heads</Label>
                    <Input id="num-heads" type="number" defaultValue="8" min="4" max="16" />
                  </div>
                  
                  <div>
                    <Label htmlFor="hidden-size">Hidden Size</Label>
                    <Input id="hidden-size" type="number" defaultValue="512" min="128" max="1024" step="64" />
                  </div>
                </div>
              </div>
            </div>
            
            <Separator />
            
            <div>
              <h3 className="text-lg font-medium flex items-center">
                <BarChart className="mr-2 h-5 w-5 text-orange-500" />
                Evaluation Settings
              </h3>
              
              <div className="grid grid-cols-2 gap-4 mt-4">
                <div>
                  <Label htmlFor="validation-split">Validation Split</Label>
                  <Input id="validation-split" type="number" defaultValue="0.2" min="0.1" max="0.5" step="0.05" />
                  <p className="text-xs text-gray-500 mt-1">
                    Proportion of data to use for validation (0.1-0.5)
                  </p>
                </div>
                
                <div>
                  <Label htmlFor="random-seed">Random Seed</Label>
                  <Input id="random-seed" type="number" defaultValue="42" min="1" max="1000" />
                  <p className="text-xs text-gray-500 mt-1">
                    Seed for reproducible results
                  </p>
                </div>
              </div>
            </div>
            
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setActiveTab("data-upload")}>
                Back
              </Button>
              <Button onClick={handleStartTraining} disabled={isProcessing}>
                {isProcessing ? "Training..." : "Start Training"}
              </Button>
            </div>
            
            {isProcessing && (
              <div className="mt-4 space-y-4">
                <div className="flex justify-between items-center">
                  <span className="font-medium">{currentStep}</span>
                  <span className="font-medium">{progress}%</span>
                </div>
                <Progress value={progress} className="h-2" />
                <p className="text-sm text-gray-500 text-center animate-pulse">
                  This may take several minutes depending on the dataset size and model complexity
                </p>
              </div>
            )}
          </div>
        </TabsContent>
        
        <TabsContent value="results" className="p-6">
          {trainingResults && (
            <div className="space-y-6">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center">
                <CheckCircle className="h-6 w-6 text-green-600 mr-3" />
                <div>
                  <h3 className="font-medium text-green-800">Training Complete</h3>
                  <p className="text-sm text-green-700">
                    Models trained successfully in {trainingResults.trainingTime.toFixed(1)} seconds
                  </p>
                </div>
              </div>
              
              <div>
                <h3 className="text-lg font-medium mb-4">Model Comparison</h3>
                
                <div className="grid grid-cols-2 gap-6">
                  <Card className={`border-2 ${trainingResults.bestModel === 'xgboost' ? 'border-green-500' : ''}`}>
                    <CardHeader className="bg-blue-50 pb-2">
                      <CardTitle className="text-lg flex items-center">
                        <Cpu className="mr-2 h-5 w-5 text-blue-600" />
                        XGBoost Model
                        {trainingResults.bestModel === 'xgboost' && (
                          <Badge className="ml-2 bg-green-100 text-green-800">Best</Badge>
                        )}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4">
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Accuracy:</span>
                          <span className="font-medium">{(trainingResults.xgboost.accuracy * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">F1 Score:</span>
                          <span className="font-medium">{(trainingResults.xgboost.f1Score * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Jaccard Score:</span>
                          <span className="font-medium">{(trainingResults.xgboost.jaccardScore * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Training Time:</span>
                          <span className="font-medium">{trainingResults.xgboost.trainTime.toFixed(1)} sec</span>
                        </div>
                      </div>
                      
                      <Separator className="my-4" />
                      
                      <div>
                        <h4 className="text-sm font-medium mb-2">Top Feature Importance</h4>
                        <div className="space-y-2">
                          {trainingResults.xgboost.featureImportance.map((feature, index) => (
                            <div key={index} className="flex items-center">
                              <div className="w-full bg-gray-200 rounded-full h-2.5">
                                <div 
                                  className="bg-blue-600 h-2.5 rounded-full" 
                                  style={{ width: `${feature.importance * 100}%` }}
                                ></div>
                              </div>
                              <span className="ml-2 text-xs">{feature.feature}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  
                  <Card className={`border-2 ${trainingResults.bestModel === 'transformer' ? 'border-green-500' : ''}`}>
                    <CardHeader className="bg-purple-50 pb-2">
                      <CardTitle className="text-lg flex items-center">
                        <Brain className="mr-2 h-5 w-5 text-purple-600" />
                        Transformer Model
                        {trainingResults.bestModel === 'transformer' && (
                          <Badge className="ml-2 bg-green-100 text-green-800">Best</Badge>
                        )}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4">
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Accuracy:</span>
                          <span className="font-medium">{(trainingResults.transformer.accuracy * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">F1 Score:</span>
                          <span className="font-medium">{(trainingResults.transformer.f1Score * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Jaccard Score:</span>
                          <span className="font-medium">{(trainingResults.transformer.jaccardScore * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Training Time:</span>
                          <span className="font-medium">{trainingResults.transformer.trainTime.toFixed(1)} sec</span>
                        </div>
                      </div>
                      
                      <Separator className="my-4" />
                      
                      <div>
                        <h4 className="text-sm font-medium mb-2">Attention Visualization</h4>
                        <div className="grid grid-cols-5 gap-1">
                          {trainingResults.transformer.attentionScores.map((score, index) => (
                            <div key={index} className="flex flex-col items-center">
                              <div 
                                className="bg-purple-500 rounded-md w-full" 
                                style={{ height: `${score * 60}px` }}
                              ></div>
                              <span className="text-xs mt-1">H{index+1}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
              
              <div className="flex justify-between">
                <Button variant="outline" onClick={() => setActiveTab("training")}>
                  Back to Training
                </Button>
                <Button>
                  <Save className="mr-2 h-4 w-4" />
                  Save Best Model
                </Button>
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>
      
      <CardFooter className="bg-gray-50 border-t p-4">
        <p className="text-xs text-gray-500">
          This pipeline trains both XGBoost and Transformer models on genomic data to predict antibiotic resistance.
          The best performing model is automatically selected based on accuracy metrics.
        </p>
      </CardFooter>
    </Card>
  );
};

export default MLPipeline;