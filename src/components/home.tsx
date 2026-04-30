"use client";
import React, { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import GenomeUploader from "./GenomeUploader";
import ResultsDashboard from "./ResultsDashboard";
import TrainingPipeline from "./TrainingPipeline";
import TrainingStatus from "./TrainingStatus";
import TrainingHistory from "./TrainingHistory";
import NCBIGenomeSearch from "./NCBIGenomeSearch";
import { motion } from "framer-motion";
import {
  ResistancePredictor,
  PredictionResult,
  GeneticMarker,
} from "@/lib/resistancePredictor";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";

interface GenomeData {
  id: string;
  name: string;
  size: number;
  uploadDate: Date;
  fastaContent?: string;
}

interface ProcessedResult {
  genomeId: string;
  genomeName: string;
  predictions: PredictionResult[];
  analysisSummary: any;
  sequence?: string;
}

interface TrainingJob {
  jobId: string;
  modelType: string;
}

import { useSearchParams } from "react-router-dom";

const HomePage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = searchParams.get("tab") || "upload";
  const [activeTab, setActiveTabState] = useState(initialTab);

  // Sync state when URL parameter changes (enables navbar routing)
  React.useEffect(() => {
    const tabFromUrl = searchParams.get("tab");
    if (tabFromUrl && tabFromUrl !== activeTab) {
      setActiveTabState(tabFromUrl);
    }
  }, [searchParams, activeTab]);

  const setActiveTab = (value: string) => {
    setActiveTabState(value);
    setSearchParams({ tab: value });
  };
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadedGenome, setUploadedGenome] = useState<GenomeData | null>(null);
  const [processedResult, setProcessedResult] =
    useState<ProcessedResult | null>(null);
  const [trainingJob, setTrainingJob] = useState<TrainingJob | null>(null);
  const [modelMode, setModelMode] = useState<
    "auto" | "xgboost" | "transformer" | "both"
  >("both");
  const [useBlast, setUseBlast] = useState(false);

  const handleFileUpload = async (file: File) => {
    setIsProcessing(true);

    try {
      // Read file to get sequence
      const fileText = await file.text();
      const sequence = fileText.split('\n').filter(line => !line.startsWith('>')).join('').replace(/\s/g, '').toUpperCase();

      // Import the API client
      const { predictResistance } = await import("@/services/apiClient");

      // Create a genome data object
      const genomeData: GenomeData = {
        id: `genome-${Date.now()}`,
        name: file.name,
        size: file.size,
        uploadDate: new Date(),
      };

      setUploadedGenome(genomeData);

      // Call the real prediction API
      const apiResponse = await predictResistance(file, modelMode, {
        enableBlast: useBlast,
      });

      // Convert API response to the format expected by ResultsDashboard
      const predictions: PredictionResult[] = apiResponse.predictions.map((p: any) => {
        const xgbMarkers = (p.xgboost_markers || []) as any[];
        const trMarkersRaw = (p.transformer_markers || []) as any[];

        const markers: GeneticMarker[] = [];

        // XGBoost k-mer markers (primary explainability)
        xgbMarkers.slice(0, 5).forEach((m, idx) => {
          markers.push({
            id: `xgb-${p.antibiotic}-${idx}`,
            name: m.kmer,
            description: `High-importance XGBoost k-mer feature present in this genome for ${p.antibiotic}`,
            impact:
              typeof m.normalized_importance === "number"
                ? m.normalized_importance
                : typeof m.importance === "number"
                  ? m.importance
                  : 0,
            confidence:
              typeof m.normalized_importance === "number"
                ? m.normalized_importance
                : typeof m.importance === "number"
                  ? m.importance
                  : 0,
            type: "gene",
          });
        });

        // Transformer markers (secondary), only when we have BLAST-based gene names
        const trMarkersWithNames = trMarkersRaw.filter(
          (m: any) => typeof m.best_hit_title === "string" && m.best_hit_title.length > 0,
        );

        if (trMarkersWithNames.length > 0) {
          const maxTr = Math.min(trMarkersWithNames.length, 3);

          trMarkersWithNames.slice(0, maxTr).forEach((m: any, idx: number) => {
            const imp =
              typeof m.normalized_importance === "number"
                ? m.normalized_importance
                : typeof m.importance === "number"
                  ? m.importance
                  : 0;

            markers.push({
              id: `tr-${p.antibiotic}-${idx}`,
              name: m.best_hit_title,
              description: `Transformer gene signal: best BLAST match ${m.best_hit_title} (${m.class_label}) for ${p.antibiotic}`,
              impact: imp,
              confidence: imp,
              type: "gene",
            });
          });
        }

        return {
          antibiotic: p.antibiotic,
          prediction: p.prediction as "S" | "I" | "R",
          confidence: p.confidence,
          markers,
          classProbabilities: p.class_probabilities
            ? {
              S: p.class_probabilities.S,
              I: p.class_probabilities.I,
              R: p.class_probabilities.R,
            }
            : undefined,
          reasoning: `Predicted ${p.prediction === "R"
            ? "Resistant"
            : p.prediction === "I"
              ? "Intermediate"
              : "Susceptible"
            } with ${(p.confidence * 100).toFixed(1)}% confidence based on genomic patterns.`,
        };
      });

      const result: ProcessedResult = {
        genomeId: genomeData.id,
        genomeName: genomeData.name,
        predictions,
        analysisSummary: {
          sequenceLength: apiResponse.analysis_summary.sequence_length,
          gcContent: apiResponse.analysis_summary.gc_content,
          sequenceQuality: apiResponse.analysis_summary.sequence_length > 1000000 ? "High" : "Medium",
          resistanceGenesFound: 0, // Can be enhanced later
          mutationsFound: 0, // Can be enhanced later
          similarGenomes: apiResponse.analysis_summary.similar_genomes?.map(g => ({
            genome_id: g.genome_id,
            species: g.species,
            similarity_score: g.similarity_score
          })) || [],
          modelUsed: apiResponse.analysis_summary.model_used,
          nGenes: apiResponse.analysis_summary.n_genes,
          uniqueKmersFound: apiResponse.analysis_summary.unique_kmers_found,
          similaritySearchPerformed: apiResponse.analysis_summary.similarity_search_performed,
          similaritySearchRequired: apiResponse.analysis_summary.similarity_search_required,
          ensembleDetails: apiResponse.analysis_summary.ensemble_details,
        },
        sequence,
      };

      setProcessedResult(result);
      setIsProcessing(false);
      setActiveTab("results");
    } catch (error: any) {
      console.error("Analysis failed:", error);
      setIsProcessing(false);
      alert(`Prediction failed: ${error.message || 'Unknown error'}. Make sure you have trained a model first.`);
    }
  };

  const handleReset = () => {
    setUploadedGenome(null);
    setProcessedResult(null);
    setActiveTab("upload");
  };

  const handleJobCreated = (jobId: string, modelType: string) => {
    setTrainingJob({ jobId, modelType });
    setActiveTab("training-status");
  };

  const handleNewTraining = () => {
    setTrainingJob(null);
    setActiveTab("training");
  };

  return (
    <div className="min-h-screen px-6 pb-6 pt-28 md:px-10 md:pb-10 md:pt-32">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-7xl mx-auto"
      >
        <header className="mb-8 text-center">
          <h1 className="text-3xl md:text-4xl lg:text-6xl font-bold text-slate-100 mb-4 drop-shadow-lg">
            Bacterial Antibiogram Predictor
          </h1>
          <p className="text-base md:text-lg lg:text-xl text-slate-300 font-normal max-w-2xl mx-auto drop-shadow-md">
            Predict antibiotic resistance profiles from whole-genome sequences using AI-powered machine learning
          </p>
        </header>

        <Card className="bg-slate-900/50 backdrop-blur-md border border-slate-800 shadow-2xl">
          <CardHeader>
            <CardTitle className="text-slate-100">Antibiogram Analysis</CardTitle>
            <CardDescription className="text-slate-400">
              Upload a bacterial genome sequence (FASTA format) to predict its
              antibiotic resistance profile.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs
              value={activeTab}
              onValueChange={setActiveTab}
              className="w-full"
            >
              <div className="mb-6 flex flex-col gap-2">
                <span className="text-sm font-medium text-slate-300">
                  Prediction model mode
                </span>
                <RadioGroup
                  className="grid gap-3 md:grid-cols-3"
                  value={modelMode}
                  onValueChange={(value: string) =>
                    setModelMode(
                      value as "auto" | "xgboost" | "transformer" | "both",
                    )
                  }
                >
                  <div className="flex items-start space-x-2 rounded-md border border-slate-700 bg-slate-800/50 p-3 text-slate-200 hover:bg-slate-800 transition-colors">
                    <RadioGroupItem value="xgboost" id="mode-xgboost" className="border-slate-400" />
                    <Label
                      htmlFor="mode-xgboost"
                      className="space-y-1 leading-tight cursor-pointer"
                    >
                      <span className="block text-sm font-semibold">
                        XGBoost only
                      </span>
                      <span className="block text-xs text-slate-400">
                        Fast baseline classifier using k-mer features.
                      </span>
                    </Label>
                  </div>
                  <div className="flex items-start space-x-2 rounded-md border border-slate-700 bg-slate-800/50 p-3 text-slate-200 hover:bg-slate-800 transition-colors">
                    <RadioGroupItem
                      value="transformer"
                      id="mode-transformer"
                      className="border-slate-400"
                    />
                    <Label
                      htmlFor="mode-transformer"
                      className="space-y-1 leading-tight cursor-pointer"
                    >
                      <span className="block text-sm font-semibold">
                        Transformer only
                      </span>
                      <span className="block text-xs text-slate-400">
                        DNABERT genome embeddings with similarity search.
                      </span>
                    </Label>
                  </div>
                  <div className="flex items-start space-x-2 rounded-md border border-blue-500/50 bg-blue-900/20 p-3 text-slate-200 hover:bg-blue-900/30 transition-colors">
                    <RadioGroupItem value="both" id="mode-both" className="border-slate-400" />
                    <Label
                      htmlFor="mode-both"
                      className="space-y-1 leading-tight cursor-pointer"
                    >
                      <span className="block text-sm font-semibold">
                        Both (ensemble)
                      </span>
                      <span className="block text-xs text-blue-300/80">
                        Transformer as main model, XGBoost as supporting signal.
                      </span>
                    </Label>
                  </div>
                </RadioGroup>
                <div className="flex items-center gap-2 mt-2 text-xs text-slate-400">
                  <input
                    id="toggle-blast"
                    type="checkbox"
                    className="h-3 w-3 accent-blue-500"
                    checked={useBlast}
                    onChange={(e) => setUseBlast(e.target.checked)}
                  />
                  <Label htmlFor="toggle-blast" className="text-xs text-slate-400 cursor-pointer">
                    Use BLAST naming for Transformer markers (slower)
                  </Label>
                </div>
              </div>
              <TabsList className="grid w-full grid-cols-5 mb-8 bg-slate-800/80 text-slate-300 p-1 rounded-lg">
                <TabsTrigger value="upload" disabled={isProcessing} className="data-[state=active]:bg-slate-700 data-[state=active]:text-white">
                  Genome Upload
                </TabsTrigger>
                <TabsTrigger value="database" className="data-[state=active]:bg-slate-700 data-[state=active]:text-white">
                  Genome Database
                </TabsTrigger>
                <TabsTrigger value="results" disabled={!processedResult} className="data-[state=active]:bg-slate-700 data-[state=active]:text-white">
                  Results Dashboard
                </TabsTrigger>
                <TabsTrigger value="training" className="data-[state=active]:bg-slate-700 data-[state=active]:text-white">
                  Model Training
                </TabsTrigger>
                <TabsTrigger value="training-status" className="data-[state=active]:bg-slate-700 data-[state=active]:text-white">
                  Training Status
                </TabsTrigger>
              </TabsList>

              <TabsContent value="upload" className="mt-0">
                <GenomeUploader
                  onFileUpload={handleFileUpload}
                  isProcessing={isProcessing}
                />
              </TabsContent>

              <TabsContent value="database" className="mt-0">
                <NCBIGenomeSearch
                  onGenomeSelect={(genome) => {
                    console.log('Selected genome:', genome);
                  }}
                  onSequenceDownload={(genome) => {
                    console.log('Downloaded sequence for:', genome.organism);
                  }}
                  onBatchProcess={async (genomes) => {
                    console.log(`Processing ${genomes.length} genomes`);
                    // You can add batch processing logic here
                    // For example, automatically upload each genome for prediction
                    for (const genome of genomes) {
                      if (genome.fastaContent) {
                        // Create a File object from the FASTA content
                        const blob = new Blob([genome.fastaContent], { type: 'text/plain' });
                        const file = new File([blob], `${genome.organism}.fasta`, { type: 'text/plain' });
                        // Process the genome
                        await handleFileUpload(file);
                      }
                    }
                  }}
                />
              </TabsContent>

              <TabsContent value="results" className="mt-0">
                {processedResult && (
                  <ResultsDashboard
                    sampleName={processedResult.genomeName}
                    predictions={processedResult.predictions}
                    analysisSummary={processedResult.analysisSummary}
                    sequence={processedResult.sequence}
                    onNewUpload={handleReset}
                  />
                )}
              </TabsContent>

              <TabsContent value="training" className="mt-0">
                <TrainingPipeline onJobCreated={handleJobCreated} />
              </TabsContent>

              <TabsContent value="training-status" className="mt-0 space-y-6">
                {trainingJob && (
                  <TrainingStatus
                    jobId={trainingJob.jobId}
                    modelType={trainingJob.modelType}
                    onNewTraining={handleNewTraining}
                  />
                )}
                <TrainingHistory
                  onSelectJob={(jobId, jobType) => {
                    setTrainingJob({ jobId, modelType: jobType });
                  }}
                />
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        <footer className="mt-8 text-center text-sm text-slate-500">
          <p>
            Bacterial Antibiogram Predictor &copy; {new Date().getFullYear()}
          </p>
          <p className="mt-1 text-slate-400">
            Predicting antibiotic resistance from genomic data
          </p>
        </footer>
      </motion.div>
    </div>
  );
};

export default HomePage;
