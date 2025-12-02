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

  const getConfidenceTier = (confidence: number) => {
    if (confidence >= 0.8) return "high";
    if (confidence >= 0.6) return "moderate";
    return "low";
  };

  const getResistanceRisk = (prediction: PredictionResult): number => {
    if (prediction.classProbabilities) {
      const { S, I, R } = prediction.classProbabilities;
      const s = typeof S === "number" ? S : 0;
      const i = typeof I === "number" ? I : 0;
      const r = typeof R === "number" ? R : 0;
      // Treat R as full risk and I as half risk to emphasize intermediate cases
      const risk = r + 0.5 * i;
      if (!Number.isFinite(risk)) return 0;
      return Math.min(1, Math.max(0, risk));
    }

    // Fallback when we don't have per-class probabilities (older paths/demo)
    if (prediction.prediction === "R") {
      return Math.min(1, Math.max(0, prediction.confidence));
    }
    if (prediction.prediction === "I") {
      return 0.5;
    }
    // Susceptible: invert confidence so low-confidence S looks riskier
    return Math.min(1, Math.max(0, 1 - prediction.confidence));
  };

  const getStatusColorByRisk = (risk: number) => {
    // Map risk 0–1 to a rich but soft color gradient using light/pastel shades
    // dark red → red → orange → dark yellow → yellow → light yellow → yellow–green → green → dark green
    if (risk >= 0.9) return "bg-red-200 text-red-900 border-red-400"; // darkest red (soft)
    if (risk >= 0.75) return "bg-red-100 text-red-800 border-red-300"; // red
    if (risk >= 0.6) return "bg-orange-100 text-orange-800 border-orange-300"; // orange
    if (risk >= 0.5) return "bg-amber-100 text-amber-800 border-amber-300"; // dark yellow
    if (risk >= 0.4) return "bg-yellow-100 text-yellow-800 border-yellow-300"; // yellow
    if (risk >= 0.3) return "bg-yellow-50 text-yellow-700 border-yellow-200"; // light yellow
    if (risk >= 0.2) return "bg-lime-100 text-lime-800 border-lime-300"; // yellow–green mix
    if (risk >= 0.1) return "bg-green-100 text-green-800 border-green-300"; // green
    return "bg-green-50 text-green-700 border-green-200"; // dark green (very low risk)
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
                <div className="mt-2 space-y-2">
                  <div className="flex items-center gap-4 text-sm text-gray-600">
                    <span className="flex items-center">
                      <Database className="mr-1 h-4 w-4" />
                      Sequence:{" "}
                      {(analysisSummary.sequenceLength / 1000000).toFixed(1)}M bp
                    </span>
                    <span>Quality: {analysisSummary.sequenceQuality}</span>
                    <span>GC: {analysisSummary.gcContent}%</span>
                    {analysisSummary.modelUsed && (
                      <span>Model: {analysisSummary.modelUsed}</span>
                    )}
                    {analysisSummary.ensembleDetails && (
                      <span className="text-blue-700 font-medium">
                        Ensemble: Transformer (primary) + XGBoost (base)
                      </span>
                    )}
                  </div>
                  {analysisSummary.similarGenomes && analysisSummary.similarGenomes.length > 0 && (
                    <div className="flex items-center gap-2 text-sm text-blue-600">
                      <Info className="h-4 w-4" />
                      <span>
                        Found {analysisSummary.similarGenomes.length} similar genomes in training data
                      </span>
                    </div>
                  )}
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
                {predictions.map((prediction, index) => {
                  const ensemble =
                    analysisSummary?.ensembleDetails?.per_antibiotic?.[
                      prediction.antibiotic
                    ];

                  const confidenceTier = getConfidenceTier(prediction.confidence);
                  const confidenceTierLabel =
                    confidenceTier === "high"
                      ? "High confidence"
                      : confidenceTier === "moderate"
                      ? "Moderate confidence"
                      : "Low / uncertain confidence";

                  const riskScore = getResistanceRisk(prediction);

                  const sourceLabel: string | undefined = (() => {
                    if (ensemble) {
                      const hasTransformer = !!ensemble.transformer;
                      const hasXgboost = !!ensemble.xgboost;

                      if (hasTransformer && hasXgboost) return "Source: Transformer + XGBoost";
                      if (hasTransformer) return "Source: Transformer only";
                      if (hasXgboost) return "Source: XGBoost only";
                      return undefined;
                    }

                    const modelUsed = analysisSummary?.modelUsed as string | undefined;
                    if (modelUsed) {
                      const lower = modelUsed.toLowerCase();
                      if (lower.includes("ensemble")) return "Source: Transformer + XGBoost";
                      if (lower.includes("transformer")) return "Source: Transformer only";
                      if (lower.includes("xgboost")) return "Source: XGBoost only";
                    }

                    return undefined;
                  })();

                  const transformerPrediction =
                    ensemble?.transformer?.prediction ?? null;
                  const xgboostPrediction =
                    ensemble?.xgboost?.prediction ?? null;
                  const modelsDisagree =
                    transformerPrediction &&
                    xgboostPrediction &&
                    transformerPrediction !== xgboostPrediction;

                  return (
                    <div
                      key={index}
                      className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <h3 className="font-medium text-lg">
                            {prediction.antibiotic}
                          </h3>
                          {sourceLabel && (
                            <p className="text-[11px] text-slate-500 mt-0.5">
                              {sourceLabel}
                            </p>
                          )}
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
                                  <p className="text-xs mt-1 text-gray-600">
                                    Confidence tier: {confidenceTierLabel}
                                  </p>
                                </div>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </div>
                        <div className="flex flex-col items-end">
                          <Badge
                            className={`text-lg px-3 py-1 font-bold ${getStatusColorByRisk(
                              riskScore
                            )}`}
                          >
                            {prediction.prediction}
                          </Badge>
                          <span className="text-xs text-gray-600 mt-1">
                            {getStatusText(prediction.prediction)}
                          </span>
                        </div>
                      </div>

                      <div className="text-xs text-gray-600 space-y-3">
                        {prediction.markers.length > 0 && (
                          <div>
                            <p className="font-medium mb-1">
                              Key markers detected
                              <span className="ml-1 text-[10px] text-slate-500">
                                (XGBoost k-mers)
                              </span>
                            </p>
                            <div className="space-y-1">
                              {prediction.markers.slice(0, 2).map((marker, idx) => {
                                const isXgb = marker.id.startsWith("xgb-");
                                const sourceLabel = isXgb ? "XGBoost" : "Transformer";
                                return (
                                  <div key={idx} className="flex justify-between items-baseline">
                                    <div className="flex flex-col">
                                      <span>{marker.name}</span>
                                      <span className="text-[10px] text-slate-500">{sourceLabel}</span>
                                    </div>
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
                                );
                              })}
                              {prediction.markers.length > 2 && (
                                <p className="text-gray-500">
                                  +{prediction.markers.length - 2} more...
                                </p>
                              )}
                            </div>
                          </div>
                        )}

                        {ensemble && (
                          <div
                            className={`mt-2 rounded-md p-2 border ${
                              modelsDisagree
                                ? "bg-amber-50 border-amber-300"
                                : "bg-slate-50 border-slate-200"
                            }`}
                          >
                            <p className="font-semibold mb-1 text-slate-800 text-[11px]">
                              Model contributions
                            </p>
                            <div className="grid grid-cols-3 gap-2 text-[11px]">
                              <div className="font-medium text-slate-500">
                                Model
                              </div>
                              <div className="font-medium text-slate-500">
                                Prediction
                              </div>
                              <div className="font-medium text-slate-500">
                                Confidence
                              </div>

                              <div className="text-emerald-700 font-semibold">
                                Transformer
                                {" "}
                                <span className="text-[10px] font-normal text-emerald-600">
                                  (primary)
                                </span>
                              </div>
                              <div>
                                {ensemble.transformer?.prediction ?? "-"}
                              </div>
                              <div>
                                {ensemble.transformer?.confidence !== undefined
                                  ? `${(ensemble.transformer.confidence * 100).toFixed(1)}%`
                                  : "-"}
                              </div>

                              <div className="text-slate-700 font-semibold">
                                XGBoost
                                {" "}
                                <span className="text-[10px] font-normal text-slate-500">
                                  (base)
                                </span>
                              </div>
                              <div>{ensemble.xgboost?.prediction ?? "-"}</div>
                              <div>
                                {ensemble.xgboost?.confidence !== undefined
                                  ? `${(ensemble.xgboost.confidence * 100).toFixed(1)}%`
                                  : "-"}
                              </div>
                            </div>

                            {modelsDisagree && (
                              <p className="mt-2 text-[11px] text-amber-700 font-medium">
                                Models disagree for this antibiotic (Transformer vs XGBoost). Interpret
                                with caution.
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-8 p-4 bg-gray-50 rounded-lg">
                <h3 className="font-medium mb-2">Legend</h3>
                <div className="flex flex-col gap-2 text-sm text-gray-700">
                  <div className="flex items-center">
                    <Badge className="bg-green-100 text-green-800 border-green-300 mr-2">
                      S
                    </Badge>
                    <span>
                      <span className="font-medium">Susceptible</span> – Antibiotic likely effective. Greener badges
                      indicate lower predicted resistance risk.
                    </span>
                  </div>
                  <div className="flex items-center">
                    <Badge className="bg-yellow-100 text-yellow-800 border-yellow-300 mr-2">
                      I
                    </Badge>
                    <span>
                      <span className="font-medium">Intermediate</span> – Limited effectiveness when the model
                      explicitly predicts I.
                    </span>
                  </div>
                  <div className="flex items-center">
                    <Badge className="bg-red-100 text-red-800 border-red-300 mr-2">
                      R
                    </Badge>
                    <span>
                      <span className="font-medium">Resistant</span> – Antibiotic likely ineffective. More
                      orange/red badges indicate higher predicted resistance risk.
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 mt-1">
                    Note: The color of each antibiotic card reflects a continuous resistance
                    risk score (from low/green to high/red), so some S or R predictions may
                    appear yellow/orange when the model is uncertain or borderline.
                  </p>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="explainability">
              <div className="space-y-6">
                {/* Similar Genomes Section */}
                {analysisSummary?.similarGenomes && analysisSummary.similarGenomes.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Similar Genomes Found</CardTitle>
                      <CardDescription>
                        Top matches from the training database based on k-mer similarity
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {analysisSummary.similarGenomes.map((genome: any, idx: number) => (
                          <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border">
                            <div>
                              <p className="font-medium">{genome.genome_id || 'Unknown ID'}</p>
                              {(() => {
                                const displayName =
                                  genome.organism_name ||
                                  genome.genome_name ||
                                  genome.species ||
                                  "Unknown species";
                                const variant = genome.strain;
                                return (
                                  <p className="text-sm text-gray-600">
                                    {variant ? `${displayName} (${variant})` : displayName}
                                  </p>
                                );
                              })()}
                            </div>
                            <div className="text-right">
                              <p className="text-lg font-bold text-blue-600">
                                {(genome.similarity_score * 100).toFixed(1)}%
                              </p>
                              <p className="text-xs text-gray-500">similarity</p>
                            </div>
                          </div>
                        ))}
                      </div>
                      <p className="mt-4 text-sm text-gray-600">
                        💡 These genomes share similar k-mer patterns with your uploaded genome. 
                        The prediction is based on resistance patterns observed in these and other training samples.
                      </p>
                    </CardContent>
                  </Card>
                )}
                
                {/* Explainability View */}
                <ExplainabilityView
                  predictions={predictions}
                  genomeId={sampleName}
                  analysisSummary={analysisSummary}
                />
              </div>
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
