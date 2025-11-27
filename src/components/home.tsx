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
import NCBIGenomeSearch from "./NCBIGenomeSearch";
import { motion } from "framer-motion";
import {
  ResistancePredictor,
  PredictionResult,
} from "@/lib/resistancePredictor";

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
      const apiResponse = await predictResistance(file);

      // Convert API response to the format expected by ResultsDashboard
      const predictions: PredictionResult[] = apiResponse.predictions.map((p: any) => ({
        antibiotic: p.antibiotic,
        prediction: p.prediction as "S" | "I" | "R",
        confidence: p.confidence,
        markers: [], // API doesn't return markers yet, can be added later
        reasoning: `Predicted ${p.prediction === 'R' ? 'Resistant' : p.prediction === 'I' ? 'Intermediate' : 'Susceptible'} with ${(p.confidence * 100).toFixed(1)}% confidence based on genomic patterns.`,
      }));

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
            similarity: g.similarity_score
          })) || [],
          modelUsed: apiResponse.analysis_summary.model_used,
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

  return (
    <div className="min-h-screen p-6 md:p-10">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-7xl mx-auto"
      >
        <header className="mb-8 text-center">
          <h1 className="text-3xl md:text-4xl lg:text-6xl font-bold text-slate-800 mb-4 drop-shadow-lg">
            Bacterial Antibiogram Predictor
          </h1>
          <p className="text-base md:text-lg lg:text-xl text-slate-700 font-normal max-w-2xl mx-auto drop-shadow-md">
            Predict antibiotic resistance profiles from whole-genome sequences using AI-powered machine learning
          </p>
        </header>

        <Card className="bg-card/95 backdrop-blur-sm shadow-xl">
          <CardHeader>
            <CardTitle>Antibiogram Analysis</CardTitle>
            <CardDescription>
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
              <TabsList className="grid w-full grid-cols-5 mb-8">
                <TabsTrigger value="upload" disabled={isProcessing}>
                  Genome Upload
                </TabsTrigger>
                <TabsTrigger value="database">
                  Genome Database
                </TabsTrigger>
                <TabsTrigger value="results" disabled={!processedResult}>
                  Results Dashboard
                </TabsTrigger>
                <TabsTrigger value="training">
                  Model Training
                </TabsTrigger>
                <TabsTrigger value="training-status" disabled={!trainingJob}>
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
                    onNewUpload={handleReset}
                  />
                )}
              </TabsContent>

              <TabsContent value="training" className="mt-0">
                <TrainingPipeline onJobCreated={handleJobCreated} />
              </TabsContent>

              <TabsContent value="training-status" className="mt-0">
                {trainingJob && (
                  <TrainingStatus
                    jobId={trainingJob.jobId}
                    modelType={trainingJob.modelType}
                    onNewTraining={handleNewTraining}
                  />
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        <footer className="mt-8 text-center text-sm text-slate-600">
          <p>
            Bacterial Antibiogram Predictor &copy; {new Date().getFullYear()}
          </p>
          <p className="mt-1">
            Predicting antibiotic resistance from genomic data
          </p>
        </footer>
      </motion.div>
    </div>
  );
};

export default HomePage;
