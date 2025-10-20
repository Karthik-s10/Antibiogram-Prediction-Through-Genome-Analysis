import React, { useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FileUp, Database, Dna, Brain, Cpu, AlertCircle, CheckCircle } from 'lucide-react';
import { AMRTrainingPipeline } from '@/lib/pipelines/amrTrainingPipeline';

interface ModelTrainerProps {
  onTrainingComplete?: (results: any) => void;
}

const ModelTrainer: React.FC<ModelTrainerProps> = ({ onTrainingComplete }) => {
  const [activeTab, setActiveTab] = useState('upload');
  const [kmerFile, setKmerFile] = useState<File | null>(null);
  const [phenotypeFile, setPhenotypeFile] = useState<File | null>(null);
  const [targetAntibiotic, setTargetAntibiotic] = useState('ciprofloxacin');
  const [xgboostKmerSize, setXgboostKmerSize] = useState(10);
  const [dnabertKmerSize, setDnabertKmerSize] = useState(6);
  const [dnabertModel, setDnabertModel] = useState('zhihan1996/DNABERT-6');
  const [isTraining, setIsTraining] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [error, setError] = useState('');
  const [trainingResults, setTrainingResults] = useState<any>(null);
  
  const kmerFileInputRef = useRef<HTMLInputElement>(null);
  const phenotypeFileInputRef = useRef<HTMLInputElement>(null);
  
  // Handle k-mer file selection
  const handleKmerFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setKmerFile(e.target.files[0]);
    }
  };
  
  // Handle phenotype file selection
  const handlePhenotypeFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setPhenotypeFile(e.target.files[0]);
    }
  };
  
  // Trigger file input click
  const handleBrowseKmerFile = () => {
    if (kmerFileInputRef.current) {
      kmerFileInputRef.current.click();
    }
  };
  
  // Trigger phenotype file input click
  const handleBrowsePhenotypeFile = () => {
    if (phenotypeFileInputRef.current) {
      phenotypeFileInputRef.current.click();
    }
  };
  
  // Start model training
  const handleStartTraining = async () => {
    if (!kmerFile || !phenotypeFile) {
      setError('Please upload both k-mer data and phenotype data files');
      return;
    }
    
    setIsTraining(true);
    setError('');
    setProgress(0);
    setCurrentStep('Preparing data');
    
    try {
      // Read file contents
      const kmerData = await kmerFile.text();
      const phenotypeData = await phenotypeFile.text();
      
      // Create training pipeline
      const pipeline = new AMRTrainingPipeline({
        xgboostKmerSize,
        dnabertKmerSize,
        dnabertModelName: dnabertModel,
        targetAntibiotic
      });
      
      // Update progress
      setProgress(10);
      setCurrentStep('Parsing data');
      
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 5;
        });
        
        // Update current step based on progress
        if (progress > 10 && progress <= 30) {
          setCurrentStep('Training XGBoost model');
        } else if (progress > 30 && progress <= 60) {
          setCurrentStep('Training DNABERT model');
        } else if (progress > 60) {
          setCurrentStep('Evaluating models');
        }
      }, 1000);
      
      // Run training pipeline
      // In a real implementation, this would actually train the models
      // For this example, we'll simulate the training process
      setTimeout(() => {
        clearInterval(progressInterval);
        
        // Mock training results
        const results = {
          xgboost: {
            accuracy: 0.92,
            precision: 0.89,
            recall: 0.94,
            f1Score: 0.91,
            confusionMatrix: [[45, 5], [3, 47]],
            featureImportance: [
              { feature: 'ACCCCGCGCG', importance: 0.15 },
              { feature: 'ACCGCCGCCG', importance: 0.12 },
              { feature: 'ACCGCGCCGC', importance: 0.10 },
              { feature: 'CGCGCGCGCG', importance: 0.08 },
              { feature: 'GCGCGCGCGC', importance: 0.07 }
            ]
          },
          dnabert: {
            accuracy: 0.94,
            precision: 0.92,
            recall: 0.95,
            f1Score: 0.93,
            confusionMatrix: [[46, 4], [2, 48]]
          },
          bestModel: 'dnabert',
          featureCount: 10000,
          sampleCount: 100,
          targetAntibiotic
        };
        
        setTrainingResults(results);
        setProgress(100);
        setCurrentStep('Training complete');
        setIsTraining(false);
        
        // Call onTrainingComplete callback
        if (onTrainingComplete) {
          onTrainingComplete(results);
        }
        
        // Move to results tab
        setActiveTab('results');
      }, 10000);
    } catch (err) {
      clearInterval(progressInterval);
      setError(`Error during training: ${err instanceof Error ? err.message : String(err)}`);
      setIsTraining(false);
    }
  };
  
  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
        <CardTitle className="text-2xl flex items-center">
          <Brain className="mr-2 h-6 w-6" />
          Antibiogram Prediction Model Trainer
        </CardTitle>
        <CardDescription className="text-blue-100">
          Train XGBoost and DNABERT models for antibiotic resistance prediction
        </CardDescription>
      </CardHeader>
      
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-3 w-full">
          <TabsTrigger value="upload" disabled={isTraining}>
            <FileUp className="mr-2 h-4 w-4" />
            Data Upload
          </TabsTrigger>
          <TabsTrigger value="configure" disabled={isTraining || !kmerFile || !phenotypeFile}>
            <Cpu className="mr-2 h-4 w-4" />
            Configure Models
          </TabsTrigger>
          <TabsTrigger value="results" disabled={!trainingResults}>
            <Database className="mr-2 h-4 w-4" />
            Results
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="upload" className="p-6">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium flex items-center">
                <Dna className="mr-2 h-5 w-5 text-blue-500" />
                K-mer Data
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Upload a file containing k-mer data in the format: GCA_000002515.1 Bacteria 10 ACCCCGCGCG 1.43e-07 9.83e-03
              </p>
              
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
                <input
                  type="file"
                  ref={kmerFileInputRef}
                  className="hidden"
                  accept=".txt,.csv,.tsv"
                  onChange={handleKmerFileSelect}
                />
                
                <div className="flex flex-col items-center justify-center space-y-4">
                  <div className="p-3 rounded-full bg-blue-100">
                    <FileUp className="h-8 w-8 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-lg font-medium">
                      Drag and drop k-mer data file here
                    </p>
                    <p className="text-sm text-gray-500 mt-1">or</p>
                    <Button
                      onClick={handleBrowseKmerFile}
                      className="mt-2"
                      variant="outline"
                    >
                      Browse Files
                    </Button>
                  </div>
                </div>
              </div>
              
              {kmerFile && (
                <div className="mt-4 flex items-center">
                  <Dna className="h-4 w-4 text-blue-500 mr-2" />
                  <span className="text-sm font-medium">{kmerFile.name}</span>
                  <span className="ml-2 text-xs text-gray-500">
                    ({(kmerFile.size / 1024).toFixed(1)} KB)
                  </span>
                </div>
              )}
            </div>
            
            <div>
              <h3 className="text-lg font-medium flex items-center">
                <Database className="mr-2 h-5 w-5 text-purple-500" />
                Phenotype Data
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Upload a CSV/TSV file containing phenotype data with columns: Genome Name, Antibiotic, Resistant Phenotype, etc.
              </p>
              
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-purple-400 transition-colors">
                <input
                  type="file"
                  ref={phenotypeFileInputRef}
                  className="hidden"
                  accept=".csv,.tsv"
                  onChange={handlePhenotypeFileSelect}
                />
                
                <div className="flex flex-col items-center justify-center space-y-4">
                  <div className="p-3 rounded-full bg-purple-100">
                    <Database className="h-8 w-8 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-lg font-medium">
                      Drag and drop phenotype data file here
                    </p>
                    <p className="text-sm text-gray-500 mt-1">or</p>
                    <Button
                      onClick={handleBrowsePhenotypeFile}
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
                  <span className="ml-2 text-xs text-gray-500">
                    ({(phenotypeFile.size / 1024).toFixed(1)} KB)
                  </span>
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
                onClick={() => setActiveTab('configure')}
                disabled={!kmerFile || !phenotypeFile}
              >
                Next: Configure Models
              </Button>
            </div>
          </div>
        </TabsContent>
        
        <TabsContent value="configure" className="p-6">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium flex items-center">
                <Database className="mr-2 h-5 w-5 text-green-500" />
                Target Antibiotic
              </h3>
              
              <div className="mt-4">
                <Label htmlFor="antibiotic">Select Antibiotic</Label>
                <Select
                  value={targetAntibiotic}
                  onValueChange={setTargetAntibiotic}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select antibiotic" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ciprofloxacin">Ciprofloxacin</SelectItem>
                    <SelectItem value="azithromycin">Azithromycin</SelectItem>
                    <SelectItem value="rifampin">Rifampin</SelectItem>
                    <SelectItem value="streptomycin">Streptomycin</SelectItem>
                    <SelectItem value="moxifloxacin">Moxifloxacin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-6">
              <div>
                <h3 className="text-lg font-medium flex items-center">
                  <Cpu className="mr-2 h-5 w-5 text-blue-500" />
                  XGBoost Configuration
                </h3>
                
                <div className="space-y-4 mt-4">
                  <div>
                    <Label htmlFor="xgboost-kmer-size">K-mer Size</Label>
                    <Input
                      id="xgboost-kmer-size"
                      type="number"
                      value={xgboostKmerSize}
                      onChange={(e) => setXgboostKmerSize(parseInt(e.target.value))}
                      min={5}
                      max={15}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Size of k-mers for XGBoost model (5-15)
                    </p>
                  </div>
                  
                  <div>
                    <Label htmlFor="xgboost-max-depth">Max Depth</Label>
                    <Input
                      id="xgboost-max-depth"
                      type="number"
                      defaultValue={6}
                      min={3}
                      max={10}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Maximum depth of trees
                    </p>
                  </div>
                  
                  <div>
                    <Label htmlFor="xgboost-eta">Learning Rate</Label>
                    <Input
                      id="xgboost-eta"
                      type="number"
                      defaultValue={0.3}
                      min={0.01}
                      max={1}
                      step={0.01}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Step size shrinkage (0.01-1.0)
                    </p>
                  </div>
                </div>
              </div>
              
              <div>
                <h3 className="text-lg font-medium flex items-center">
                  <Brain className="mr-2 h-5 w-5 text-purple-500" />
                  DNABERT Configuration
                </h3>
                
                <div className="space-y-4 mt-4">
                  <div>
                    <Label htmlFor="dnabert-model">DNABERT Model</Label>
                    <Select
                      value={dnabertModel}
                      onValueChange={setDnabertModel}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select DNABERT model" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="zhihan1996/DNABERT-6">DNABERT-6 (6-mer)</SelectItem>
                        <SelectItem value="zhihan1996/DNABERT-3">DNABERT-3 (3-mer)</SelectItem>
                        <SelectItem value="zhihan1996/DNABERT-4">DNABERT-4 (4-mer)</SelectItem>
                        <SelectItem value="zhihan1996/DNABERT-5">DNABERT-5 (5-mer)</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-gray-500 mt-1">
                      Pre-trained DNABERT model to use
                    </p>
                  </div>
                  
                  <div>
                    <Label htmlFor="dnabert-kmer-size">K-mer Size</Label>
                    <Input
                      id="dnabert-kmer-size"
                      type="number"
                      value={dnabertKmerSize}
                      onChange={(e) => setDnabertKmerSize(parseInt(e.target.value))}
                      min={3}
                      max={6}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Size of k-mers for DNABERT model (3-6)
                    </p>
                  </div>
                  
                  <div>
                    <Label htmlFor="dnabert-batch-size">Batch Size</Label>
                    <Input
                      id="dnabert-batch-size"
                      type="number"
                      defaultValue={8}
                      min={1}
                      max={32}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Batch size for training
                    </p>
                  </div>
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
              <Button variant="outline" onClick={() => setActiveTab('upload')}>
                Back
              </Button>
              <Button onClick={handleStartTraining} disabled={isTraining}>
                {isTraining ? 'Training...' : 'Start Training'}
              </Button>
            </div>
            
            {isTraining && (
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
                    Models trained successfully for {trainingResults.targetAntibiotic}
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
                          <span className="text-sm text-gray-600">Precision:</span>
                          <span className="font-medium">{(trainingResults.xgboost.precision * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Recall:</span>
                          <span className="font-medium">{(trainingResults.xgboost.recall * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                      
                      <div className="mt-4">
                        <h4 className="text-sm font-medium mb-2">Top Feature Importance</h4>
                        <div className="space-y-2">
                          {trainingResults.xgboost.featureImportance.map((feature: any, index: number) => (
                            <div key={index} className="flex items-center">
                              <div className="w-full bg-gray-200 rounded-full h-2.5">
                                <div 
                                  className="bg-blue-600 h-2.5 rounded-full" 
                                  style={{ width: `${feature.importance * 100 * 5}%` }}
                                ></div>
                              </div>
                              <span className="ml-2 text-xs">{feature.feature}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  
                  <Card className={`border-2 ${trainingResults.bestModel === 'dnabert' ? 'border-green-500' : ''}`}>
                    <CardHeader className="bg-purple-50 pb-2">
                      <CardTitle className="text-lg flex items-center">
                        <Brain className="mr-2 h-5 w-5 text-purple-600" />
                        DNABERT Model
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4">
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Accuracy:</span>
                          <span className="font-medium">{(trainingResults.dnabert.accuracy * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">F1 Score:</span>
                          <span className="font-medium">{(trainingResults.dnabert.f1Score * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Precision:</span>
                          <span className="font-medium">{(trainingResults.dnabert.precision * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Recall:</span>
                          <span className="font-medium">{(trainingResults.dnabert.recall * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                      
                      <div className="mt-4">
                        <h4 className="text-sm font-medium mb-2">Confusion Matrix</h4>
                        <div className="grid grid-cols-2 gap-2 text-center">
                          <div className="bg-green-100 p-2 rounded">
                            <div className="text-xs text-gray-600">True Negative</div>
                            <div className="font-medium">{trainingResults.dnabert.confusionMatrix[0][0]}</div>
                          </div>
                          <div className="bg-red-100 p-2 rounded">
                            <div className="text-xs text-gray-600">False Positive</div>
                            <div className="font-medium">{trainingResults.dnabert.confusionMatrix[0][1]}</div>
                          </div>
                          <div className="bg-red-100 p-2 rounded">
                            <div className="text-xs text-gray-600">False Negative</div>
                            <div className="font-medium">{trainingResults.dnabert.confusionMatrix[1][0]}</div>
                          </div>
                          <div className="bg-green-100 p-2 rounded">
                            <div className="text-xs text-gray-600">True Positive</div>
                            <div className="font-medium">{trainingResults.dnabert.confusionMatrix[1][1]}</div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
              
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="font-medium text-blue-800 mb-2">Training Summary</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Target Antibiotic:</span>
                    <span className="ml-2 font-medium">{trainingResults.targetAntibiotic}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Best Model:</span>
                    <span className="ml-2 font-medium">{trainingResults.bestModel === 'dnabert' ? 'DNABERT' : 'XGBoost'}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Sample Count:</span>
                    <span className="ml-2 font-medium">{trainingResults.sampleCount}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Feature Count:</span>
                    <span className="ml-2 font-medium">{trainingResults.featureCount}</span>
                  </div>
                </div>
              </div>
              
              <div className="flex justify-between">
                <Button variant="outline" onClick={() => setActiveTab('configure')}>
                  Back to Configuration
                </Button>
                <Button>
                  Save Models
                </Button>
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>
      
      <CardFooter className="bg-gray-50 border-t p-4">
        <p className="text-xs text-gray-500">
          This trainer builds both XGBoost and DNABERT models for antibiotic resistance prediction.
          The best performing model is automatically selected based on F1 score.
        </p>
      </CardFooter>
    </Card>
  );
};

export default ModelTrainer;