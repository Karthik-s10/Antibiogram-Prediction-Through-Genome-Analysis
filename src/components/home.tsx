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
import KEGGGenomeSearch from "./KEGGGenomeSearch";
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

const HomePage = () => {
  const [activeTab, setActiveTab] = useState("upload");
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadedGenome, setUploadedGenome] = useState<GenomeData | null>(null);
  const [processedResult, setProcessedResult] =
    useState<ProcessedResult | null>(null);

  const handleFileUpload = async (file: File) => {
    setIsProcessing(true);

    try {
      // Read the FASTA file content
      const fastaContent = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target?.result as string);
        reader.onerror = reject;
        reader.readAsText(file);
      });

      // Create a genome data object
      const genomeData: GenomeData = {
        id: `genome-${Date.now()}`,
        name: file.name,
        size: file.size,
        uploadDate: new Date(),
        fastaContent,
      };

      setUploadedGenome(genomeData);

      // Simulate processing delay for realistic UX
      setTimeout(async () => {
        try {
          // Initialize the ML predictor with the genome sequence
          const predictor = new ResistancePredictor(fastaContent);

          // Run the machine learning analysis
          const predictions = await predictor.predictResistance();
          const analysisSummary = predictor.getAnalysisSummary();

          const result: ProcessedResult = {
            genomeId: genomeData.id,
            genomeName: genomeData.name,
            predictions,
            analysisSummary,
          };

          setProcessedResult(result);
          setIsProcessing(false);
          setActiveTab("results");
        } catch (error) {
          console.error("Analysis failed:", error);
          setIsProcessing(false);
          // Could add error handling here
        }
      }, 2000);
    } catch (error) {
      console.error("File reading failed:", error);
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setUploadedGenome(null);
    setProcessedResult(null);
    setActiveTab("upload");
  };

  return (
    <div className="min-h-screen bg-background p-6 md:p-10">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-7xl mx-auto"
      >
        <header className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-2">
            Bacterial Antibiogram Predictor
          </h1>
          <p className="text-muted-foreground text-lg">
            Predict antibiotic resistance profiles from whole-genome sequences
          </p>
        </header>

        <Card className="bg-card">
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
              <TabsList className="grid w-full grid-cols-3 mb-8">
                <TabsTrigger value="upload" disabled={isProcessing}>
                  Genome Upload
                </TabsTrigger>
                <TabsTrigger value="kegg" disabled={isProcessing}>
                  KEGG Database
                </TabsTrigger>
                <TabsTrigger value="results" disabled={!processedResult}>
                  Results Dashboard
                </TabsTrigger>
              </TabsList>

              <TabsContent value="upload" className="mt-0">
                <GenomeUploader
                  onFileUpload={handleFileUpload}
                  isProcessing={isProcessing}
                />
              </TabsContent>

              <TabsContent value="kegg" className="mt-0">
                <KEGGGenomeSearch
                  onGenomeSelect={(genome) => {
                    console.log("Selected KEGG genome:", genome);
                    // You can add logic here to process the selected KEGG genome
                  }}
                  onSequenceDownload={(genome) => {
                    console.log("Downloaded sequence for:", genome.organism);
                    // You can add logic here to handle the downloaded sequence
                  }}
                  onBatchProcess={(genomes) => {
                    console.log(
                      `Processing ${genomes.length} genomes in batch mode`,
                    );
                    setIsProcessing(true);

                    // Simulate batch processing
                    setTimeout(() => {
                      // In a real implementation, this would call the Python ML model
                      // through an API endpoint to process all genomes

                      // For demo, we'll create a mock result for the first genome
                      if (genomes.length > 0) {
                        const genome = genomes[0];

                        // Create a mock genome data object
                        const genomeData = {
                          id: genome.id,
                          name: `${genome.organism} (${genome.id})`,
                          size: genome.size,
                          uploadDate: new Date(),
                        };

                        setUploadedGenome(genomeData);

                        // Initialize the ML predictor with mock data
                        const mockFastaContent = `>${genome.id}\nACGTACGT`; // Mock sequence
                        const predictor = new ResistancePredictor(
                          mockFastaContent,
                        );

                        // Run the analysis
                        predictor.predictResistance().then((predictions) => {
                          const analysisSummary =
                            predictor.getAnalysisSummary();

                          const result = {
                            genomeId: genomeData.id,
                            genomeName: genomeData.name,
                            predictions,
                            analysisSummary,
                          };

                          setProcessedResult(result);
                          setIsProcessing(false);
                          setActiveTab("results");
                        });
                      } else {
                        setIsProcessing(false);
                      }
                    }, 3000);
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
            </Tabs>
          </CardContent>
        </Card>

        <footer className="mt-8 text-center text-sm text-muted-foreground">
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
