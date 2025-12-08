import React, { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Upload, FileCheck, AlertCircle, Sparkles, Database } from "lucide-react";
import { trainXGBoost, trainTransformer } from "@/services/apiClient";

interface TrainingPipelineProps {
  onJobCreated: (jobId: string, modelType: string) => void;
}

const TrainingPipeline = ({ onJobCreated }: TrainingPipelineProps) => {
  const [modelType, setModelType] = useState<"xgboost" | "transformer" | "parallel">("parallel");
  const [kmerFile, setKmerFile] = useState<File | null>(null);
  const [phenotypeFile, setPhenotypeFile] = useState<File | null>(null);
  const [rosettaFile, setRosettaFile] = useState<File | null>(null);
  const [modelName, setModelName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // K-mer size
  const [kmerSize, setKmerSize] = useState<"auto" | number>("auto");
  const [customK, setCustomK] = useState(10);
  
  // XGBoost hyperparameters
  const [maxDepth, setMaxDepth] = useState(6);
  const [learningRate, setLearningRate] = useState(0.1);
  const [nEstimators, setNEstimators] = useState(100);
  
  // Transformer hyperparameters
  const [epochs, setEpochs] = useState(3);
  const [batchSize, setBatchSize] = useState(8);
  const [maxGenomes, setMaxGenomes] = useState(1000);
  const [useAllGenomes, setUseAllGenomes] = useState(false);
  const [transformerLearningRate, setTransformerLearningRate] = useState(0.00002);
  const [useRosetta, setUseRosetta] = useState(false);
  const [cycleIndex, setCycleIndex] = useState(0);

  const handleKmerFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setKmerFile(e.target.files[0]);
      setError(null);
    }
  };

  const handlePhenotypeFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setPhenotypeFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleRosettaFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setRosettaFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!kmerFile || !phenotypeFile) {
      setError("Please upload both k-mer and phenotype files");
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      let response;
      const k = kmerSize === "auto" ? undefined : customK;
      const effectiveMaxGenomes = useAllGenomes ? 0 : maxGenomes;
      
      if (modelType === "xgboost") {
        response = await trainXGBoost(kmerFile, phenotypeFile, {
          model_name: modelName || undefined,
          max_depth: maxDepth,
          learning_rate: learningRate,
          n_estimators: nEstimators,
          k: k,
          rosetta_file: rosettaFile || undefined,
          use_rosetta_preprocessor: useRosetta,
          max_genomes: effectiveMaxGenomes,
          cycle_index: cycleIndex,
        });
      } else if (modelType === "transformer") {
        response = await trainTransformer(kmerFile, phenotypeFile, {
          model_name: modelName || undefined,
          epochs: epochs,
          batch_size: batchSize,
          learning_rate: transformerLearningRate,
          k: k,
          rosetta_file: rosettaFile || undefined,
          use_rosetta_preprocessor: useRosetta,
          max_genomes: effectiveMaxGenomes,
          cycle_index: cycleIndex,
        });
      } else {
        // Parallel training
        const { trainParallel } = await import("@/services/apiClient");
        response = await trainParallel(kmerFile, phenotypeFile, {
          model_name: modelName || undefined,
          xgb_max_depth: maxDepth,
          xgb_learning_rate: learningRate,
          xgb_n_estimators: nEstimators,
          transformer_epochs: epochs,
          transformer_batch_size: batchSize,
          transformer_learning_rate: transformerLearningRate,
          k: k,
          rosetta_file: rosettaFile || undefined,
          use_rosetta_preprocessor: useRosetta,
          max_genomes: effectiveMaxGenomes,
          cycle_index: cycleIndex,
        });
      }
      
      onJobCreated(response.job_id || response.parent_job_id, modelType);
    } catch (err: any) {
      setError(err.message || "Failed to start training job");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center text-2xl">
            <Database className="mr-2 h-6 w-6 text-blue-600" />
            Model Training Pipeline
          </CardTitle>
          <CardDescription>
            Upload k-mer data and phenotype labels to train antibiotic resistance prediction models
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Model Type Selection */}
            <div className="space-y-3">
              <Label className="text-base font-semibold">Select Training Mode</Label>
              <RadioGroup value={modelType} onValueChange={(v) => setModelType(v as "xgboost" | "transformer" | "parallel")}>
                <div className="flex items-center space-x-2 p-3 border-2 border-blue-500 rounded-lg bg-blue-50 hover:bg-blue-100">
                  <RadioGroupItem value="parallel" id="parallel" />
                  <Label htmlFor="parallel" className="flex-1 cursor-pointer">
                    <div className="font-medium text-blue-900">⚡ Parallel Training (Recommended)</div>
                    <div className="text-sm text-blue-700">Train both XGBoost and Transformer simultaneously - Save time!</div>
                  </Label>
                </div>
                <div className="flex items-center space-x-2 p-3 border rounded-lg hover:bg-gray-50">
                  <RadioGroupItem value="xgboost" id="xgboost" />
                  <Label htmlFor="xgboost" className="flex-1 cursor-pointer">
                    <div className="font-medium">XGBoost Only</div>
                    <div className="text-sm text-gray-500">Fast baseline model with feature importance (~1-2 hours)</div>
                  </Label>
                </div>
                <div className="flex items-center space-x-2 p-3 border rounded-lg hover:bg-gray-50">
                  <RadioGroupItem value="transformer" id="transformer" />
                  <Label htmlFor="transformer" className="flex-1 cursor-pointer">
                    <div className="font-medium">Transformer (DNABERT) Only</div>
                    <div className="text-sm text-gray-500">Advanced model for complex patterns (~4-8 hours)</div>
                  </Label>
                </div>
              </RadioGroup>
            </div>

            {/* K-mer Size Selection */}
            <div className="space-y-3 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <Label className="text-base font-semibold">K-mer Size</Label>
              <RadioGroup value={kmerSize.toString()} onValueChange={(v) => setKmerSize(v === "auto" ? "auto" : parseInt(v))}>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="auto" id="auto-k" />
                  <Label htmlFor="auto-k" className="cursor-pointer">
                    <div className="font-medium">🔍 Auto-detect from file (Recommended)</div>
                    <div className="text-xs text-gray-600">System will detect k from your uploaded file</div>
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value={customK.toString()} id="custom-k" />
                  <Label htmlFor="custom-k" className="cursor-pointer">Manual selection:</Label>
                  <Input
                    type="number"
                    min="3"
                    max="15"
                    value={customK}
                    onChange={(e) => {
                      const val = parseInt(e.target.value);
                      setCustomK(val);
                      setKmerSize(val);
                    }}
                    className="w-20"
                    disabled={kmerSize === "auto"}
                  />
                </div>
              </RadioGroup>
              <p className="text-xs text-gray-600 mt-2">
                Common values: k=6 (DNABERT), k=10 (XGBoost), or let the system auto-detect
              </p>
            </div>

            {/* File Uploads */}
            <div className="space-y-4">
              <div>
                <Label htmlFor="kmer-file" className="text-base font-semibold">
                  K-mer Data File {kmerSize === "auto" ? "(k will be auto-detected)" : `(k=${customK})`}
                </Label>
                <div className="mt-2">
                  <div className="flex items-center gap-2">
                    <Input
                      id="kmer-file"
                      type="file"
                      onChange={handleKmerFileChange}
                      className="flex-1"
                    />
                    {kmerFile && <FileCheck className="h-5 w-5 text-green-600" />}
                  </div>
                  {kmerFile && (
                    <p className="text-sm text-gray-600 mt-1">
                      {kmerFile.name} ({(kmerFile.size / (1024 * 1024)).toFixed(2)} MB)
                    </p>
                  )}
                  <p className="text-xs text-gray-500 mt-1">
                    Expected format: genome_id  domain  k  kmer_sequence  prob1  prob2
                  </p>
                </div>
              </div>

              <div>
                <Label htmlFor="phenotype-file" className="text-base font-semibold">
                  Phenotype Data File (CSV)
                </Label>
                <div className="mt-2">
                  <div className="flex items-center gap-2">
                    <Input
                      id="phenotype-file"
                      type="file"
                      accept=".csv,.txt,.tsv"
                      onChange={handlePhenotypeFileChange}
                      className="flex-1"
                    />
                    {phenotypeFile && <FileCheck className="h-5 w-5 text-green-600" />}
                  </div>
                  {phenotypeFile && (
                    <p className="text-sm text-gray-600 mt-1">
                      {phenotypeFile.name} ({(phenotypeFile.size / (1024 * 1024)).toFixed(2)} MB)
                    </p>
                  )}
                  <p className="text-xs text-gray-500 mt-1">
                    Required columns: Genome Name, Antibiotic, Resistant Phenotype
                  </p>
                </div>
              </div>

              <div>
                <Label htmlFor="rosetta-file" className="text-base font-semibold">
                  Rosetta Mapping File (BVBRC_genome.txt, optional)
                </Label>
                <div className="mt-2">
                  <div className="flex items-center gap-2">
                    <Input
                      id="rosetta-file"
                      type="file"
                      accept=".txt,.tsv,.csv"
                      onChange={handleRosettaFileChange}
                      className="flex-1"
                    />
                    {rosettaFile && <FileCheck className="h-5 w-5 text-green-600" />}
                  </div>
                  {rosettaFile && (
                    <p className="text-sm text-gray-600 mt-1">
                      {rosettaFile.name} ({(rosettaFile.size / (1024 * 1024)).toFixed(2)} MB)
                    </p>
                  )}
                  <p className="text-xs text-gray-500 mt-1">
                    Rosetta (BVBRC_genome.txt) maps phenotype Genome IDs to Assembly/GenBank accessions used in the k-mer file,
                    so that features and labels line up on the same genomes.
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <input
                      id="use-rosetta"
                      type="checkbox"
                      checked={useRosetta}
                      onChange={(e) => setUseRosetta(e.target.checked)}
                      className="h-4 w-4"
                    />
                    <Label htmlFor="use-rosetta" className="text-sm cursor-pointer">
                      Use Rosetta preprocessor (BV-BRC ID mapping). When enabled and no file is uploaded,
                      the server will require BVBRC_genome.txt on disk.
                    </Label>
                  </div>
                </div>
              </div>
            </div>

            {/* Model Name */}
            <div>
              <Label htmlFor="model-name">Model Name (Optional)</Label>
              <Input
                id="model-name"
                type="text"
                placeholder="e.g., ecoli_xgboost_v1"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                className="mt-2"
              />
              <p className="text-xs text-gray-500 mt-1">
                Leave empty to auto-generate a unique name
              </p>
            </div>

            {/* Hyperparameters */}
            {(modelType === "xgboost" || modelType === "parallel") && (
              <div className="space-y-3 p-4 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-sm">XGBoost Hyperparameters</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="max-depth" className="text-sm">Max Depth</Label>
                    <Input
                      id="max-depth"
                      type="number"
                      min="1"
                      max="20"
                      value={maxDepth}
                      onChange={(e) => setMaxDepth(parseInt(e.target.value))}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="learning-rate" className="text-sm">Learning Rate</Label>
                    <Input
                      id="learning-rate"
                      type="number"
                      step="0.01"
                      min="0.01"
                      max="1"
                      value={learningRate}
                      onChange={(e) => setLearningRate(parseFloat(e.target.value))}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="n-estimators" className="text-sm">N Estimators</Label>
                    <Input
                      id="n-estimators"
                      type="number"
                      min="10"
                      max="1000"
                      value={nEstimators}
                      onChange={(e) => setNEstimators(parseInt(e.target.value))}
                      className="mt-1"
                    />
                  </div>
                </div>
              </div>
            )}

            {(modelType === "transformer" || modelType === "parallel") && (
              <div className="space-y-3 p-4 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-sm">Transformer Hyperparameters</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="epochs" className="text-sm">Epochs</Label>
                    <Input
                      id="epochs"
                      type="number"
                      min="1"
                      max="20"
                      value={epochs}
                      onChange={(e) => setEpochs(parseInt(e.target.value))}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="batch-size" className="text-sm">Batch Size (Recommended: 8)</Label>
                    <Input
                      id="batch-size"
                      type="number"
                      min="1"
                      max="128"
                      value={batchSize}
                      onChange={(e) => setBatchSize(parseInt(e.target.value))}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="transformer-lr" className="text-sm">Learning Rate</Label>
                    <Input
                      id="transformer-lr"
                      type="number"
                      step="0.00001"
                      min="0.00001"
                      max="0.001"
                      value={transformerLearningRate}
                      onChange={(e) => setTransformerLearningRate(parseFloat(e.target.value))}
                      className="mt-1"
                    />
                  </div>
                </div>
              </div>
            )}

            {(modelType === "xgboost" || modelType === "transformer" || modelType === "parallel") && (
              <div className="space-y-3 p-4 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-sm">Dataset Chunking & Cycles</h3>
                <div className="mt-1">
                  <Label htmlFor="max-genomes" className="text-sm">Max Genomes per Cycle (Recommended: 1000)</Label>
                  <Input
                    id="max-genomes"
                    type="number"
                    min="100"
                    max="50000"
                    value={maxGenomes}
                    onChange={(e) => setMaxGenomes(parseInt(e.target.value))}
                    className="mt-1 w-32"
                    disabled={useAllGenomes}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Limits genomes per training cycle to prevent memory issues. Lower values = faster, less RAM.
                    Your data has ~7,300 genomes; set higher for full training on powerful GPUs.
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <input
                      id="use-all-genomes"
                      type="checkbox"
                      checked={useAllGenomes}
                      onChange={(e) => {
                        const checked = e.target.checked;
                        setUseAllGenomes(checked);
                        if (checked) {
                          setCycleIndex(0);
                        }
                      }}
                      className="h-4 w-4"
                    />
                    <Label htmlFor="use-all-genomes" className="text-sm cursor-pointer">
                      Use all genomes in one job (disable chunking). This may use more RAM but trains on the full dataset in a single run.
                    </Label>
                  </div>
                </div>
                <div className="mt-3">
                  <Label htmlFor="cycle-index" className="text-sm">Cycle Index (0 for first chunk, 1 for second, ...)</Label>
                  <Input
                    id="cycle-index"
                    type="number"
                    min="0"
                    value={cycleIndex}
                    onChange={(e) => {
                      const val = parseInt(e.target.value, 10);
                      setCycleIndex(Number.isNaN(val) ? 0 : Math.max(0, val));
                    }}
                    className="mt-1 w-32"
                    disabled={useAllGenomes}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Use different cycle indexes (0, 1, 2, ...) across runs to cover all genomes in deterministic chunks.
                  </p>
                </div>
              </div>
            )}
            {/* Error Display */}
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Submit Button */}
            <Button
              type="submit"
              disabled={isSubmitting || !kmerFile || !phenotypeFile}
              className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-semibold py-3"
            >
              {isSubmitting ? (
                <>
                  <Sparkles className="mr-2 h-5 w-5 animate-spin" />
                  Starting Training...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-5 w-5" />
                  Start Training
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default TrainingPipeline;
