import React, { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Download, FileUp, Info, Activity, Database } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import ExplainabilityView from "./ExplainabilityView";
import { PredictionResult } from "@/lib/resistancePredictor";

interface ResultsDashboardProps {
  sampleName?: string;
  organism?: string;
  predictions?: PredictionResult[];
  analysisSummary?: any;
  timestamp?: string;
  onNewUpload?: () => void;
}

const ResultsDashboard = ({
  sampleName = "Sample_WGS_001",
  organism = "Bacterial isolate",
  predictions = [],
  analysisSummary,
  timestamp = new Date().toLocaleString(),
  onNewUpload = () => {},
}: ResultsDashboardProps) => {
  const [activeTab, setActiveTab] = useState("profile");

  const getStatusColor = (status: string) => {
    switch (status) {
      case "S":
        return "bg-green-100 text-green-800 border-green-300";
      case "I":
        return "bg-yellow-100 text-yellow-800 border-yellow-300";
      case "R":
        return "bg-red-100 text-red-800 border-red-300";
      default:
        return "bg-gray-100 text-gray-800 border-gray-300";
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "S":
        return "Susceptible";
      case "I":
        return "Intermediate";
      case "R":
        return "Resistant";
      default:
        return "Unknown";
    }
  };

  const handleDownloadReport = () => {
    // Generate and download ML analysis report
    const reportData = {
      sampleName,
      organism,
      timestamp,
      analysisSummary,
      predictions: predictions.map((p) => ({
        antibiotic: p.antibiotic,
        prediction: p.prediction,
        confidence: p.confidence,
        reasoning: p.reasoning,
        markers: p.markers.length,
      })),
    };

    const blob = new Blob([JSON.stringify(reportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${sampleName}_resistance_analysis.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full max-w-7xl mx-auto p-4 bg-white rounded-lg shadow-sm">
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle className="text-2xl font-bold flex items-center">
                <Activity className="mr-2 h-6 w-6 text-blue-600" />
                ML-Powered Antibiogram Analysis
              </CardTitle>
              <CardDescription className="mt-2">
                <span className="font-medium">Sample:</span> {sampleName} |{" "}
                <span className="font-medium">Organism:</span> {organism} |{" "}
                <span className="font-medium">Analyzed:</span> {timestamp}
              </CardDescription>
              {analysisSummary && (
                <div className="mt-2 flex items-center gap-4 text-sm text-gray-600">
                  <span className="flex items-center">
                    <Database className="mr-1 h-4 w-4" />
                    Sequence:{" "}
                    {(analysisSummary.sequenceLength / 1000000).toFixed(1)}M bp
                  </span>
                  <span>Quality: {analysisSummary.sequenceQuality}</span>
                  <span>GC: {analysisSummary.gcContent}%</span>
                  <span>
                    Resistance genes: {analysisSummary.resistanceGenesFound}
                  </span>
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleDownloadReport}>
                <Download className="mr-2 h-4 w-4" /> Download Report
              </Button>
              <Button onClick={onNewUpload}>
                <FileUp className="mr-2 h-4 w-4" /> New Analysis
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="w-full"
          >
            <TabsList className="grid w-full grid-cols-2 mb-8">
              <TabsTrigger value="profile">Resistance Profile</TabsTrigger>
              <TabsTrigger value="explainability">Genetic Markers</TabsTrigger>
            </TabsList>

            <TabsContent value="profile" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {predictions.map((prediction, index) => (
                  <div
                    key={index}
                    className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="font-medium text-lg">
                          {prediction.antibiotic}
                        </h3>
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <p className="text-sm text-gray-500 flex items-center cursor-help">
                                Confidence:{" "}
                                {(prediction.confidence * 100).toFixed(1)}%
                                <Info className="ml-1 h-3 w-3" />
                              </p>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-sm">
                              <div className="space-y-2">
                                <p className="font-medium">
                                  ML Analysis Result:
                                </p>
                                <p className="text-sm">
                                  {prediction.reasoning}
                                </p>
                                <p className="text-xs mt-1">
                                  Based on {prediction.markers.length} genetic
                                  markers
                                </p>
                              </div>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                      <div className="flex flex-col items-end">
                        <Badge
                          className={`text-lg px-3 py-1 font-bold ${getStatusColor(prediction.prediction)}`}
                        >
                          {prediction.prediction}
                        </Badge>
                        <span className="text-xs text-gray-600 mt-1">
                          {getStatusText(prediction.prediction)}
                        </span>
                      </div>
                    </div>

                    <div className="text-xs text-gray-600">
                      <p className="font-medium mb-1">Key markers detected:</p>
                      <div className="space-y-1">
                        {prediction.markers.slice(0, 2).map((marker, idx) => (
                          <div key={idx} className="flex justify-between">
                            <span>{marker.name}</span>
                            <span
                              className={
                                marker.impact > 0
                                  ? "text-red-600"
                                  : "text-green-600"
                              }
                            >
                              {marker.impact > 0 ? "+" : ""}
                              {(marker.impact * 100).toFixed(0)}%
                            </span>
                          </div>
                        ))}
                        {prediction.markers.length > 2 && (
                          <p className="text-gray-500">
                            +{prediction.markers.length - 2} more...
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-8 p-4 bg-gray-50 rounded-lg">
                <h3 className="font-medium mb-2">Legend</h3>
                <div className="flex gap-4">
                  <div className="flex items-center">
                    <Badge className="bg-green-100 text-green-800 border-green-300 mr-2">
                      S
                    </Badge>
                    <span>Susceptible - Antibiotic likely effective</span>
                  </div>
                  <div className="flex items-center">
                    <Badge className="bg-yellow-100 text-yellow-800 border-yellow-300 mr-2">
                      I
                    </Badge>
                    <span>Intermediate - Limited effectiveness</span>
                  </div>
                  <div className="flex items-center">
                    <Badge className="bg-red-100 text-red-800 border-red-300 mr-2">
                      R
                    </Badge>
                    <span>Resistant - Antibiotic likely ineffective</span>
                  </div>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="explainability">
              <ExplainabilityView
                predictions={predictions}
                genomeId={sampleName}
                analysisSummary={analysisSummary}
              />
            </TabsContent>
          </Tabs>
        </CardContent>
        <CardFooter className="border-t pt-4 text-sm text-gray-500">
          <div className="space-y-2">
            <p className="flex items-center">
              <Activity className="mr-2 h-4 w-4 text-blue-500" />
              <strong>Machine Learning Analysis:</strong> Predictions based on
              resistance gene detection and chromosomal mutation analysis from
              whole genome sequence.
            </p>
            <p>
              <strong>Clinical Note:</strong> These ML predictions should be
              interpreted alongside clinical judgment and phenotypic testing
              when available. Results may vary based on specific strain
              characteristics and environmental factors.
            </p>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
};

export default ResultsDashboard;
