import React from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Brain, Cpu, BarChart2, Download, Clock, HardDrive, Zap } from "lucide-react";

interface ModelComparisonProps {
  xgboostMetrics?: {
    accuracy: number;
    f1Score: number;
    jaccardScore: number;
    trainTime: number;
    modelSize: number;
    inferenceTime: number;
  };
  transformerMetrics?: {
    accuracy: number;
    f1Score: number;
    jaccardScore: number;
    trainTime: number;
    modelSize: number;
    inferenceTime: number;
  };
}

const ModelComparison: React.FC<ModelComparisonProps> = ({
  xgboostMetrics = {
    accuracy: 0.92,
    f1Score: 0.89,
    jaccardScore: 0.85,
    trainTime: 45.2,
    modelSize: 2.4,
    inferenceTime: 0.05
  },
  transformerMetrics = {
    accuracy: 0.94,
    f1Score: 0.91,
    jaccardScore: 0.88,
    trainTime: 128.7,
    modelSize: 8.7,
    inferenceTime: 0.12
  }
}) => {
  const [activeTab, setActiveTab] = React.useState("performance");
  
  // Calculate which model is better for each metric
  const betterAccuracy = transformerMetrics.accuracy > xgboostMetrics.accuracy ? "transformer" : "xgboost";
  const betterF1 = transformerMetrics.f1Score > xgboostMetrics.f1Score ? "transformer" : "xgboost";
  const betterJaccard = transformerMetrics.jaccardScore > xgboostMetrics.jaccardScore ? "transformer" : "xgboost";
  const fasterTraining = transformerMetrics.trainTime < xgboostMetrics.trainTime ? "transformer" : "xgboost";
  const smallerModel = transformerMetrics.modelSize < xgboostMetrics.modelSize ? "transformer" : "xgboost";
  const fasterInference = transformerMetrics.inferenceTime < xgboostMetrics.inferenceTime ? "transformer" : "xgboost";
  
  // Calculate percentage differences
  const accuracyDiff = Math.abs(transformerMetrics.accuracy - xgboostMetrics.accuracy) / 
    Math.min(transformerMetrics.accuracy, xgboostMetrics.accuracy) * 100;
  
  const f1Diff = Math.abs(transformerMetrics.f1Score - xgboostMetrics.f1Score) / 
    Math.min(transformerMetrics.f1Score, xgboostMetrics.f1Score) * 100;
  
  const jaccardDiff = Math.abs(transformerMetrics.jaccardScore - xgboostMetrics.jaccardScore) / 
    Math.min(transformerMetrics.jaccardScore, xgboostMetrics.jaccardScore) * 100;
  
  const trainTimeDiff = Math.abs(transformerMetrics.trainTime - xgboostMetrics.trainTime) / 
    Math.min(transformerMetrics.trainTime, xgboostMetrics.trainTime) * 100;
  
  const modelSizeDiff = Math.abs(transformerMetrics.modelSize - xgboostMetrics.modelSize) / 
    Math.min(transformerMetrics.modelSize, xgboostMetrics.modelSize) * 100;
  
  const inferenceTimeDiff = Math.abs(transformerMetrics.inferenceTime - xgboostMetrics.inferenceTime) / 
    Math.min(transformerMetrics.inferenceTime, xgboostMetrics.inferenceTime) * 100;
  
  return (
    <Card className="w-full max-w-4xl mx-auto bg-white shadow-lg">
      <CardHeader className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
        <CardTitle className="text-2xl flex items-center">
          <BarChart2 className="mr-2 h-6 w-6" />
          Model Comparison: XGBoost vs Transformer
        </CardTitle>
        <CardDescription className="text-blue-100">
          Comparing performance metrics between gradient boosting and deep learning approaches
        </CardDescription>
      </CardHeader>
      
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid grid-cols-3 w-full">
          <TabsTrigger value="performance">
            <BarChart2 className="mr-2 h-4 w-4" />
            Performance
          </TabsTrigger>
          <TabsTrigger value="efficiency">
            <Zap className="mr-2 h-4 w-4" />
            Efficiency
          </TabsTrigger>
          <TabsTrigger value="tradeoffs">
            <HardDrive className="mr-2 h-4 w-4" />
            Tradeoffs
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="performance" className="p-6">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium mb-4">Prediction Performance</h3>
              <p className="text-sm text-gray-600 mb-6">
                Comparing the predictive performance metrics between XGBoost and Transformer models
                for antibiotic resistance prediction.
              </p>
              
              <div className="space-y-6">
                {/* Accuracy Comparison */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <div className="text-sm font-medium">Accuracy</div>
                    <div className="flex items-center">
                      <Badge className={`${betterAccuracy === 'transformer' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'}`}>
                        {betterAccuracy === 'transformer' ? 'Transformer Better' : 'XGBoost Better'} (+{accuracyDiff.toFixed(1)}%)
                      </Badge>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-4">
                    <div className="w-1/2">
                      <div className="flex justify-between text-xs mb-1">
                        <span>XGBoost</span>
                        <span>{(xgboostMetrics.accuracy * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div 
                          className="bg-blue-600 h-2.5 rounded-full" 
                          style={{ width: `${xgboostMetrics.accuracy * 100}%` }}
                        ></div>
                      </div>
                    </div>
                    
                    <div className="w-1/2">
                      <div className="flex justify-between text-xs mb-1">
                        <span>Transformer</span>
                        <span>{(transformerMetrics.accuracy * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div 
                          className="bg-purple-600 h-2.5 rounded-full" 
                          style={{ width: `${transformerMetrics.accuracy * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* F1 Score Comparison */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <div className="text-sm font-medium">F1 Score</div>
                    <div className="flex items-center">
                      <Badge className={`${betterF1 === 'transformer' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'}`}>
                        {betterF1 === 'transformer' ? 'Transformer Better' : 'XGBoost Better'} (+{f1Diff.toFixed(1)}%)
                      </Badge>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-4">
                    <div className="w-1/2">
                      <div className="flex justify-between text-xs mb-1">
                        <span>XGBoost</span>
                        <span>{(xgboostMetrics.f1Score * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div 
                          className="bg-blue-600 h-2.5 rounded-full" 
                          style={{ width: `${xgboostMetrics.f1Score * 100}%` }}
                        ></div>
                      </div>
                    </div>
                    
                    <div className="w-1/2">
                      <div className="flex justify-between text-xs mb-1">
                        <span>Transformer</span>
                        <span>{(transformerMetrics.f1Score * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div 
                          className="bg-purple-600 h-2.5 rounded-full" 
                          style={{ width: `${transformerMetrics.f1Score * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Jaccard Score Comparison */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <div className="text-sm font-medium">Jaccard Score</div>
                    <div className="flex items-center">
                      <Badge className={`${betterJaccard === 'transformer' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'}`}>
                        {betterJaccard === 'transformer' ? 'Transformer Better' : 'XGBoost Better'} (+{jaccardDiff.toFixed(1)}%)
                      </Badge>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-4">
                    <div className="w-1/2">
                      <div className="flex justify-between text-xs mb-1">
                        <span>XGBoost</span>
                        <span>{(xgboostMetrics.jaccardScore * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div 
                          className="bg-blue-600 h-2.5 rounded-full" 
                          style={{ width: `${xgboostMetrics.jaccardScore * 100}%` }}
                        ></div>
                      </div>
                    </div>
                    
                    <div className="w-1/2">
                      <div className="flex justify-between text-xs mb-1">
                        <span>Transformer</span>
                        <span>{(transformerMetrics.jaccardScore * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div 
                          className="bg-purple-600 h-2.5 rounded-full" 
                          style={{ width: `${transformerMetrics.jaccardScore * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <Separator />
            
            <div className="flex justify-between">
              <div className="flex items-center">
                <Cpu className="h-5 w-5 text-blue-600 mr-2" />
                <span className="font-medium text-blue-800">XGBoost</span>
              </div>
              <div className="text-sm text-gray-600">
                Gradient boosting model with tree-based learning
              </div>
            </div>
            
            <div className="flex justify-between">
              <div className="flex items-center">
                <Brain className="h-5 w-5 text-purple-600 mr-2" />
                <span className="font-medium text-purple-800">Transformer</span>
              </div>
              <div className="text-sm text-gray-600">
                Deep learning model with attention mechanism
              </div>
            </div>
          </div>
        </TabsContent>
        
        <TabsContent value="efficiency" className="p-6">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium mb-4">Computational Efficiency</h3>
              <p className="text-sm text-gray-600 mb-6">
                Comparing the computational efficiency metrics between XGBoost and Transformer models
                including training time, model size, and inference speed.
              </p>
              
              <div className="space-y-6">
                {/* Training Time Comparison */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <div className="text-sm font-medium">Training Time (seconds)</div>
                    <div className="flex items-center">
                      <Badge className={`${fasterTraining === 'transformer' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'}`}>
                        {fasterTraining === 'transformer' ? 'Transformer Faster' : 'XGBoost Faster'} (-{trainTimeDiff.toFixed(1)}%)
                      </Badge>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-4">
                    <div className="w-1/2">
                      <div className="flex justify-between text-xs mb-1">
                        <span>XGBoost</span>
                        <span>{xgboostMetrics.trainTime.toFixed(1)}s</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div 
                          className="bg-blue-600 h-2.5 rounded-full" 
                          style={{ width: `${(xgboostMetrics.trainTime / Math.max(xgboostMetrics.trainTime, transformerMetrics.trainTime)) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                    
                    <div className="w-1/2">
                      <div className="flex justify-between text-xs mb-1">
                        <span>Transformer</span>
                        <span>{transformerMetrics.trainTime.toFixed(1)}s</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div 
                          className="bg-purple-600 h-2.5 rounded-full" 
                          style={{ width: `${(transformerMetrics.trainTime / Math.max(xgboostMetrics.trainTime, transformerMetrics.trainTime)) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Model Size Comparison */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <div className="text-sm font-medium">Model Size (MB)</div>
                    <div className="flex items-center">
                      <Badge className={`${smallerModel === 'transformer' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'}`}>
                        {smallerModel === 'transformer' ? 'Transformer Smaller' : 'XGBoost Smaller'} (-{modelSizeDiff.toFixed(1)}%)
                      </Badge>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-4">
                    <div className="w-1/2">
                      <div className="flex justify-between text-xs mb-1">
                        <span>XGBoost</span>
                        <span>{xgboostMetrics.modelSize.toFixed(1)} MB</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div 
                          className="bg-blue-600 h-2.5 rounded-full" 
                          style={{ width: `${(xgboostMetrics.modelSize / Math.max(xgboostMetrics.modelSize, transformerMetrics.modelSize)) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                    
                    <div className="w-1/2">
                      <div className="flex justify-between text-xs mb-1">
                        <span>Transformer</span>
                        <span>{transformerMetrics.modelSize.toFixed(1)} MB</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div 
                          className="bg-purple-600 h-2.5 rounded-full" 
                          style={{ width: `${(transformerMetrics.modelSize / Math.max(xgboostMetrics.modelSize, transformerMetrics.modelSize)) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Inference Time Comparison */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <div className="text-sm font-medium">Inference Time (seconds)</div>
                    <div className="flex items-center">
                      <Badge className={`${fasterInference === 'transformer' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'}`}>
                        {fasterInference === 'transformer' ? 'Transformer Faster' : 'XGBoost Faster'} (-{inferenceTimeDiff.toFixed(1)}%)
                      </Badge>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-4">
                    <div className="w-1/2">
                      <div className="flex justify-between text-xs mb-1">
                        <span>XGBoost</span>
                        <span>{xgboostMetrics.inferenceTime.toFixed(3)}s</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div 
                          className="bg-blue-600 h-2.5 rounded-full" 
                          style={{ width: `${(xgboostMetrics.inferenceTime / Math.max(xgboostMetrics.inferenceTime, transformerMetrics.inferenceTime)) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                    
                    <div className="w-1/2">
                      <div className="flex justify-between text-xs mb-1">
                        <span>Transformer</span>
                        <span>{transformerMetrics.inferenceTime.toFixed(3)}s</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div 
                          className="bg-purple-600 h-2.5 rounded-full" 
                          style={{ width: `${(transformerMetrics.inferenceTime / Math.max(xgboostMetrics.inferenceTime, transformerMetrics.inferenceTime)) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <Separator />
            
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                <div className="flex items-center mb-2">
                  <Clock className="h-4 w-4 text-blue-600 mr-2" />
                  <h4 className="text-sm font-medium text-blue-800">XGBoost Efficiency</h4>
                </div>
                <p className="text-xs text-blue-700">
                  XGBoost is more efficient in terms of training time and model size,
                  making it suitable for environments with limited computational resources.
                </p>
              </div>
              
              <div className="bg-purple-50 p-4 rounded-lg border border-purple-100">
                <div className="flex items-center mb-2">
                  <Brain className="h-4 w-4 text-purple-600 mr-2" />
                  <h4 className="text-sm font-medium text-purple-800">Transformer Complexity</h4>
                </div>
                <p className="text-xs text-purple-700">
                  Transformer models require more computational resources but can capture
                  complex patterns in the data that simpler models might miss.
                </p>
              </div>
            </div>
          </div>
        </TabsContent>
        
        <TabsContent value="tradeoffs" className="p-6">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium mb-4">Model Tradeoffs</h3>
              <p className="text-sm text-gray-600 mb-6">
                Understanding the tradeoffs between XGBoost and Transformer models for antibiotic resistance prediction.
              </p>
              
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left border-collapse">
                  <thead>
                    <tr className="bg-gray-100">
                      <th className="p-3 border">Aspect</th>
                      <th className="p-3 border">
                        <div className="flex items-center">
                          <Cpu className="h-4 w-4 text-blue-600 mr-2" />
                          XGBoost
                        </div>
                      </th>
                      <th className="p-3 border">
                        <div className="flex items-center">
                          <Brain className="h-4 w-4 text-purple-600 mr-2" />
                          Transformer
                        </div>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="p-3 border font-medium">Accuracy</td>
                      <td className="p-3 border">
                        <div className="flex items-center">
                          <span className="mr-2">{(xgboostMetrics.accuracy * 100).toFixed(1)}%</span>
                          {betterAccuracy === 'xgboost' && (
                            <Badge className="bg-green-100 text-green-800">Better</Badge>
                          )}
                        </div>
                      </td>
                      <td className="p-3 border">
                        <div className="flex items-center">
                          <span className="mr-2">{(transformerMetrics.accuracy * 100).toFixed(1)}%</span>
                          {betterAccuracy === 'transformer' && (
                            <Badge className="bg-green-100 text-green-800">Better</Badge>
                          )}
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td className="p-3 border font-medium">Training Speed</td>
                      <td className="p-3 border">
                        <div className="flex items-center">
                          <span className="mr-2">{xgboostMetrics.trainTime.toFixed(1)}s</span>
                          {fasterTraining === 'xgboost' && (
                            <Badge className="bg-green-100 text-green-800">Faster</Badge>
                          )}
                        </div>
                      </td>
                      <td className="p-3 border">
                        <div className="flex items-center">
                          <span className="mr-2">{transformerMetrics.trainTime.toFixed(1)}s</span>
                          {fasterTraining === 'transformer' && (
                            <Badge className="bg-green-100 text-green-800">Faster</Badge>
                          )}
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td className="p-3 border font-medium">Model Size</td>
                      <td className="p-3 border">
                        <div className="flex items-center">
                          <span className="mr-2">{xgboostMetrics.modelSize.toFixed(1)} MB</span>
                          {smallerModel === 'xgboost' && (
                            <Badge className="bg-green-100 text-green-800">Smaller</Badge>
                          )}
                        </div>
                      </td>
                      <td className="p-3 border">
                        <div className="flex items-center">
                          <span className="mr-2">{transformerMetrics.modelSize.toFixed(1)} MB</span>
                          {smallerModel === 'transformer' && (
                            <Badge className="bg-green-100 text-green-800">Smaller</Badge>
                          )}
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td className="p-3 border font-medium">Inference Speed</td>
                      <td className="p-3 border">
                        <div className="flex items-center">
                          <span className="mr-2">{xgboostMetrics.inferenceTime.toFixed(3)}s</span>
                          {fasterInference === 'xgboost' && (
                            <Badge className="bg-green-100 text-green-800">Faster</Badge>
                          )}
                        </div>
                      </td>
                      <td className="p-3 border">
                        <div className="flex items-center">
                          <span className="mr-2">{transformerMetrics.inferenceTime.toFixed(3)}s</span>
                          {fasterInference === 'transformer' && (
                            <Badge className="bg-green-100 text-green-800">Faster</Badge>
                          )}
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td className="p-3 border font-medium">Interpretability</td>
                      <td className="p-3 border">
                        <div className="flex items-center">
                          <span className="mr-2">High</span>
                          <Badge className="bg-green-100 text-green-800">Better</Badge>
                        </div>
                      </td>
                      <td className="p-3 border">
                        <span>Medium</span>
                      </td>
                    </tr>
                    <tr>
                      <td className="p-3 border font-medium">Complex Pattern Recognition</td>
                      <td className="p-3 border">
                        <span>Medium</span>
                      </td>
                      <td className="p-3 border">
                        <div className="flex items-center">
                          <span className="mr-2">High</span>
                          <Badge className="bg-green-100 text-green-800">Better</Badge>
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td className="p-3 border font-medium">Resource Requirements</td>
                      <td className="p-3 border">
                        <div className="flex items-center">
                          <span className="mr-2">Low</span>
                          <Badge className="bg-green-100 text-green-800">Better</Badge>
                        </div>
                      </td>
                      <td className="p-3 border">
                        <span>High</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            
            <Separator />
            
            <div>
              <h3 className="text-lg font-medium mb-4">Recommendations</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardHeader className="bg-blue-50 pb-2">
                    <CardTitle className="text-base flex items-center">
                      <Cpu className="mr-2 h-4 w-4 text-blue-600" />
                      When to Choose XGBoost
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-4">
                    <ul className="space-y-2 text-sm">
                      <li className="flex items-start">
                        <div className="rounded-full bg-blue-100 p-1 mr-2 mt-0.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
                        </div>
                        <span>Limited computational resources</span>
                      </li>
                      <li className="flex items-start">
                        <div className="rounded-full bg-blue-100 p-1 mr-2 mt-0.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
                        </div>
                        <span>Need for model interpretability</span>
                      </li>
                      <li className="flex items-start">
                        <div className="rounded-full bg-blue-100 p-1 mr-2 mt-0.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
                        </div>
                        <span>Faster training and deployment required</span>
                      </li>
                      <li className="flex items-start">
                        <div className="rounded-full bg-blue-100 p-1 mr-2 mt-0.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
                        </div>
                        <span>Smaller dataset size</span>
                      </li>
                    </ul>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader className="bg-purple-50 pb-2">
                    <CardTitle className="text-base flex items-center">
                      <Brain className="mr-2 h-4 w-4 text-purple-600" />
                      When to Choose Transformer
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-4">
                    <ul className="space-y-2 text-sm">
                      <li className="flex items-start">
                        <div className="rounded-full bg-purple-100 p-1 mr-2 mt-0.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-purple-600"></div>
                        </div>
                        <span>Maximum prediction accuracy needed</span>
                      </li>
                      <li className="flex items-start">
                        <div className="rounded-full bg-purple-100 p-1 mr-2 mt-0.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-purple-600"></div>
                        </div>
                        <span>Complex genomic patterns to capture</span>
                      </li>
                      <li className="flex items-start">
                        <div className="rounded-full bg-purple-100 p-1 mr-2 mt-0.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-purple-600"></div>
                        </div>
                        <span>Large dataset available</span>
                      </li>
                      <li className="flex items-start">
                        <div className="rounded-full bg-purple-100 p-1 mr-2 mt-0.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-purple-600"></div>
                        </div>
                        <span>GPU resources available for training</span>
                      </li>
                    </ul>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
      
      <CardFooter className="bg-gray-50 border-t p-4">
        <div className="flex justify-between items-center w-full">
          <p className="text-xs text-gray-500">
            Both models have their strengths and weaknesses. The best choice depends on your specific requirements and constraints.
          </p>
          <Button variant="outline" className="flex items-center">
            <Download className="mr-2 h-4 w-4" />
            Export Comparison
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
};

export default ModelComparison;