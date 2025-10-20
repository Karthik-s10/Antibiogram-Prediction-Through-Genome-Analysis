import React, { useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { FileUp, AlertCircle, CheckCircle, Search, Dna, Database } from 'lucide-react';
import { AMRTrainingPipeline } from '@/lib/pipelines/amrTrainingPipeline';

interface GenomePredictorProps {
  onPredictionComplete?: (result: any) => void;
  targetAntibiotic?: string;
}

const GenomePredictor: React.FC<GenomePredictorProps> = ({
  onPredictionComplete,
  targetAntibiotic = 'ciprofloxacin'
}) => {
  const [activeTab, setActiveTab] = useState('upload');
  const [genomeFile, setGenomeFile] = useState<File | null>(null);
  const [isPredicting, setIsPredicting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [error, setError] = useState('');
  const [predictionResult, setPredictionResult] = useState<any>(null);
  
  const genomeFileInputRef = useRef<HTMLInputElement>(null);
  
  // Handle genome file selection
  const handleGenomeFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setGenomeFile(e.target.files[0]);
    }
  };
  
  // Trigger file input click
  const handleBrowseGenomeFile = () => {
    if (genomeFileInputRef.current) {
      genomeFileInputRef.current.click();
    }
  };
  
  // Start prediction
  const handleStartPrediction = async () => {
    if (!genomeFile) {
      setError('Please upload a genome FASTA file');
      return;
    }
    
    setIsPredicting(true);
    setError('');
    setProgress(0);
    setCurrentStep('Preparing genome');
    
    try {
      // Read file content
      const fastaContent = await genomeFile.text();
      
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
        
        // Update current step based on progress
        if (progress > 10 && progress <= 30) {
          setCurrentStep('Extracting k-mers');
        } else if (progress > 30 && progress <= 60) {
          setCurrentStep('Running prediction models');
        } else if (progress > 60) {
          setCurrentStep('Finding similar genomes');
        }
      }, 500);
      
      // In a real implementation, this would use the AMRTrainingPipeline to make predictions
      // For this example, we'll simulate the prediction process
      setTimeout(() => {
        clearInterval(progressInterval);
        
        // Mock prediction result
        const result = {
          prediction: Math.random() > 0.5 ? 'R' : 'S',
          confidence: 0.92,
          model: Math.random() > 0.5 ? 'xgboost' : 'dnabert',
          antibiotic: targetAntibiotic,
          genomeName: genomeFile.name.replace(/\.[^/.]+$/, ''),
          similarGenomes: [
            {
              genomeId: 'GCA_000002515.1',
              score: 0.95,
              prediction: 'R',
              taxonomy: 'Bacteria'
            },
            {
              genomeId: 'GCA_000003215.2',
              score: 0.87,
              prediction: 'R',
              taxonomy: 'Bacteria'
            },
            {
              genomeId: 'GCA_000004125.3',
              score: 0.82,
              prediction: 'S',
              taxonomy: 'Bacteria'
            }
          ]
        };
        
        setPredictionResult(result);
        setProgress(100);
        setCurrentStep('Prediction complete');
        setIsPredicting(false);
        
        // Call onPredictionComplete callback
        if (onPredictionComplete) {
          onPredictionComplete(result);
        }
        
        // Move to results tab
        setActiveTab('results');
      }, 3000);
    } catch (err) {
      clearInterval(progressInterval);
      setError(`Error during prediction: ${err instanceof Error ? err.message : String(err)}`);
      setIsPredicting(false);
    }
  };
  
  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader className="bg-gradient-to-r from-blue-600 to-green-600 text-white">
        <CardTitle className="text-2xl flex items-center">
          <Search className="mr-2 h-6 w-6" />
          Antibiogram Predictor
        </CardTitle>
        <CardDescription className="text-blue-100">
          Predict antibiotic resistance from bacterial genome sequences
        </CardDescription>
      </CardHeader>
      
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-2 w-full">
          <TabsTrigger value="upload" disabled={isPredicting}>
            <FileUp className="mr-2 h-4 w-4" />
            Upload Genome
          </TabsTrigger>
          <TabsTrigger value="results" disabled={!predictionResult}>
            <Database className="mr-2 h-4 w-4" />
            Prediction Results
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="upload" className="p-6">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium flex items-center">
                <Dna className="mr-2 h-5 w-5 text-blue-500" />
                Genome FASTA File
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Upload a bacterial genome in FASTA format (.fasta or .fa)
              </p>
              
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
                <input
                  type="file"
                  ref={genomeFileInputRef}
                  className="hidden"
                  accept=".fasta,.fa,.fna"
                  onChange={handleGenomeFileSelect}
                />
                
                <div className="flex flex-col items-center justify-center space-y-4">
                  <div className="p-3 rounded-full bg-blue-100">
                    <FileUp className="h-8 w-8 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-lg font-medium">
                      Drag and drop genome FASTA file here
                    </p>
                    <p className="text-sm text-gray-500 mt-1">or</p>
                    <Button
                      onClick={handleBrowseGenomeFile}
                      className="mt-2"
                      variant="outline"
                    >
                      Browse Files
                    </Button>
                  </div>
                </div>
              </div>
              
              {genomeFile && (
                <div className="mt-4 flex items-center">
                  <Dna className="h-4 w-4 text-blue-500 mr-2" />
                  <span className="text-sm font-medium">{genomeFile.name}</span>
                  <span className="ml-2 text-xs text-gray-500">
                    ({(genomeFile.size / 1024).toFixed(1)} KB)
                  </span>
                </div>
              )}
            </div>
            
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-medium text-blue-800 mb-2">Target Antibiotic</h3>
              <p className="text-sm text-blue-700">
                Predicting resistance to <span className="font-medium">{targetAntibiotic}</span>
              </p>
              <p className="text-xs text-blue-600 mt-2">
                The prediction will use pre-trained models for this antibiotic
              </p>
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
                onClick={handleStartPrediction}
                disabled={!genomeFile || isPredicting}
              >
                {isPredicting ? 'Predicting...' : 'Start Prediction'}
              </Button>
            </div>
            
            {isPredicting && (
              <div className="mt-4 space-y-4">
                <div className="flex justify-between items-center">
                  <span className="font-medium">{currentStep}</span>
                  <span className="font-medium">{progress}%</span>
                </div>
                <Progress value={progress} className="h-2" />
                <p className="text-sm text-gray-500 text-center animate-pulse">
                  Analyzing genome sequence and predicting antibiotic resistance
                </p>
              </div>
            )}
          </div>
        </TabsContent>
        
        <TabsContent value="results" className="p-6">
          {predictionResult && (
            <div className="space-y-6">
              <div className={`bg-${predictionResult.prediction === 'R' ? 'red' : 'green'}-50 border border-${predictionResult.prediction === 'R' ? 'red' : 'green'}-200 rounded-lg p-4 flex items-center`}>
                <CheckCircle className={`h-6 w-6 text-${predictionResult.prediction === 'R' ? 'red' : 'green'}-600 mr-3`} />
                <div>
                  <h3 className={`font-medium text-${predictionResult.prediction === 'R' ? 'red' : 'green'}-800`}>
                    {predictionResult.prediction === 'R' ? 'Resistant' : 'Susceptible'}
                  </h3>
                  <p className={`text-sm text-${predictionResult.prediction === 'R' ? 'red' : 'green'}-700`}>
                    {predictionResult.genomeName} is predicted to be {predictionResult.prediction === 'R' ? 'resistant' : 'susceptible'} to {predictionResult.antibiotic}
                  </p>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-6">
                <Card>
                  <CardHeader className="bg-blue-50 pb-2">
                    <CardTitle className="text-lg">Prediction Details</CardTitle>
                  </CardHeader>
                  <CardContent className="pt-4">
                    <div className="space-y-4">
                      <div>
                        <div className="text-sm text-gray-600 mb-1">Confidence</div>
                        <div className="flex items-center">
                          <div className="w-full bg-gray-200 rounded-full h-2.5 mr-2">
                            <div 
                              className={`bg-${predictionResult.prediction === 'R' ? 'red' : 'green'}-600 h-2.5 rounded-full`}
                              style={{ width: `${predictionResult.confidence * 100}%` }}
                            ></div>
                          </div>
                          <span className="text-sm font-medium">
                            {(predictionResult.confidence * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <div className="text-sm text-gray-600 mb-1">Model Used</div>
                          <div className="font-medium flex items-center">
                            {predictionResult.model === 'xgboost' ? (
                              <>
                                <Database className="h-4 w-4 mr-1 text-blue-600" />
                                XGBoost
                              </>
                            ) : (
                              <>
                                <Dna className="h-4 w-4 mr-1 text-purple-600" />
                                DNABERT
                              </>
                            )}
                          </div>
                        </div>
                        
                        <div>
                          <div className="text-sm text-gray-600 mb-1">Antibiotic</div>
                          <div className="font-medium capitalize">
                            {predictionResult.antibiotic}
                          </div>
                        </div>
                      </div>
                      
                      <div>
                        <div className="text-sm text-gray-600 mb-1">Genome File</div>
                        <div className="font-medium">
                          {predictionResult.genomeName}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader className="bg-blue-50 pb-2">
                    <CardTitle className="text-lg">Similar Genomes</CardTitle>
                  </CardHeader>
                  <CardContent className="pt-4">
                    <div className="space-y-4">
                      {predictionResult.similarGenomes.map((genome: any, index: number) => (
                        <div key={index} className="flex items-center justify-between">
                          <div>
                            <div className="font-medium">{genome.genomeId}</div>
                            <div className="text-xs text-gray-500">{genome.taxonomy}</div>
                          </div>
                          <div className="flex items-center space-x-2">
                            <div className="text-sm">
                              {(genome.score * 100).toFixed(1)}% match
                            </div>
                            <Badge className={`bg-${genome.prediction === 'R' ? 'red' : 'green'}-100 text-${genome.prediction === 'R' ? 'red' : 'green'}-800`}>
                              {genome.prediction === 'R' ? 'Resistant' : 'Susceptible'}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
              
              <div className="flex justify-between">
                <Button variant="outline" onClick={() => setActiveTab('upload')}>
                  Predict Another Genome
                </Button>
                <Button>
                  Download Report
                </Button>
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>
      
      <CardFooter className="bg-gray-50 border-t p-4">
        <p className="text-xs text-gray-500">
          This predictor uses machine learning models trained on bacterial genomes to predict
          antibiotic resistance profiles without the need for laboratory testing.
        </p>
      </CardFooter>
    </Card>
  );
};

export default GenomePredictor;