import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { InfoIcon, DownloadIcon, RefreshCwIcon, TrendingUpIcon, TrendingDownIcon } from "lucide-react";

interface ShapVisualizationProps {
  explanation: {
    shap_values: number[] | number[][];
    feature_names: string[];
    class_names?: string[];
    base_values: number | number[];
    prediction: string;
    probability?: number;
    model_type: string;
    antibiotic: string;
    force_plot_data?: any;
    waterfall_plot_data?: any;
    metadata?: any;
  };
  isLoading?: boolean;
  onRefresh?: () => void;
}

export function ShapVisualization({ explanation, isLoading = false, onRefresh }: ShapVisualizationProps) {
  const [activeTab, setActiveTab] = useState("importance");
  const [topFeatures, setTopFeatures] = useState(15);

  if (!explanation || !explanation.shap_values || !explanation.feature_names) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-gray-500">
            <InfoIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No SHAP data available</p>
            <p className="text-sm mt-2">Generate model explanations to see feature importance</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Prepare data for visualization
  const features = explanation.feature_names;
  let shapValues: number[];
  let baseValue: number;
  
  if (explanation.shap_values) {
    if (Array.isArray(explanation.shap_values[0])) {
      // Multi-class case: shap_values[0] is an array
      shapValues = explanation.shap_values[0];
    } else {
      // Single class case: shap_values is a number array
      shapValues = explanation.shap_values as number[];
    }
  } else {
    shapValues = [];
  }
  
  if (explanation.base_values) {
    if (Array.isArray(explanation.base_values)) {
      baseValue = explanation.base_values[0];
    } else {
      baseValue = explanation.base_values as number;
    }
  } else {
    baseValue = 0;
  }
  
  const data = features.map((f, i) => ({
    feature: f,
    value: shapValues[i],
    absValue: Math.abs(shapValues[i]),
    sign: shapValues[i] > 0 ? 'positive' : 'negative'
  }))
  .sort((a, b) => b.absValue - a.absValue)
  .slice(0, topFeatures);

  const maxValue = Math.max(...data.map(d => Math.abs(d.value)));

  const getFeatureDisplayName = (feature: string) => {
    // Clean up feature names for display
    if (feature.startsWith('kmer_')) {
      return `k-mer: ${feature.substring(5)}`;
    } else if (feature.startsWith('token_')) {
      const parts = feature.split('_');
      return `Token ${parts[1]}: ${parts.slice(2).join('_')}`;
    }
    return feature;
  };

  const getFeatureColor = (sign: string) => {
    return sign === 'positive' ? 'bg-red-500' : 'bg-green-500';
  };

  const getFeatureTextColor = (sign: string) => {
    return sign === 'positive' ? 'text-red-600' : 'text-green-600';
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex justify-between items-center">
          <div>
            <CardTitle className="flex items-center gap-2">
              Model Explainability
              <Badge variant="outline">{explanation.model_type}</Badge>
              <Badge variant="secondary">{explanation.antibiotic}</Badge>
            </CardTitle>
            <CardDescription>
              SHAP values show how each feature contributes to the prediction
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onRefresh} disabled={isLoading}>
              <RefreshCwIcon className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="importance">Feature Importance</TabsTrigger>
            <TabsTrigger value="waterfall">Waterfall Plot</TabsTrigger>
            <TabsTrigger value="details">Details</TabsTrigger>
          </TabsList>

          <TabsContent value="importance" className="space-y-4">
            <div className="flex justify-between items-center">
              <h4 className="text-lg font-semibold">Top {topFeatures} Feature Contributions</h4>
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium">Features:</label>
                <select 
                  value={topFeatures} 
                  onChange={(e) => setTopFeatures(Number(e.target.value))}
                  className="border rounded px-2 py-1 text-sm"
                >
                  <option value={10}>Top 10</option>
                  <option value={15}>Top 15</option>
                  <option value={20}>Top 20</option>
                  <option value={50}>Top 50</option>
                </select>
              </div>
            </div>

            <div className="space-y-3">
              {data.map((item, index) => (
                <div key={index} className="flex items-center space-x-3">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="text-sm font-medium truncate" title={item.feature}>
                      {getFeatureDisplayName(item.feature)}
                    </span>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger>
                          <InfoIcon className="h-3 w-3 text-gray-400 flex-shrink-0" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-xs">{item.feature}</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                  
                  <div className="flex-1 bg-gray-200 rounded-full h-6 relative overflow-hidden min-w-0">
                    <div
                      className={`h-full transition-all duration-300 ${getFeatureColor(item.sign)}`}
                      style={{
                        width: `${(Math.abs(item.value) / maxValue) * 100}%`,
                        marginLeft: item.sign === 'negative' ? 'auto' : '0',
                        marginRight: item.sign === 'positive' ? 'auto' : '0'
                      }}
                    />
                  </div>
                  
                  <div className="flex items-center gap-1 min-w-0">
                    {item.sign === 'positive' ? (
                      <TrendingUpIcon className="h-3 w-3 text-red-500 flex-shrink-0" />
                    ) : (
                      <TrendingDownIcon className="h-3 w-3 text-green-500 flex-shrink-0" />
                    )}
                    <span className={`text-sm font-mono text-right ${getFeatureTextColor(item.sign)}`}>
                      {item.sign === 'positive' ? '+' : ''}{item.value.toFixed(3)}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
              <h5 className="font-semibold mb-2">Understanding SHAP Values</h5>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-red-500 rounded"></div>
                  <span>Features that <strong>increase</strong> resistance probability</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-green-500 rounded"></div>
                  <span>Features that <strong>decrease</strong> resistance probability</span>
                </div>
              </div>
              <p className="text-xs text-gray-600 mt-2">
                Base value: {explanation.base_values?.toFixed(3)} | 
                Prediction: {explanation.prediction} 
                {explanation.probability && ` (${(explanation.probability * 100).toFixed(1)}%)`}
              </p>
            </div>
          </TabsContent>

          <TabsContent value="waterfall" className="space-y-4">
            {explanation.waterfall_plot_data ? (
              <div>
                <h4 className="text-lg font-semibold mb-4">Waterfall Plot</h4>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Base Value:</span>
                      <span className="font-mono">{explanation.waterfall_plot_data.base_value.toFixed(3)}</span>
                    </div>
                    <div className="flex justify-between text-sm font-semibold">
                      <span>Final Prediction:</span>
                      <span className="font-mono">{explanation.waterfall_plot_data.final_prediction.toFixed(3)}</span>
                    </div>
                  </div>
                  
                  <div className="mt-4 space-y-2">
                    {explanation.waterfall_plot_data.features?.slice(0, 10).map((feature: any, index: number) => (
                      <div key={index} className="flex items-center justify-between text-sm">
                        <span className="truncate mr-2">{getFeatureDisplayName(feature.feature)}</span>
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded ${getFeatureColor(feature.contribution_type)}`}></div>
                          <span className={`font-mono ${getFeatureTextColor(feature.contribution_type)}`}>
                            {feature.contribution_type === 'positive' ? '+' : ''}{feature.shap_value.toFixed(3)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                <p>Waterfall plot data not available</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="details" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Model Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Model Type:</span>
                    <Badge>{explanation.model_type}</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span>Antibiotic:</span>
                    <Badge variant="secondary">{explanation.antibiotic}</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span>Prediction:</span>
                    <span className="font-semibold">{explanation.prediction}</span>
                  </div>
                  {explanation.probability && (
                    <div className="flex justify-between">
                      <span>Confidence:</span>
                      <div className="flex items-center gap-2">
                        <Progress value={explanation.probability * 100} className="w-20" />
                        <span className="font-mono">{(explanation.probability * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Feature Statistics</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Total Features:</span>
                    <span className="font-mono">{explanation.feature_names.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>SHAP Values:</span>
                    <span className="font-mono">{shapValues.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Max Impact:</span>
                    <span className="font-mono">{maxValue.toFixed(3)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Base Value:</span>
                    <span className="font-mono">{explanation.base_values?.toFixed(3)}</span>
                  </div>
                </CardContent>
              </Card>
            </div>

            {explanation.metadata && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Technical Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    {Object.entries(explanation.metadata).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span className="capitalize">{key.replace(/_/g, ' ')}:</span>
                        <span className="font-mono text-xs">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
