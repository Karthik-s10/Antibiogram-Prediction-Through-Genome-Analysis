import React, { useState, useRef, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { InfoIcon, ZoomInIcon, ZoomOutIcon, Dna, RefreshCwIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PredictionResult } from "@/lib/resistancePredictor";
import DNAHelixVisualization from "./DNAHelixVisualization";
import { ShapVisualization } from "./explanation/ShapVisualization";
import { ForcePlot } from "./explanation/ForcePlot";
import { ComparativeExplanation } from "./explanation/ComparativeExplanation";

interface ExplainabilityViewProps {
  predictions?: PredictionResult[];
  genomeId?: string;
  analysisSummary?: any;
}

const ExplainabilityView: React.FC<ExplainabilityViewProps> = ({
  predictions = [],
  genomeId = "Sample_123456",
  analysisSummary,
}) => {
  const [selectedAntibiotic, setSelectedAntibiotic] = useState<string>(
    predictions[0]?.antibiotic || "",
  );
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [viewMode, setViewMode] = useState<"heatmap" | "network" | "dna-helix" | "shap" | "genetic-markers">("shap");
  const [shapExplanation, setShapExplanation] = useState<any>(null);
  const [isLoadingShap, setIsLoadingShap] = useState(false);
  const [xgbExplanation, setXgbExplanation] = useState<any>(null);
  const [dnabertExplanation, setDnabertExplanation] = useState<any>(null);

  // Load sample SHAP explanations for demo
  useEffect(() => {
    const loadSampleExplanations = async () => {
      try {
        // Load XGBoost explanation
        const xgbResponse = await fetch('/api/explanations/single', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            antibiotic: 'amikacin',
            model_type: 'xgboost',
            features: Array(1000).fill(0).map((_, i) => Math.random()),
            prediction: 'R',
            probability: 0.75
          })
        });
        
        if (xgbResponse.ok) {
          const xgbData = await xgbResponse.json();
          if (xgbData.success) {
            setXgbExplanation(xgbData.explanation);
          }
        } else {
          // Fallback to sample data
          const sampleXgbResponse = await fetch('/data_cache/shap_explanations/working_xgboost_explanation.json');
          if (sampleXgbResponse.ok) {
            const sampleXgbData = await sampleXgbResponse.json();
            setXgbExplanation(sampleXgbData);
          }
        }

        // Load DNABERT explanation
        const dnabertResponse = await fetch('/api/explanations/single', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            antibiotic: 'amikacin',
            model_type: 'transformer',
            sequence: 'ATCGATCGATCGATCGATCG',
            prediction: 'S',
            probability: 0.82
          })
        });
        
        if (dnabertResponse.ok) {
          const dnabertData = await dnabertResponse.json();
          if (dnabertData.success) {
            setDnabertExplanation(dnabertData.explanation);
          }
        } else {
          // Fallback to sample data
          const sampleDnabertResponse = await fetch('/data_cache/shap_explanations/working_dnabert_explanation.json');
          if (sampleDnabertResponse.ok) {
            const sampleDnabertData = await sampleDnabertResponse.json();
            setDnabertExplanation(sampleDnabertData);
          }
        }
      } catch (error) {
        console.error('Error loading SHAP explanations:', error);
      }
    };

    if (viewMode === 'shap') {
      loadSampleExplanations();
    }
  }, [viewMode]);

  const handleRefreshShap = async () => {
    setIsLoadingShap(true);
    try {
      // Simulate API call to refresh explanations
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Reload sample explanations
      const sampleXgbResponse = await fetch('/data_cache/shap_explanations/working_xgboost_explanation.json');
      if (sampleXgbResponse.ok) {
        const sampleXgbData = await sampleXgbResponse.json();
        setXgbExplanation(sampleXgbData);
      }
      
      const sampleDnabertResponse = await fetch('/data_cache/shap_explanations/working_dnabert_explanation.json');
      if (sampleDnabertResponse.ok) {
        const sampleDnabertData = await sampleDnabertResponse.json();
        setDnabertExplanation(sampleDnabertData);
      }
    } catch (error) {
      console.error('Error refreshing SHAP explanations:', error);
    } finally {
      setIsLoadingShap(false);
    }
  };

  const selectedData = predictions.find(
    (item) => item.antibiotic === selectedAntibiotic,
  );
    const getPredictionColor = (prediction: "S" | "I" | "R") => {
    switch (prediction) {
      case "R":
        return "bg-red-500";
      case "I":
        return "bg-yellow-500";
      case "S":
        return "bg-green-500";
      default:
        return "bg-gray-500";
    }
  };

  const getImpactColor = (impact: number) => {
    if (impact > 0.7) return "bg-red-600";
    if (impact > 0.5) return "bg-red-400";
    if (impact > 0.3) return "bg-red-300";
    if (impact > 0.1) return "bg-red-200";
    if (impact > -0.1) return "bg-gray-200";
    if (impact > -0.3) return "bg-green-200";
    if (impact > -0.5) return "bg-green-300";
    if (impact > -0.7) return "bg-green-400";
    return "bg-green-600";
  };

  return (
    <Card className="w-full bg-white shadow-md">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <div>
            <CardTitle className="text-xl">
              Genetic Markers Explainability
            </CardTitle>
            <CardDescription>
              Visualizing genetic markers contributing to antibiotic resistance
              predictions
            </CardDescription>
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setZoomLevel((prev) => Math.max(0.5, prev - 0.1))}
              disabled={zoomLevel <= 0.5}
            >
              <ZoomOutIcon className="h-4 w-4" />
            </Button>
            <span className="text-sm">{Math.round(zoomLevel * 100)}%</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setZoomLevel((prev) => Math.min(2, prev + 0.1))}
              disabled={zoomLevel >= 2}
            >
              <ZoomInIcon className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="mt-2">
          <Tabs
            defaultValue="heatmap"
            onValueChange={(value) =>
              setViewMode(value as "heatmap" | "network" | "dna-helix" | "shap" | "genetic-markers")
            }
          >
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="heatmap">Heatmap</TabsTrigger>
              <TabsTrigger value="network">Network</TabsTrigger>
              <TabsTrigger value="dna-helix">DNA Helix</TabsTrigger>
              <TabsTrigger value="shap">SHAP Analysis</TabsTrigger>
              <TabsTrigger value="genetic-markers">Genetic Markers</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-4">
          {analysisSummary && (
            <div className="mb-4 p-3 bg-blue-50 rounded-lg">
              <h4 className="font-medium text-sm mb-2">
                Genome Analysis Summary
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                <div>
                  Length:{" "}
                  {(analysisSummary.sequenceLength / 1000000).toFixed(1)}M bp
                </div>
                <div>Quality: {analysisSummary.sequenceQuality}</div>
                <div>GC Content: {analysisSummary.gcContent}%</div>
                <div>
                  Resistance Genes: {analysisSummary.resistanceGenesFound}
                </div>
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-2 mb-4">
            {predictions.map((item) => (
              <Badge
                key={item.antibiotic}
                variant={
                  selectedAntibiotic === item.antibiotic ? "default" : "outline"
                }
                className={`cursor-pointer ${selectedAntibiotic === item.antibiotic ? "" : "hover:bg-accent"}`}
                onClick={() => setSelectedAntibiotic(item.antibiotic)}
              >
                {item.antibiotic}
                <span
                  className={`ml-1 inline-block w-2 h-2 rounded-full ${getPredictionColor(item.prediction)}`}
                ></span>
              </Badge>
            ))}
          </div>
        </div>

        {viewMode === "heatmap" && selectedData && (
          <div className="overflow-x-auto">
            <div className="text-sm font-medium mb-4">
              <div className="flex items-center justify-between">
                <div>
                  ML Analysis for {selectedData.antibiotic}
                  <span
                    className={`ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${selectedData.prediction === "R" ? "bg-red-100 text-red-800" : selectedData.prediction === "I" ? "bg-yellow-100 text-yellow-800" : "bg-green-100 text-green-800"}`}
                  >
                    {selectedData.prediction === "R"
                      ? "Resistant"
                      : selectedData.prediction === "I"
                        ? "Intermediate"
                        : "Susceptible"}
                  </span>
                </div>
                <div className="text-xs text-gray-600">
                  Confidence: {(selectedData.confidence * 100).toFixed(1)}%
                </div>
              </div>
              <p className="text-xs text-gray-600 mt-1">
                {selectedData.reasoning}
              </p>
            </div>

            <div
              className="space-y-3"
              style={{
                transform: `scale(${zoomLevel})`,
                transformOrigin: "top left",
              }}
            >
              {selectedData.markers.map((marker) => (
                <div key={marker.id} className="flex items-center">
                  <div className="w-1/3 font-medium text-sm">
                    <div>{marker.name}</div>
                    <div className="text-xs text-gray-500">
                      {marker.type === "gene" ? "Resistance Gene" : "Mutation"}
                    </div>
                  </div>
                  <div className="w-1/3 relative">
                    <div className="h-6 w-full bg-gray-100 rounded-md">
                      <div
                        className={`h-6 rounded-md ${getImpactColor(marker.impact)}`}
                        style={{ width: `${Math.abs(marker.impact) * 100}%` }}
                      ></div>
                    </div>
                  </div>
                  <div className="w-1/3 pl-4 flex items-center">
                    <span className="text-sm font-mono">
                      {marker.impact > 0 ? "+" : ""}
                      {(marker.impact * 100).toFixed(1)}%
                    </span>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="ml-1 h-6 w-6 p-0"
                          >
                            <InfoIcon className="h-4 w-4" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="font-medium">{marker.name}</p>
                          <p className="text-sm">{marker.description}</p>
                          <p className="text-xs mt-1">
                            Type: {marker.type} | Confidence:{" "}
                            {(marker.confidence * 100).toFixed(1)}%
                          </p>
                          <p className="text-xs">
                            Impact:{" "}
                            {marker.impact > 0
                              ? "Promotes resistance"
                              : "Supports susceptibility"}
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {viewMode === "network" && (
          <div
            className="border rounded-md bg-gray-50 overflow-hidden"
            style={{ height: "500px" }}
          >
            <NetworkVisualization
              predictions={predictions}
              selectedAntibiotic={selectedAntibiotic}
              zoomLevel={zoomLevel}
            />
          </div>
        )}

        {viewMode === "dna-helix" && (
          <div className="border rounded-md bg-gray-50 overflow-hidden">
            <DNAHelixVisualization
              predictions={predictions}
              genomeId={genomeId}
              width={800}
              height={500}
            />
          </div>
        )}

        {viewMode === "shap" && (
          <div className="space-y-6">
            {/* SHAP Controls */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  SHAP Explanations
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRefreshShap}
                    disabled={isLoadingShap}
                  >
                    <RefreshCwIcon className={`h-4 w-4 ${isLoadingShap ? 'animate-spin' : ''}`} />
                    {isLoadingShap ? 'Loading...' : 'Refresh'}
                  </Button>
                </CardTitle>
                <CardDescription>
                  Model explainability using SHAP values for feature importance
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* XGBoost Explanation */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        XGBoost Explanation
                        <Badge variant="outline">f0849bdd</Badge>
                      </CardTitle>
                      <CardDescription>
                        Tree-based model with k-mer features
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {xgbExplanation ? (
                        <ShapVisualization
                          explanation={xgbExplanation}
                          isLoading={isLoadingShap}
                          onRefresh={handleRefreshShap}
                        />
                      ) : (
                        <div className="text-center py-8">
                          <InfoIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
                          <p className="text-gray-500">No XGBoost explanation available</p>
                          <p className="text-sm text-gray-400">
                            Select an antibiotic and generate predictions
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* DNABERT Explanation */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        DNABERT Explanation
                        <Badge variant="outline">ce13dcc6</Badge>
                      </CardTitle>
                      <CardDescription>
                        Transformer model with DNA sequence analysis
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {dnabertExplanation ? (
                        <ShapVisualization
                          explanation={dnabertExplanation}
                          isLoading={isLoadingShap}
                          onRefresh={handleRefreshShap}
                        />
                      ) : (
                        <div className="text-center py-8">
                          <InfoIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
                          <p className="text-gray-500">No DNABERT explanation available</p>
                          <p className="text-sm text-gray-400">
                            Select an antibiotic and generate predictions
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </CardContent>
            </Card>

            {/* Comparative Analysis */}
            {xgbExplanation && dnabertExplanation && (
              <Card>
                <CardHeader>
                  <CardTitle>Comparative Analysis</CardTitle>
                  <CardDescription>
                    Compare XGBoost vs DNABERT explanations side-by-side
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ComparativeExplanation
                    xgboostExplanation={xgbExplanation}
                    transformerExplanation={dnabertExplanation}
                    antibiotic={selectedAntibiotic}
                  />
                </CardContent>
              </Card>
            )}

            {/* Force Plots */}
            {xgbExplanation && (
              <Card>
                <CardHeader>
                  <CardTitle>XGBoost Force Plot</CardTitle>
                  <CardDescription>
                    Interactive force plot showing feature contributions
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ForcePlot explanation={xgbExplanation} />
                </CardContent>
              </Card>
            )}

            {dnabertExplanation && (
              <Card>
                <CardHeader>
                  <CardTitle>DNABERT Force Plot</CardTitle>
                  <CardDescription>
                    Interactive force plot showing token contributions
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ForcePlot explanation={dnabertExplanation} />
                </CardContent>
              </Card>
            )}
          </div>
        )}

        <div className="mt-6 text-xs text-gray-500">
          <p>Genome ID: {genomeId}</p>
          <p className="mt-1">
            <strong>Machine Learning Analysis:</strong> Impact values represent
            each genetic marker's contribution to the resistance prediction
            model.
          </p>
          <p>
            Positive values indicate resistance-promoting factors, negative
            values support susceptibility.
          </p>
          <p className="mt-1">
            Analysis based on resistance gene detection, chromosomal mutations,
            and sequence quality assessment.
          </p>
        </div>
      </CardContent>
    </Card>
  );
};

// DNA-inspired Network visualization component using SVG
interface NetworkVisualizationProps {
  predictions: PredictionResult[];
  selectedAntibiotic: string;
  zoomLevel: number;
}

interface NetworkNode {
  id: string;
  name: string;
  x: number;
  y: number;
  type: "antibiotic" | "gene" | "mutation";
  prediction?: "S" | "I" | "R";
  impact?: number;
  description?: string;
  sequence?: string;
}

interface NetworkLink {
  source: string;
  target: string;
  impact: number;
  strength: number;
}

interface DNAHelix {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  strength: number;
}

const NetworkVisualization: React.FC<NetworkVisualizationProps> = ({
  predictions,
  selectedAntibiotic,
  zoomLevel,
}) => {
  const [nodes, setNodes] = useState<NetworkNode[]>([]);
  const [links, setLinks] = useState<NetworkLink[]>([]);
  const [dnaHelixes, setDnaHelixes] = useState<DNAHelix[]>([]);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [animationPhase, setAnimationPhase] = useState<number>(0);

  useEffect(() => {
    if (!predictions || predictions.length === 0) return;

    const selectedPrediction = predictions.find(
      (p) => p.antibiotic === selectedAntibiotic,
    );
    if (!selectedPrediction) return;

    const newNodes: NetworkNode[] = [];
    const newLinks: NetworkLink[] = [];
    const newHelixes: DNAHelix[] = [];

    // Add antibiotic node at center (like a nucleus)
    newNodes.push({
      id: selectedPrediction.antibiotic,
      name: selectedPrediction.antibiotic,
      x: 400,
      y: 250,
      type: "antibiotic",
      prediction: selectedPrediction.prediction,
      sequence: "TARGET",
    });

    // Create DNA-like double helix structure around the antibiotic
    const radius = 180;
    const helixRadius = 20;
    const angleStep = (2 * Math.PI) / selectedPrediction.markers.length;

    selectedPrediction.markers.forEach((marker, index) => {
      const angle = index * angleStep;
      const baseX = 400 + radius * Math.cos(angle);
      const baseY = 250 + radius * Math.sin(angle);

      // Create complementary base pairs for DNA structure
      const helixOffset = Math.sin(angle * 3) * helixRadius;
      const x = baseX + helixOffset;
      const y = baseY;

      // Generate mock DNA sequence based on marker type
      const sequences = {
        gene: ["ATCG", "GCTA", "TACG", "CGAT"],
        mutation: ["MUTX", "DELX", "INSX", "SNPX"],
      };
      const sequenceOptions = sequences[
        marker.type as keyof typeof sequences
      ] || ["UNKN"];
      const sequence = sequenceOptions[index % sequenceOptions.length];

      newNodes.push({
        id: marker.id,
        name: marker.name,
        x,
        y,
        type: marker.type,
        impact: marker.impact,
        description: marker.description,
        sequence,
      });

      // Create DNA helix connections
      const linkStrength = Math.abs(marker.impact);
      newLinks.push({
        source: marker.id,
        target: selectedPrediction.antibiotic,
        impact: marker.impact,
        strength: linkStrength,
      });

      // Add DNA helix visual elements
      if (index < selectedPrediction.markers.length - 1) {
        const nextAngle = (index + 1) * angleStep;
        const nextBaseX = 400 + radius * Math.cos(nextAngle);
        const nextBaseY = 250 + radius * Math.sin(nextAngle);
        const nextHelixOffset = Math.sin(nextAngle * 3) * helixRadius;

        newHelixes.push({
          x1: x,
          y1: y,
          x2: nextBaseX + nextHelixOffset,
          y2: nextBaseY,
          strength:
            (linkStrength +
              Math.abs(
                selectedPrediction.markers[
                  (index + 1) % selectedPrediction.markers.length
                ].impact,
              )) /
            2,
        });
      }
    });

    // Close the DNA ring
    if (selectedPrediction.markers.length > 2) {
      const firstMarker = selectedPrediction.markers[0];
      const lastMarker =
        selectedPrediction.markers[selectedPrediction.markers.length - 1];
      const firstAngle = 0;
      const lastAngle = (selectedPrediction.markers.length - 1) * angleStep;

      const firstX =
        400 +
        radius * Math.cos(firstAngle) +
        Math.sin(firstAngle * 3) * helixRadius;
      const firstY = 250 + radius * Math.sin(firstAngle);
      const lastX =
        400 +
        radius * Math.cos(lastAngle) +
        Math.sin(lastAngle * 3) * helixRadius;
      const lastY = 250 + radius * Math.sin(lastAngle);

      newHelixes.push({
        x1: lastX,
        y1: lastY,
        x2: firstX,
        y2: firstY,
        strength:
          (Math.abs(firstMarker.impact) + Math.abs(lastMarker.impact)) / 2,
      });
    }

    setNodes(newNodes);
    setLinks(newLinks);
    setDnaHelixes(newHelixes);
  }, [predictions, selectedAntibiotic]);

  // Animation for DNA helix
  useEffect(() => {
    const interval = setInterval(() => {
      setAnimationPhase((prev) => (prev + 0.1) % (2 * Math.PI));
    }, 100);
    return () => clearInterval(interval);
  }, []);

  const getNodeColor = (node: NetworkNode) => {
    if (node.type === "antibiotic") {
      // Central nucleus-like coloring
      switch (node.prediction) {
        case "R":
          return "#dc2626"; // Deep red for resistance
        case "I":
          return "#d97706"; // Orange for intermediate
        case "S":
          return "#059669"; // Green for susceptible
        default:
          return "#4b5563";
      }
    } else {
      // DNA base-like coloring
      const impact = node.impact || 0;
      if (node.type === "gene") {
        // Gene nodes use blue-purple spectrum (like DNA bases)
        if (impact > 0.5) return "#7c3aed"; // Purple for high resistance impact
        if (impact > 0.2) return "#3b82f6"; // Blue for moderate impact
        if (impact > -0.2) return "#06b6d4"; // Cyan for neutral
        return "#10b981"; // Emerald for susceptibility
      } else {
        // Mutation nodes use red-orange spectrum
        if (impact > 0.5) return "#dc2626"; // Red for high resistance
        if (impact > 0.2) return "#ea580c"; // Orange for moderate
        if (impact > -0.2) return "#84cc16"; // Lime for neutral
        return "#22c55e"; // Green for susceptibility
      }
    }
  };

  const getNodeSize = (node: NetworkNode) => {
    if (node.type === "antibiotic") return 35; // Larger nucleus
    const impact = Math.abs(node.impact || 0);
    return 12 + impact * 15; // More variation in size
  };

  const getLinkColor = (link: NetworkLink) => {
    // DNA strand-like coloring
    const strength = link.strength || Math.abs(link.impact);
    if (link.impact > 0.5) return "#dc2626"; // Strong resistance connection
    if (link.impact > 0.2) return "#f59e0b"; // Moderate resistance
    if (link.impact > -0.2) return "#6b7280"; // Neutral
    return "#059669"; // Susceptibility connection
  };

  const getLinkWidth = (link: NetworkLink) => {
    return Math.max(2, Math.abs(link.impact) * 6); // Thicker DNA strands
  };

  const getHelixColor = (helix: DNAHelix) => {
    // DNA backbone coloring
    if (helix.strength > 0.6) return "#8b5cf6"; // Purple for strong connections
    if (helix.strength > 0.3) return "#3b82f6"; // Blue for moderate
    return "#06b6d4"; // Cyan for weak
  };

  if (nodes.length === 0) {
    return (
      <div className="flex justify-center items-center h-full">
        <div className="text-center text-gray-500">
          <p>No data available for network visualization.</p>
          <p className="text-sm">
            Please select an antibiotic with resistance data.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full relative overflow-hidden bg-gradient-to-br from-slate-50 to-blue-50">
      <svg
        width="100%"
        height="100%"
        viewBox="0 0 800 500"
        style={{ transform: `scale(${zoomLevel})`, transformOrigin: "center" }}
      >
        {/* DNA Helix Background */}
        <defs>
          <pattern
            id="dnaPattern"
            x="0"
            y="0"
            width="20"
            height="20"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="10" cy="10" r="1" fill="#e2e8f0" opacity="0.3" />
          </pattern>
          <linearGradient
            id="helixGradient"
            x1="0%"
            y1="0%"
            x2="100%"
            y2="100%"
          >
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.3" />
            <stop offset="50%" stopColor="#8b5cf6" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.3" />
          </linearGradient>
        </defs>

        <rect width="100%" height="100%" fill="url(#dnaPattern)" />

        {/* DNA Helix Strands */}
        {dnaHelixes.map((helix, index) => {
          const animatedOffset = Math.sin(animationPhase + index * 0.5) * 3;
          return (
            <g key={`helix-${index}`}>
              {/* Main helix strand */}
              <path
                d={`M ${helix.x1 + animatedOffset} ${helix.y1} Q ${(helix.x1 + helix.x2) / 2} ${(helix.y1 + helix.y2) / 2 + animatedOffset * 2} ${helix.x2 - animatedOffset} ${helix.y2}`}
                stroke={getHelixColor(helix)}
                strokeWidth="3"
                fill="none"
                opacity="0.7"
              />
              {/* Complementary strand */}
              <path
                d={`M ${helix.x1 - animatedOffset} ${helix.y1} Q ${(helix.x1 + helix.x2) / 2} ${(helix.y1 + helix.y2) / 2 - animatedOffset * 2} ${helix.x2 + animatedOffset} ${helix.y2}`}
                stroke={getHelixColor(helix)}
                strokeWidth="2"
                fill="none"
                opacity="0.5"
                strokeDasharray="5,3"
              />
            </g>
          );
        })}

        {/* Resistance/Susceptibility Links */}
        {links.map((link, index) => {
          const sourceNode = nodes.find((n) => n.id === link.source);
          const targetNode = nodes.find((n) => n.id === link.target);
          if (!sourceNode || !targetNode) return null;

          return (
            <g key={`link-${index}`}>
              <line
                x1={sourceNode.x}
                y1={sourceNode.y}
                x2={targetNode.x}
                y2={targetNode.y}
                stroke={getLinkColor(link)}
                strokeWidth={getLinkWidth(link)}
                opacity={0.4}
                strokeDasharray={link.impact > 0 ? "none" : "8,4"}
              />
              {/* Impact indicator */}
              <circle
                cx={(sourceNode.x + targetNode.x) / 2}
                cy={(sourceNode.y + targetNode.y) / 2}
                r="4"
                fill={getLinkColor(link)}
                opacity="0.8"
              >
                <animate
                  attributeName="r"
                  values="3;6;3"
                  dur="2s"
                  repeatCount="indefinite"
                />
              </circle>
            </g>
          );
        })}

        {/* Genetic Marker Nodes (DNA Bases) */}
        {nodes.map((node) => (
          <g key={node.id}>
            {/* Node shadow */}
            <circle
              cx={node.x + 2}
              cy={node.y + 2}
              r={getNodeSize(node)}
              fill="#000000"
              opacity="0.1"
            />
            {/* Main node */}
            <circle
              cx={node.x}
              cy={node.y}
              r={getNodeSize(node)}
              fill={getNodeColor(node)}
              stroke={node.type === "antibiotic" ? "#ffffff" : "#f8fafc"}
              strokeWidth={node.type === "antibiotic" ? 4 : 2}
              opacity={hoveredNode === node.id ? 1 : 0.9}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              style={{ cursor: "pointer" }}
            >
              {node.type !== "antibiotic" && (
                <animate
                  attributeName="r"
                  values={`${getNodeSize(node)};${getNodeSize(node) + 2};${getNodeSize(node)}`}
                  dur="3s"
                  repeatCount="indefinite"
                />
              )}
            </circle>

            {/* DNA sequence label */}
            {node.sequence && (
              <text
                x={node.x}
                y={node.y + 4}
                textAnchor="middle"
                fontSize={node.type === "antibiotic" ? "10" : "8"}
                fill="white"
                fontWeight="bold"
                fontFamily="monospace"
              >
                {node.sequence}
              </text>
            )}

            {/* Node name */}
            <text
              x={node.x}
              y={node.y + getNodeSize(node) + 18}
              textAnchor="middle"
              fontSize="11"
              fill="#1f2937"
              fontWeight={node.type === "antibiotic" ? "bold" : "medium"}
            >
              {node.name.length > 12
                ? node.name.substring(0, 12) + "..."
                : node.name}
            </text>

            {/* Impact percentage */}
            {node.impact !== undefined && (
              <text
                x={node.x}
                y={node.y + getNodeSize(node) + 32}
                textAnchor="middle"
                fontSize="9"
                fill={node.impact > 0 ? "#dc2626" : "#059669"}
                fontWeight="bold"
              >
                {node.impact > 0 ? "+" : ""}
                {(node.impact * 100).toFixed(0)}%
              </text>
            )}
          </g>
        ))}
      </svg>

      {/* Enhanced DNA-themed Legend */}
      <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur-sm p-4 rounded-xl shadow-lg border border-blue-200 text-xs">
        <div className="font-bold mb-3 text-blue-900 flex items-center">
          <div className="w-2 h-2 bg-blue-500 rounded-full mr-2 animate-pulse"></div>
          DNA Network Analysis
        </div>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 border-2 border-white"></div>
            <span className="font-medium">Target Antibiotic</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-purple-500"></div>
            <span>Resistance Gene</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-orange-500"></div>
            <span>Chromosomal Mutation</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-1 bg-gradient-to-r from-blue-400 to-purple-400 rounded"></div>
            <span>DNA Helix Structure</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-1 bg-red-500 rounded"></div>
            <span>Resistance Connection</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-1 bg-green-500 rounded"
              style={{ borderStyle: "dashed", borderWidth: "1px 0" }}
            ></div>
            <span>Susceptibility Connection</span>
          </div>
        </div>
        <div className="mt-3 pt-2 border-t border-blue-200 text-gray-600">
          <div className="font-medium text-blue-800 mb-1">
            DNA Sequence Codes:
          </div>
          <div className="grid grid-cols-2 gap-1 text-xs">
            <span>ATCG - Gene bases</span>
            <span>MUTX - Mutations</span>
          </div>
        </div>
      </div>

      {/* Analysis Info Panel */}
      <div className="absolute top-4 right-4 bg-white/95 backdrop-blur-sm p-3 rounded-xl shadow-lg border border-blue-200 text-xs max-w-xs">
        <div className="font-bold mb-2 text-blue-900">Genomic Analysis</div>
        <div className="space-y-1 text-gray-700">
          <div>
            🧬 <strong>Network Structure:</strong> DNA double helix model
          </div>
          <div>
            🎯 <strong>Central Target:</strong> {selectedAntibiotic}
          </div>
          <div>
            📊 <strong>Genetic Markers:</strong> {nodes.length - 1} detected
          </div>
          <div>
            🔗 <strong>Interactions:</strong> {links.length} resistance pathways
          </div>
        </div>
        <div className="mt-2 pt-2 border-t border-blue-200">
          <div className="text-blue-700 font-medium">Impact Scale:</div>
          <div className="flex items-center justify-between mt-1">
            <span className="text-green-600">Susceptible</span>
            <div className="flex-1 mx-2 h-2 bg-gradient-to-r from-green-400 via-yellow-400 to-red-500 rounded"></div>
            <span className="text-red-600">Resistant</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExplainabilityView;
