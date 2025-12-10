"use client";
import React, { useState } from "react";
import GenomeUploader from "./GenomeUploader";
import ResultsDashboard from "./ResultsDashboard";
import TrainingPipeline from "./TrainingPipeline";
import TrainingStatus from "./TrainingStatus";
import TrainingHistory from "./TrainingHistory";
import NCBIGenomeSearch from "./NCBIGenomeSearch";
import Sidebar from "./layout/Sidebar";
import { motion, AnimatePresence } from "framer-motion";
import {
  ResistancePredictor,
  PredictionResult,
  GeneticMarker,
} from "@/lib/resistancePredictor";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import {
  Upload,
  Database,
  BarChart3,
  Cpu,
  Activity,
  ChevronRight,
  Sparkles,
  Zap,
  Shield,
} from "lucide-react";

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
}

interface TrainingJob {
  jobId: string;
  modelType: string;
}

const HomePage = () => {
  const [activeTab, setActiveTab] = useState("upload");
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
          reasoning: `Predicted ${
            p.prediction === "R"
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

  // Page title based on active tab
  const getPageTitle = () => {
    switch (activeTab) {
      case "upload": return "Genome Upload";
      case "database": return "Genome Database";
      case "results": return "Results Dashboard";
      case "training": return "Model Training";
      case "training-status": return "Training Status";
      default: return "Dashboard";
    }
  };

  const getPageDescription = () => {
    switch (activeTab) {
      case "upload": return "Upload bacterial genome sequences for resistance prediction";
      case "database": return "Search and download genomes from NCBI database";
      case "results": return "View antibiotic resistance predictions and analysis";
      case "training": return "Train machine learning models on genomic data";
      case "training-status": return "Monitor training progress and view history";
      default: return "";
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content */}
      <main className="flex-1 ml-64">
        {/* Top Header Bar */}
        <header className="sticky top-0 z-40 bg-background/80 backdrop-blur-xl border-b border-border">
          <div className="flex items-center justify-between px-8 py-4">
            <div>
              <h1 className="text-2xl font-bold text-foreground">{getPageTitle()}</h1>
              <p className="text-sm text-muted-foreground">{getPageDescription()}</p>
            </div>

            {/* Model Mode Selector - Only show on upload tab */}
            {activeTab === "upload" && (
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 bg-secondary rounded-xl p-1">
                  {[
                    { value: "xgboost", label: "XGBoost", icon: <Zap className="w-4 h-4" /> },
                    { value: "transformer", label: "Transformer", icon: <Sparkles className="w-4 h-4" /> },
                    { value: "both", label: "Ensemble", icon: <Shield className="w-4 h-4" /> },
                  ].map((mode) => (
                    <button
                      key={mode.value}
                      onClick={() => setModelMode(mode.value as any)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                        modelMode === mode.value
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {mode.icon}
                      {mode.label}
                    </button>
                  ))}
                </div>
                <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useBlast}
                    onChange={(e) => setUseBlast(e.target.checked)}
                    className="w-4 h-4 rounded border-border bg-secondary"
                  />
                  BLAST naming
                </label>
              </div>
            )}
          </div>
        </header>

        {/* Page Content */}
        <div className="p-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.2 }}
            >
              {activeTab === "upload" && (
                <div className="space-y-6">
                  {/* Quick Stats Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="revolut-card p-6 revolut-glow-blue">
                      <div className="flex items-center gap-4">
                        <div className="feature-icon revolut-gradient-blue">
                          <Upload className="w-6 h-6 text-white" />
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Ready to Analyze</p>
                          <p className="text-2xl font-bold text-foreground">FASTA Files</p>
                        </div>
                      </div>
                    </div>
                    <div className="revolut-card p-6">
                      <div className="flex items-center gap-4">
                        <div className="feature-icon revolut-gradient-green">
                          <Sparkles className="w-6 h-6 text-white" />
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Model</p>
                          <p className="text-2xl font-bold text-foreground capitalize">{modelMode}</p>
                        </div>
                      </div>
                    </div>
                    <div className="revolut-card p-6">
                      <div className="flex items-center gap-4">
                        <div className="feature-icon revolut-gradient-purple">
                          <Shield className="w-6 h-6 text-white" />
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Analysis</p>
                          <p className="text-2xl font-bold text-foreground">AI-Powered</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Upload Component */}
                  <div className="revolut-card p-6">
                    <GenomeUploader
                      onFileUpload={handleFileUpload}
                      isProcessing={isProcessing}
                    />
                  </div>
                </div>
              )}

              {activeTab === "database" && (
                <div className="revolut-card p-6">
                  <NCBIGenomeSearch
                    onGenomeSelect={(genome) => {
                      console.log('Selected genome:', genome);
                    }}
                    onSequenceDownload={(genome) => {
                      console.log('Downloaded sequence for:', genome.organism);
                    }}
                    onBatchProcess={async (genomes) => {
                      console.log(`Processing ${genomes.length} genomes`);
                      for (const genome of genomes) {
                        if (genome.fastaContent) {
                          const blob = new Blob([genome.fastaContent], { type: 'text/plain' });
                          const file = new File([blob], `${genome.organism}.fasta`, { type: 'text/plain' });
                          await handleFileUpload(file);
                        }
                      }
                    }}
                  />
                </div>
              )}

              {activeTab === "results" && (
                <div className="revolut-card p-6">
                  {processedResult ? (
                    <ResultsDashboard
                      sampleName={processedResult.genomeName}
                      predictions={processedResult.predictions}
                      analysisSummary={processedResult.analysisSummary}
                      onNewUpload={handleReset}
                    />
                  ) : (
                    <div className="text-center py-16">
                      <div className="w-16 h-16 rounded-2xl revolut-gradient-green mx-auto mb-4 flex items-center justify-center">
                        <BarChart3 className="w-8 h-8 text-white" />
                      </div>
                      <h3 className="text-xl font-semibold text-foreground mb-2">No Results Yet</h3>
                      <p className="text-muted-foreground mb-6">Upload a genome sequence to see predictions</p>
                      <button
                        onClick={() => setActiveTab("upload")}
                        className="revolut-button inline-flex items-center gap-2"
                      >
                        <Upload className="w-4 h-4" />
                        Upload Genome
                      </button>
                    </div>
                  )}
                </div>
              )}

              {activeTab === "training" && (
                <div className="revolut-card p-6">
                  <TrainingPipeline onJobCreated={handleJobCreated} />
                </div>
              )}

              {activeTab === "training-status" && (
                <div className="space-y-6">
                  {trainingJob && (
                    <div className="revolut-card p-6">
                      <TrainingStatus
                        jobId={trainingJob.jobId}
                        modelType={trainingJob.modelType}
                        onNewTraining={handleNewTraining}
                      />
                    </div>
                  )}
                  <div className="revolut-card p-6">
                    <TrainingHistory
                      onSelectJob={(jobId, jobType) => {
                        setTrainingJob({ jobId, modelType: jobType });
                      }}
                    />
                  </div>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Footer */}
        <footer className="border-t border-border px-8 py-4 mt-auto">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <p>Bacterial Antibiogram Predictor &copy; {new Date().getFullYear()}</p>
            <p>AI-powered antibiotic resistance prediction</p>
          </div>
        </footer>
      </main>
    </div>
  );
};

export default HomePage;
