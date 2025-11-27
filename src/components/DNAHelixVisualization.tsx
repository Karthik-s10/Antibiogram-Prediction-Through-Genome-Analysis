import React, { useState, useEffect } from "react";
import { PredictionResult } from "@/lib/resistancePredictor";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { RotateCw, ZoomIn, ZoomOut, Info } from "lucide-react";

interface DNAHelixVisualizationProps {
  predictions: PredictionResult[];
  genomeId?: string;
  width?: number;
  height?: number;
}

interface DNABase {
  id: string;
  name: string;
  position: number;
  angle: number;
  impact: number;
  antibiotic: string;
  prediction: "S" | "I" | "R";
  confidence: number;
  description?: string;
}

const DNAHelixVisualization: React.FC<DNAHelixVisualizationProps> = ({
  predictions = [],
  genomeId = "unknown",
  width = 800,
  height = 500,
}) => {
  const [rotation, setRotation] = useState<number>(0);
  const [autoRotate, setAutoRotate] = useState<boolean>(true);
  const [zoom, setZoom] = useState<number>(1);
  const [bases, setBases] = useState<DNABase[]>([]);
  const [hoveredBase, setHoveredBase] = useState<string | null>(null);

  // Generate DNA bases from predictions
  useEffect(() => {
    if (!predictions || predictions.length === 0) return;

    const newBases: DNABase[] = [];
    const basesPerTurn = 10; // Number of base pairs per complete turn of DNA helix
    const totalBases = predictions.length * 2; // Each prediction gets 2 bases (one on each strand)

    // Sort predictions by impact for better visualization
    const sortedPredictions = [...predictions].sort((a, b) => {
      // Calculate average impact for each prediction
      const avgImpactA =
        a.markers.reduce((sum, marker) => sum + marker.impact, 0) /
        (a.markers.length || 1);
      const avgImpactB =
        b.markers.reduce((sum, marker) => sum + marker.impact, 0) /
        (b.markers.length || 1);
      return avgImpactB - avgImpactA; // Sort by impact (highest first)
    });

    // Create DNA bases
    sortedPredictions.forEach((prediction, index) => {
      // Calculate average impact for this prediction
      const avgImpact =
        prediction.markers.reduce((sum, marker) => sum + marker.impact, 0) /
        (prediction.markers.length || 1);

      // Calculate position along the helix
      const position = index / predictions.length;
      const angle = (index * (360 / basesPerTurn)) % 360;

      // Create base on first strand
      newBases.push({
        id: `${prediction.antibiotic}-1`,
        name: prediction.antibiotic,
        position,
        angle,
        impact: avgImpact,
        antibiotic: prediction.antibiotic,
        prediction: prediction.prediction,
        confidence: prediction.confidence,
        description: prediction.reasoning,
      });

      // Create complementary base on second strand (180 degrees opposite)
      newBases.push({
        id: `${prediction.antibiotic}-2`,
        name: prediction.antibiotic,
        position,
        angle: (angle + 180) % 360,
        impact: avgImpact,
        antibiotic: prediction.antibiotic,
        prediction: prediction.prediction,
        confidence: prediction.confidence,
        description: prediction.reasoning,
      });
    });

    setBases(newBases);
  }, [predictions]);

  // Auto-rotation effect
  useEffect(() => {
    if (!autoRotate) return;

    const interval = setInterval(() => {
      setRotation((prev) => (prev + 1) % 360);
    }, 100);

    return () => clearInterval(interval);
  }, [autoRotate]);

  // Get color based on prediction and impact
  const getBaseColor = (base: DNABase) => {
    if (base.prediction === "R") {
      // Red spectrum for resistant
      if (base.impact > 0.7) return "#ef4444"; // Strong red
      if (base.impact > 0.4) return "#f87171"; // Medium red
      return "#fca5a5"; // Light red
    } else if (base.prediction === "I") {
      // Yellow/orange spectrum for intermediate
      if (base.impact > 0.5) return "#f59e0b"; // Strong orange
      if (base.impact > 0.3) return "#fbbf24"; // Medium yellow
      return "#fcd34d"; // Light yellow
    } else {
      // Green spectrum for susceptible
      if (base.impact < -0.5) return "#10b981"; // Strong green
      if (base.impact < -0.2) return "#34d399"; // Medium green
      return "#6ee7b7"; // Light green
    }
  };

  // Get backbone color
  const getBackboneColor = (index: number) => {
    const colors = ["#3b82f6", "#8b5cf6", "#6366f1"];
    return colors[index % colors.length];
  };

  // Calculate 3D position with perspective
  const calculatePosition = (base: DNABase) => {
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.35;
    const verticalOffset = height * 0.7 * base.position - height * 0.35;

    // Apply rotation to angle
    const rotatedAngle = (base.angle + rotation) % 360;
    const angleRad = (rotatedAngle * Math.PI) / 180;

    // Calculate position with perspective
    const x = centerX + radius * Math.cos(angleRad);
    const y = centerY + verticalOffset;
    const z = radius * Math.sin(angleRad); // Z-coordinate for depth

    // Apply perspective scaling based on z
    const scale = (1000 + z) / 1000;

    return {
      x,
      y,
      scale: scale * zoom,
      depth: z, // Used for z-index ordering
    };
  };

  // Calculate backbone curve points
  const calculateBackboneCurve = (startIndex: number, endIndex: number) => {
    const points: { x: number; y: number; z: number }[] = [];
    const steps = 20;

    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const position = startIndex + (endIndex - startIndex) * t;
      const angle = (position * 36 + rotation) % 360; // 36 degrees per base
      const angleRad = (angle * Math.PI) / 180;

      const centerX = width / 2;
      const centerY = height / 2;
      const radius = Math.min(width, height) * 0.35;
      const verticalOffset =
        height * 0.7 * (position / predictions.length) - height * 0.35;

      const x = centerX + radius * Math.cos(angleRad);
      const y = centerY + verticalOffset;
      const z = radius * Math.sin(angleRad);

      points.push({ x, y, z });
    }

    return points;
  };

  // Generate SVG path for backbone
  const generateBackbonePath = (strand: number) => {
    const points = calculateBackboneCurve(0, predictions.length - 1);
    const offset = strand === 1 ? 0 : Math.PI; // 180 degrees offset for second strand

    let path = "M ";
    points.forEach((point, index) => {
      const angleRad =
        (((point.z > 0 ? 0 : 180) + rotation + (strand === 1 ? 0 : 180)) *
          Math.PI) /
        180;
      const offsetX = 10 * Math.cos(angleRad);
      const offsetY = 5 * Math.sin(angleRad);

      if (index === 0) {
        path += `${point.x + offsetX} ${point.y + offsetY}`;
      } else {
        path += ` L ${point.x + offsetX} ${point.y + offsetY}`;
      }
    });

    return path;
  };

  // Sort bases by depth for proper rendering order
  const sortedBases = [...bases].sort((a, b) => {
    const posA = calculatePosition(a);
    const posB = calculatePosition(b);
    return posA.depth - posB.depth;
  });

  return (
    <div className="w-full h-full bg-gradient-to-br from-slate-50 to-blue-50 rounded-lg overflow-hidden border border-blue-200">
      <div className="p-4 flex justify-between items-center bg-white border-b border-blue-200">
        <div className="text-lg font-semibold text-blue-900 flex items-center">
          <svg
            className="w-5 h-5 mr-2"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M8 12H16"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M12 8V16"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          DNA Helix Visualization
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAutoRotate(!autoRotate)}
            className={autoRotate ? "bg-blue-100" : ""}
          >
            <RotateCw
              className={`h-4 w-4 ${autoRotate ? "animate-spin" : ""}`}
            />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setZoom(Math.max(0.5, zoom - 0.1))}
            disabled={zoom <= 0.5}
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setZoom(Math.min(2, zoom + 0.1))}
            disabled={zoom >= 2}
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="relative" style={{ width, height }}>
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
          {/* DNA Backbone Strands */}
          <path
            d={generateBackbonePath(1)}
            fill="none"
            stroke={getBackboneColor(0)}
            strokeWidth="4"
            strokeLinecap="round"
            opacity="0.7"
          />
          <path
            d={generateBackbonePath(2)}
            fill="none"
            stroke={getBackboneColor(1)}
            strokeWidth="4"
            strokeLinecap="round"
            opacity="0.7"
          />

          {/* DNA Bases */}
          {sortedBases.map((base) => {
            const { x, y, scale, depth } = calculatePosition(base);
            const baseSize = 20 * scale;
            const isHovered = hoveredBase === base.id;
            const isFirstStrand = base.id.endsWith("-1");
            const baseColor = getBaseColor(base);

            // Only show labels and arrows for first strand bases
            const showLabel =
              isFirstStrand && (base.impact > 0.5 || base.impact < -0.5);

            return (
              <g key={base.id}>
                {/* Base connection line */}
                {isFirstStrand && (
                  <line
                    x1={x}
                    y1={y}
                    x2={width / 2}
                    y2={y}
                    stroke={baseColor}
                    strokeWidth={2 * scale}
                    strokeDasharray={depth > 0 ? "none" : "4,2"}
                    opacity={0.5}
                  />
                )}

                {/* Base circle */}
                <circle
                  cx={x}
                  cy={y}
                  r={baseSize}
                  fill={baseColor}
                  stroke="white"
                  strokeWidth={isHovered ? 3 : 1}
                  opacity={depth > 0 ? 1 : 0.7}
                  style={{ cursor: "pointer" }}
                  onMouseEnter={() => setHoveredBase(base.id)}
                  onMouseLeave={() => setHoveredBase(null)}
                />

                {/* Base label */}
                {depth > 0 && (
                  <text
                    x={x}
                    y={y}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="white"
                    fontSize={10 * scale}
                    fontWeight="bold"
                  >
                    {base.prediction}
                  </text>
                )}

                {/* Arrows and labels for significant bases */}
                {showLabel && depth > 0 && (
                  <g>
                    <line
                      x1={x + baseSize * 1.2}
                      y1={y}
                      x2={x + baseSize * 2.5}
                      y2={y}
                      stroke={base.impact > 0 ? "#ef4444" : "#10b981"}
                      strokeWidth={2}
                      markerEnd={`url(#arrow-${base.impact > 0 ? "red" : "green"})`}
                    />
                    <text
                      x={x + baseSize * 3}
                      y={y}
                      textAnchor="start"
                      dominantBaseline="middle"
                      fill={base.impact > 0 ? "#ef4444" : "#10b981"}
                      fontSize={12 * scale}
                      fontWeight="bold"
                    >
                      {base.name}
                      <tspan fontSize={10 * scale} fill="#64748b">
                        {` (${base.impact > 0 ? "+" : ""}${(base.impact * 100).toFixed(0)}%)`}
                      </tspan>
                    </text>
                  </g>
                )}
              </g>
            );
          })}

          {/* Arrow markers for the labels */}
          <defs>
            <marker
              id="arrow-red"
              viewBox="0 0 10 10"
              refX="5"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#ef4444" />
            </marker>
            <marker
              id="arrow-green"
              viewBox="0 0 10 10"
              refX="5"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#10b981" />
            </marker>
          </defs>
        </svg>

        {/* Tooltip for hovered base */}
        {hoveredBase && (
          <TooltipProvider>
            <Tooltip open={!!hoveredBase}>
              <TooltipTrigger asChild>
                <div className="absolute top-0 left-0 w-1 h-1 opacity-0" />
              </TooltipTrigger>
              <TooltipContent side="right" className="max-w-xs">
                {(() => {
                  const base = bases.find((b) => b.id === hoveredBase);
                  if (!base) return null;
                  return (
                    <div className="space-y-2">
                      <div className="font-bold">{base.antibiotic}</div>
                      <div className="flex items-center">
                        <span
                          className={`inline-block w-3 h-3 rounded-full mr-2 ${getBaseColor(base)}`}
                        ></span>
                        <span>
                          {base.prediction === "R"
                            ? "Resistant"
                            : base.prediction === "I"
                              ? "Intermediate"
                              : "Susceptible"}
                          {` (${(base.confidence * 100).toFixed(0)}% confidence)`}
                        </span>
                      </div>
                      <div className="text-xs">{base.description}</div>
                    </div>
                  );
                })()}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>

      {/* Legend */}
      <div className="p-4 bg-white border-t border-blue-200 flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <div className="flex items-center">
            <span className="inline-block w-3 h-3 rounded-full bg-red-500 mr-1"></span>
            <span className="text-sm">Resistant (R)</span>
          </div>
          <div className="flex items-center">
            <span className="inline-block w-3 h-3 rounded-full bg-yellow-500 mr-1"></span>
            <span className="text-sm">Intermediate (I)</span>
          </div>
          <div className="flex items-center">
            <span className="inline-block w-3 h-3 rounded-full bg-green-500 mr-1"></span>
            <span className="text-sm">Susceptible (S)</span>
          </div>
        </div>
        <div className="text-xs text-gray-500 flex items-center">
          <Info className="h-3 w-3 mr-1" />
          <span>Genome ID: {genomeId}</span>
        </div>
      </div>
    </div>
  );
};

export default DNAHelixVisualization;
