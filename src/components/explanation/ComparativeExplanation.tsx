import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { 
  BarChart3Icon, 
  TrendingUpIcon, 
  TrendingDownIcon,
  InfoIcon,
  DownloadIcon,
  EyeIcon,
  EyeOffIcon 
} from "lucide-react";

interface ComparativeExplanationProps {
  xgboostExplanation?: any;
  transformerExplanation?: any;
  antibiotic: string;
  isLoading?: boolean;
}

export function ComparativeExplanation({ 
  xgboostExplanation, 
  transformerExplanation, 
  antibiotic,
  isLoading = false 
}: ComparativeExplanationProps) {
  const [activeView, setActiveView] = useState("comparison");
  const [showDetails, setShowDetails] = useState(true);

  if (!xgboostExplanation && !transformerExplanation) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-gray-500">
            <InfoIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No comparative data available</p>
            <p className="text-sm mt-2">Generate explanations for both models to compare</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const getModelComparison = () => {
    if (!xgboostExplanation || !transformerExplanation) return null;

    const xgbFeatures = xgboostExplanation.feature_names || [];
    const transformerFeatures = transformerExplanation.feature_names || [];
    
    const xgbShapValues = Array.isArray(xgboostExplanation.shap_values[0]) 
      ? xgboostExplanation.shap_values[0] 
      : xgboostExplanation.shap_values;
    const transformerShapValues = Array.isArray(transformerExplanation.shap_values[0])
      ? transformerExplanation.shap_values[0]
      : transformerExplanation.shap_values;

    const xgbTopFeatures = xgbFeatures.map((f, i) => ({
      feature: f,
      value: xgbShapValues[i],
      absValue: Math.abs(xgbShapValues[i])
    })).sort((a, b) => b.absValue - a.absValue).slice(0, 10);

    const transformerTopFeatures = transformerFeatures.map((f, i) => ({
      feature: f,
      value: transformerShapValues[i],
      absValue: Math.abs(transformerShapValues[i])
    })).sort((a, b) => b.absValue - a.absValue).slice(0, 10);

    return {
      xgb: xgbTopFeatures,
      transformer: transformerTopFeatures
    };
  };

  const getFeatureDisplayName = (feature: string, modelType: string) => {
    if (feature.startsWith('kmer_')) {
      return `k-mer: ${feature.substring(5)}`;
    } else if (feature.startsWith('token_')) {
      const parts = feature.split('_');
      return `Token ${parts[1]}: ${parts.slice(2).join('_')}`;
    }
    return feature;
  };

  const getAgreementLevel = () => {
    if (!xgboostExplanation || !transformerExplanation) return null;
    
    const xgbPred = xgboostExplanation.prediction;
    const transformerPred = transformerExplanation.prediction;
    
    if (xgbPred === transformerPred) {
      return {
        level: 'full',
        text: 'Full Agreement',
        color: 'bg-green-100 text-green-800 border-green-200'
      };
    } else {
      return {
        level: 'disagreement',
        text: 'Model Disagreement',
        color: 'bg-red-100 text-red-800 border-red-200'
      };
    }
  };

  const getPerformanceComparison = () => {
    if (!xgboostExplanation || !transformerExplanation) return null;

    const xgbConf = xgboostExplanation.probability || 0;
    const transformerConf = transformerExplanation.probability || 0;

    return {
      xgb: {
        confidence: xgbConf,
        confidencePercent: (xgbConf * 100).toFixed(1),
        prediction: xgboostExplanation.prediction
      },
      transformer: {
        confidence: transformerConf,
        confidencePercent: (transformerConf * 100).toFixed(1),
        prediction: transformerExplanation.prediction
      },
      difference: Math.abs(xgbConf - transformerConf),
      winner: xgbConf > transformerConf ? 'XGBoost' : 'DNABERT'
    };
  };

  const comparison = getModelComparison();
  const agreement = getAgreementLevel();
  const performance = getPerformanceComparison();

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex justify-between items-center">
          <div>
            <CardTitle className="flex items-center gap-2">
              Comparative Model Analysis
              <Badge variant="outline">{antibiotic}</Badge>
            </CardTitle>
            <CardDescription>
              Compare XGBoost vs DNABERT explanations side-by-side
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => setShowDetails(!showDetails)}
            >
              {showDetails ? <EyeOffIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs value={activeView} onValueChange={setActiveView} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="comparison">Side-by-Side</TabsTrigger>
            <TabsTrigger value="agreement">Agreement Analysis</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
          </TabsList>

          <TabsContent value="comparison" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* XGBoost Side */}
              {xgboostExplanation && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-blue-100 text-blue-800">XGBoost</Badge>
                    <span className="font-semibold">Feature Importance</span>
                  </div>
                  
                  <div className="space-y-3">
                    {comparison?.xgb.map((feature, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm truncate" title={feature.feature}>
                            {getFeatureDisplayName(feature.feature, 'xgboost')}
                          </div>
                          {showDetails && (
                            <div className="text-xs text-gray-600">
                              Value: {feature.value.toFixed(3)}
                            </div>
                          )}
                        </div>
                        <div className="ml-3 text-right">
                          <div className="font-bold text-blue-600">
                            {feature.absValue.toFixed(3)}
                          </div>
                          {showDetails && (
                            <div className="text-xs text-gray-600">
                              Impact: {feature.value > 0 ? '+' : ''}{feature.value.toFixed(2)}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* DNABERT Side */}
              {transformerExplanation && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-red-100 text-red-800">DNABERT</Badge>
                    <span className="font-semibold">Token Importance</span>
                  </div>
                  
                  <div className="space-y-3">
                    {comparison?.transformer.map((feature, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm truncate" title={feature.feature}>
                            {getFeatureDisplayName(feature.feature, 'transformer')}
                          </div>
                          {showDetails && (
                            <div className="text-xs text-gray-600">
                              Value: {feature.value.toFixed(3)}
                            </div>
                          )}
                        </div>
                        <div className="ml-3 text-right">
                          <div className="font-bold text-red-600">
                            {feature.absValue.toFixed(3)}
                          </div>
                          {showDetails && (
                            <div className="text-xs text-gray-600">
                              Impact: {feature.value > 0 ? '+' : ''}{feature.value.toFixed(2)}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {showDetails && (
              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <h5 className="font-semibold mb-3">Model Comparison Summary</h5>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">XGBoost Features:</span>
                    <div className="font-mono">{comparison?.xgb.length}</div>
                  </div>
                  <div>
                    <span className="text-gray-600">DNABERT Tokens:</span>
                    <div className="font-mono">{comparison?.transformer.length}</div>
                  </div>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="agreement" className="space-y-6">
            {agreement && (
              <div className="space-y-4">
                <div className={`p-4 rounded-lg border-2 ${agreement.color}`}>
                  <div className="flex items-center gap-3">
                    <div className={`w-4 h-4 rounded-full ${
                      agreement.level === 'full' ? 'bg-green-500' : 'bg-red-500'
                    }`}></div>
                    <div>
                      <h4 className="font-semibold text-lg">{agreement.text}</h4>
                      <p className="text-sm text-gray-600">
                        {agreement.level === 'full' 
                          ? 'Both models agree on the prediction'
                          : 'Models disagree - requires further investigation'
                        }
                      </p>
                    </div>
                  </div>
                </div>

                {performance && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                          XGBoost Prediction
                          <Badge variant="outline">Blue Model</Badge>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="flex justify-between items-center">
                          <span>Prediction:</span>
                          <Badge className={performance.xgb.prediction === 'R' ? 'bg-red-100 text-red-800' : 
                                        performance.xgb.prediction === 'I' ? 'bg-yellow-100 text-yellow-800' : 
                                        'bg-green-100 text-green-800'}>
                            {performance.xgb.prediction}
                          </Badge>
                        </div>
                        <div className="flex justify-between items-center">
                          <span>Confidence:</span>
                          <div className="flex items-center gap-2">
                            <Progress value={performance.xgb.confidence * 100} className="w-20" />
                            <span className="font-mono text-sm">{performance.xgb.confidencePercent}%</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                          DNABERT Prediction
                          <Badge variant="outline">Red Model</Badge>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="flex justify-between items-center">
                          <span>Prediction:</span>
                          <Badge className={performance.transformer.prediction === 'R' ? 'bg-red-100 text-red-800' : 
                                        performance.transformer.prediction === 'I' ? 'bg-yellow-100 text-yellow-800' : 
                                        'bg-green-100 text-green-800'}>
                            {performance.transformer.prediction}
                          </Badge>
                        </div>
                        <div className="flex justify-between items-center">
                          <span>Confidence:</span>
                          <div className="flex items-center gap-2">
                            <Progress value={performance.transformer.confidence * 100} className="w-20" />
                            <span className="font-mono text-sm">{performance.transformer.confidencePercent}%</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}

                {performance && (
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <h5 className="font-semibold mb-3">Performance Analysis</h5>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>Confidence Difference:</span>
                        <span className="font-mono">{(performance.difference * 100).toFixed(1)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Higher Confidence:</span>
                        <Badge variant="outline">{performance.winner}</Badge>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </TabsContent>

          <TabsContent value="performance" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* XGBoost Performance */}
              {xgboostExplanation && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      XGBoost Metrics
                      <BarChart3Icon className="h-5 w-5" />
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span>Prediction:</span>
                        <Badge>{xgboostExplanation.prediction}</Badge>
                      </div>
                      {xgboostExplanation.probability && (
                        <div className="flex justify-between">
                          <span>Confidence:</span>
                          <div className="flex items-center gap-2">
                            <Progress value={xgboostExplanation.probability * 100} />
                            <span className="font-mono text-sm">
                              {(xgboostExplanation.probability * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span>Features:</span>
                        <span className="font-mono text-sm">
                          {xgboostExplanation.feature_names?.length || 0}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>SHAP Values:</span>
                        <span className="font-mono text-sm">
                          {Array.isArray(xgboostExplanation.shap_values[0]) 
                            ? xgboostExplanation.shap_values[0].length 
                            : xgboostExplanation.shap_values.length}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* DNABERT Performance */}
              {transformerExplanation && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      DNABERT Metrics
                      <BarChart3Icon className="h-5 w-5" />
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span>Prediction:</span>
                        <Badge>{transformerExplanation.prediction}</Badge>
                      </div>
                      {transformerExplanation.probability && (
                        <div className="flex justify-between">
                          <span>Confidence:</span>
                          <div className="flex items-center gap-2">
                            <Progress value={transformerExplanation.probability * 100} />
                            <span className="font-mono text-sm">
                              {(transformerExplanation.probability * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span>Tokens:</span>
                        <span className="font-mono text-sm">
                          {transformerExplanation.feature_names?.length || 0}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>SHAP Values:</span>
                        <span className="font-mono text-sm">
                          {Array.isArray(transformerExplanation.shap_values[0]) 
                            ? transformerExplanation.shap_values[0].length 
                            : transformerExplanation.shap_values.length}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>

            {showDetails && xgboostExplanation?.metadata && transformerExplanation?.metadata && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <h5 className="font-semibold mb-3">Technical Comparison</h5>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
                  <div>
                    <h6 className="font-medium mb-2">XGBoost Details</h6>
                    <div className="space-y-1">
                      {Object.entries(xgboostExplanation.metadata).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span className="capitalize">{key.replace(/_/g, ' ')}:</span>
                          <span className="font-mono text-xs">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h6 className="font-medium mb-2">DNABERT Details</h6>
                    <div className="space-y-1">
                      {Object.entries(transformerExplanation.metadata).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span className="capitalize">{key.replace(/_/g, ' ')}:</span>
                          <span className="font-mono text-xs">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
