import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { 
  ArrowUpIcon, 
  ArrowDownIcon, 
  MinusIcon, 
  InfoIcon,
  DownloadIcon,
  ZoomInIcon,
  ZoomOutIcon 
} from "lucide-react";

interface ForcePlotProps {
  explanation: {
    force_plot_data?: any;
    prediction: string;
    probability?: number;
    model_type: string;
    antibiotic: string;
  };
  className?: string;
}

export function ForcePlot({ explanation, className = "" }: ForcePlotProps) {
  const [zoomLevel, setZoomLevel] = useState(1);
  const [showDetails, setShowDetails] = useState(true);

  if (!explanation.force_plot_data) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <div className="text-center text-gray-500">
            <InfoIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Force plot data not available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const { base_value, shap_values, feature_names, feature_importance } = explanation.force_plot_data;
  
  // Calculate cumulative values for force plot
  let cumulativeValue = base_value;
  const contributions = feature_importance.slice(0, 10).map(([feature, value]) => {
    const prevValue = cumulativeValue;
    cumulativeValue += value;
    
    return {
      feature,
      value,
      cumulative: cumulativeValue,
      contribution: value,
      direction: value > 0 ? 'pushing' : value < 0 ? 'pulling' : 'neutral',
      percentage: Math.abs(value) / Math.max(...feature_importance.map(f => Math.abs(f[1]))) * 100
    };
  });

  const getContributionColor = (direction: string) => {
    switch (direction) {
      case 'pushing': return 'text-red-600 bg-red-50 border-red-200';
      case 'pulling': return 'text-green-600 bg-green-50 border-green-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getContributionIcon = (direction: string) => {
    switch (direction) {
      case 'pushing': return <ArrowUpIcon className="h-4 w-4" />;
      case 'pulling': return <ArrowDownIcon className="h-4 w-4" />;
      default: return <MinusIcon className="h-4 w-4" />;
    }
  };

  const getFeatureDisplayName = (feature: string) => {
    if (feature.startsWith('kmer_')) {
      return `k-mer: ${feature.substring(5)}`;
    } else if (feature.startsWith('token_')) {
      const parts = feature.split('_');
      return `Token ${parts[1]}: ${parts.slice(2).join('_')}`;
    }
    return feature;
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex justify-between items-center">
          <div>
            <CardTitle className="flex items-center gap-2">
              Force Plot Explanation
              <Badge variant="outline">{explanation.model_type}</Badge>
              <Badge variant="secondary">{explanation.antibiotic}</Badge>
            </CardTitle>
            <CardDescription>
              Visualizes how features push prediction from base value to final outcome
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => setShowDetails(!showDetails)}
            >
              {showDetails ? 'Hide' : 'Show'} Details
            </Button>
            <div className="flex items-center gap-1 border rounded">
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => setZoomLevel(Math.max(0.5, zoomLevel - 0.25))}
              >
                <ZoomOutIcon className="h-4 w-4" />
              </Button>
              <span className="px-2 text-sm font-mono">{zoomLevel.toFixed(1)}x</span>
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => setZoomLevel(Math.min(2, zoomLevel + 0.25))}
              >
                <ZoomInIcon className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-6" style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'top left' }}>
          {/* Base Value */}
          <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg border-2 border-blue-200">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-500 rounded-full"></div>
              <span className="font-semibold">Base Value</span>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-blue-600">{base_value.toFixed(3)}</div>
              <div className="text-sm text-gray-600">Starting point</div>
            </div>
          </div>

          {/* Contributions */}
          <div className="space-y-3">
            <h4 className="font-semibold text-lg">Feature Contributions</h4>
            {contributions.map((contrib, index) => (
              <div 
                key={index} 
                className={`p-4 rounded-lg border-2 transition-all duration-300 hover:shadow-md ${getContributionColor(contrib.direction)}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    {getContributionIcon(contrib.direction)}
                    <div className="min-w-0 flex-1">
                      <div className="font-medium truncate" title={contrib.feature}>
                        {getFeatureDisplayName(contrib.feature)}
                      </div>
                      {showDetails && (
                        <div className="text-sm text-gray-600">
                          Contribution: {contrib.contribution.toFixed(3)}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="text-right ml-4">
                    <div className="font-bold text-lg">
                      {contrib.contribution > 0 ? '+' : ''}{contrib.contribution.toFixed(3)}
                    </div>
                    {showDetails && (
                      <div className="text-sm text-gray-600">
                        {contrib.percentage.toFixed(1)}% impact
                      </div>
                    )}
                  </div>
                </div>

                {showDetails && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="flex justify-between text-sm">
                      <span>Cumulative:</span>
                      <span className="font-mono">{contrib.cumulative.toFixed(3)}</span>
                    </div>
                    <Progress 
                      value={Math.abs(contrib.percentage)} 
                      className="mt-2"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Final Prediction */}
          <div className="flex items-center justify-between p-4 bg-purple-50 rounded-lg border-2 border-purple-200">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-purple-500 rounded-full"></div>
              <span className="font-semibold">Final Prediction</span>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-purple-600">
                {explanation.prediction}
              </div>
              <div className="text-sm text-gray-600">
                {explanation.probability && `Confidence: ${(explanation.probability * 100).toFixed(1)}%`}
              </div>
            </div>
          </div>

          {/* Summary */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <h5 className="font-semibold mb-3">Force Plot Summary</h5>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Base Value:</span>
                <div className="font-mono font-semibold">{base_value.toFixed(3)}</div>
              </div>
              <div>
                <span className="text-gray-600">Total Change:</span>
                <div className="font-mono font-semibold">
                  {(contributions.reduce((sum, c) => sum + c.contribution, 0)).toFixed(3)}
                </div>
              </div>
              <div>
                <span className="text-gray-600">Features Used:</span>
                <div className="font-mono font-semibold">{contributions.length}</div>
              </div>
            </div>
            
            <div className="mt-4 space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-red-500 rounded"></div>
                <span className="text-sm">Features pushing towards resistance</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-green-500 rounded"></div>
                <span className="text-sm">Features pulling towards susceptibility</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                <span className="text-sm">Base value (model average)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
                <span className="text-sm">Final prediction outcome</span>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
