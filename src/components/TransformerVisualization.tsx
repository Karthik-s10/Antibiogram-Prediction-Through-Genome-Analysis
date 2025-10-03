import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Brain, Download, Info, Layers } from "lucide-react";

interface TransformerVisualizationProps {
  modelName?: string;
  accuracy?: number;
  f1Score?: number;
  jaccardScore?: number;
  attentionWeights?: number[][];
  confusionMatrix?: number[][];
}

const TransformerVisualization: React.FC<TransformerVisualizationProps> = ({
  modelName = "Transformer Antibiogram Predictor",
  accuracy = 0.94,
  f1Score = 0.91,
  jaccardScore = 0.88,
  attentionWeights = [
    [0.8, 0.05, 0.05, 0.05, 0.05],
    [0.1, 0.7, 0.1, 0.05, 0.05],
    [0.05, 0.1, 0.75, 0.05, 0.05],
    [0.05, 0.05, 0.1, 0.7, 0.1],
    [0.05, 0.05, 0.05, 0.05, 0.8]
  ],
  confusionMatrix = [
    [47, 2, 1],
    [3, 39, 3],
    [1, 1, 43]
  ]
}) => {
  const [activeTab, setActiveTab] = useState("attention");
  const [selectedLayer, setSelectedLayer] = useState(0);
  const [selectedHead, setSelectedHead] = useState(0);
  
  // Calculate total samples and accuracy from confusion matrix
  const totalSamples = confusionMatrix.reduce((sum, row) => 
    sum + row.reduce((rowSum, cell) => rowSum + cell, 0), 0);
  
  const correctPredictions = confusionMatrix.reduce((sum, row, i) => 
    sum + row[i], 0);
  
  const matrixAccuracy = correctPredictions / totalSamples;
  
  // Class labels
  const classLabels = ["Susceptible (S)", "Intermediate (I)", "Resistant (R)"];
  
  // Mock sequence tokens for attention visualization
  const sequenceTokens = ["ACGTA", "TCGAT", "GCTAT", "ATGCA", "CGATA"];
  
  // Generate layer and head options
  const layers = [0, 1, 2, 3];
  const heads = [0, 1, 2, 3, 4, 5, 6, 7];
  
  return (
    <Card className="w-full max-w-4xl mx-auto bg-white shadow-lg">
      <CardHeader className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white">
        <div className="flex justify-between items-center">
          <div>
            <CardTitle className="text-2xl flex items-center">
              <Brain className="mr-2 h-6 w-6" />
              {modelName}
            </CardTitle>
            <CardDescription className="text-purple-100">
              Deep Learning Transformer Model for Antibiotic Resistance Prediction
            </CardDescription>
          </div>
          <Badge className="bg-white text-purple-700 text-sm px-3 py-1">
            {(accuracy * 100).toFixed(1)}% Accuracy
          </Badge>
        </div>
      </CardHeader>
      
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid grid-cols-2 w-full">
          <TabsTrigger value="attention">
            <Brain className="mr-2 h-4 w-4" />
            Attention Visualization
          </TabsTrigger>
          <TabsTrigger value="performance">
            <Info className="mr-2 h-4 w-4" />
            Model Performance
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="attention" className="p-6">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium mb-4">Attention Mechanism Visualization</h3>
              <p className="text-sm text-gray-600 mb-6">
                The heatmap below shows how the transformer model's attention mechanism focuses on different parts of the sequence.
                Darker colors indicate stronger attention between tokens.
              </p>
              
              <div className="flex space-x-4 mb-4">
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">Layer</label>
                  <select 
                    className="border rounded-md px-3 py-1.5 bg-white"
                    value={selectedLayer}
                    onChange={(e) => setSelectedLayer(Number(e.target.value))}
                  >
                    {layers.map(layer => (
                      <option key={layer} value={layer}>Layer {layer}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">Attention Head</label>
                  <select 
                    className="border rounded-md px-3 py-1.5 bg-white"
                    value={selectedHead}
                    onChange={(e) => setSelectedHead(Number(e.target.value))}
                  >
                    {heads.map(head => (
                      <option key={head} value={head}>Head {head}</option>
                    ))}
                  </select>
                </div>
              </div>
              
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="flex justify-center mb-2">
                  {sequenceTokens.map((token, i) => (
                    <div key={i} className="w-16 text-center text-xs font-medium py-1">
                      {token}
                    </div>
                  ))}
                </div>
                
                <div className="flex flex-col">
                  {attentionWeights.map((row, i) => (
                    <div key={i} className="flex">
                      <div className="w-10 flex items-center justify-center text-xs font-medium">
                        {sequenceTokens[i]}
                      </div>
                      {row.map((weight, j) => (
                        <div 
                          key={j} 
                          className="w-16 h-16 flex items-center justify-center text-xs font-medium text-white"
                          style={{ 
                            backgroundColor: `rgba(79, 70, 229, ${weight})`,
                            border: '1px solid rgba(255,255,255,0.2)'
                          }}
                        >
                          {weight.toFixed(2)}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
                
                <div className="mt-4 flex justify-center items-center">
                  <div className="w-64 h-4 bg-gradient-to-r from-white to-indigo-600"></div>
                  <div className="flex justify-between w-64 text-xs mt-1">
                    <span>Low Attention</span>
                    <span>High Attention</span>
                  </div>
                </div>
              </div>
            </div>
            
            <Separator />
            
            <div>
              <h3 className="text-lg font-medium mb-4">Transformer Architecture</h3>
              
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="flex justify-center">
                  <div className="flex flex-col items-center space-y-2">
                    <div className="bg-purple-100 border border-purple-200 rounded-lg p-3 w-64 text-center">
                      <div className="text-sm font-medium text-purple-800">Input Embedding</div>
                    </div>
                    
                    {layers.map(layer => (
                      <div key={layer} className="relative">
                        <div className="absolute -left-24 top-1/2 transform -translate-y-1/2">
                          <Badge className={`${layer === selectedLayer ? 'bg-purple-500' : 'bg-gray-300'}`}>
                            Layer {layer}
                          </Badge>
                        </div>
                        <div className={`bg-${layer === selectedLayer ? 'purple' : 'gray'}-100 border border-${layer === selectedLayer ? 'purple' : 'gray'}-200 rounded-lg p-3 w-64`}>
                          <div className="flex justify-between">
                            <div className="text-xs">Multi-Head Attention</div>
                            <div className="text-xs">Feed Forward</div>
                          </div>
                          <div className="flex justify-center mt-1">
                            <div className="flex space-x-1">
                              {heads.slice(0, 4).map(head => (
                                <div 
                                  key={head} 
                                  className={`w-3 h-3 rounded-full ${
                                    layer === selectedLayer && head === selectedHead 
                                      ? 'bg-purple-500' 
                                      : 'bg-gray-300'
                                  }`}
                                ></div>
                              ))}
                            </div>
                          </div>
                        </div>
                        <div className="h-2 w-0.5 bg-gray-300 mx-auto"></div>
                      </div>
                    ))}
                    
                    <div className="bg-purple-100 border border-purple-200 rounded-lg p-3 w-64 text-center">
                      <div className="text-sm font-medium text-purple-800">Output Layer</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="flex justify-end">
              <Button variant="outline" className="flex items-center">
                <Download className="mr-2 h-4 w-4" />
                Export Attention Weights
              </Button>
            </div>
          </div>
        </TabsContent>
        
        <TabsContent value="performance" className="p-6">
          <div className="space-y-6">
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-purple-50 p-4 rounded-lg border border-purple-100">
                <div className="text-sm text-purple-700 mb-1">Accuracy</div>
                <div className="text-2xl font-bold text-purple-800">{(accuracy * 100).toFixed(1)}%</div>
              </div>
              
              <div className="bg-indigo-50 p-4 rounded-lg border border-indigo-100">
                <div className="text-sm text-indigo-700 mb-1">F1 Score</div>
                <div className="text-2xl font-bold text-indigo-800">{(f1Score * 100).toFixed(1)}%</div>
              </div>
              
              <div className="bg-violet-50 p-4 rounded-lg border border-violet-100">
                <div className="text-sm text-violet-700 mb-1">Jaccard Score</div>
                <div className="text-2xl font-bold text-violet-800">{(jaccardScore * 100).toFixed(1)}%</div>
              </div>
            </div>
            
            <Separator />
            
            <div>
              <h3 className="text-lg font-medium mb-4">Confusion Matrix</h3>
              
              <div className="relative overflow-x-auto">
                <table className="w-full text-sm text-left border-collapse">
                  <thead>
                    <tr className="bg-gray-100">
                      <th className="p-3 border"></th>
                      <th className="p-3 border text-center font-medium" colSpan={3}>Predicted</th>
                    </tr>
                    <tr className="bg-gray-100">
                      <th className="p-3 border"></th>
                      {classLabels.map((label, i) => (
                        <th key={i} className="p-3 border text-center font-medium">{label}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {confusionMatrix.map((row, i) => (
                      <tr key={i}>
                        <th className="p-3 border bg-gray-100 font-medium">
                          {classLabels[i]}
                        </th>
                        {row.map((cell, j) => (
                          <td 
                            key={j} 
                            className={`p-3 border text-center ${i === j ? 'bg-purple-100 font-medium' : ''}`}
                          >
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              <div className="mt-6 grid grid-cols-2 gap-4">
                <div className="bg-purple-50 p-4 rounded-lg border border-purple-100">
                  <div className="text-sm text-purple-700 mb-1">Matrix Accuracy</div>
                  <div className="text-2xl font-bold text-purple-800">{(matrixAccuracy * 100).toFixed(1)}%</div>
                  <div className="text-xs text-purple-600 mt-1">
                    {correctPredictions} correct out of {totalSamples} samples
                  </div>
                </div>
                
                <div className="bg-purple-50 p-4 rounded-lg border border-purple-100">
                  <div className="text-sm text-purple-700 mb-1">Class Distribution</div>
                  <div className="flex items-center space-x-2 mt-2">
                    {confusionMatrix.map((row, i) => {
                      const classTotal = row.reduce((sum, cell) => sum + cell, 0);
                      const classPercentage = (classTotal / totalSamples) * 100;
                      
                      return (
                        <div key={i} className="flex-1">
                          <div className="text-xs text-center mb-1">{classLabels[i].split(' ')[0]}</div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className={`h-2 rounded-full ${
                                i === 0 ? 'bg-green-500' : i === 1 ? 'bg-yellow-500' : 'bg-red-500'
                              }`}
                              style={{ width: `${classPercentage}%` }}
                            ></div>
                          </div>
                          <div className="text-xs text-center mt-1">{classPercentage.toFixed(1)}%</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
            
            <Separator />
            
            <div>
              <h3 className="text-lg font-medium mb-4">Model Architecture</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <h4 className="text-sm font-medium mb-2">Transformer Parameters</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Number of Layers:</span>
                      <span className="font-medium">4</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Number of Heads:</span>
                      <span className="font-medium">8</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Hidden Size:</span>
                      <span className="font-medium">512</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Intermediate Size:</span>
                      <span className="font-medium">2048</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Dropout Rate:</span>
                      <span className="font-medium">0.1</span>
                    </div>
                  </div>
                </div>
                
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <h4 className="text-sm font-medium mb-2">Training Parameters</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Learning Rate:</span>
                      <span className="font-medium">5e-5</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Batch Size:</span>
                      <span className="font-medium">32</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Epochs:</span>
                      <span className="font-medium">10</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Optimizer:</span>
                      <span className="font-medium">AdamW</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Weight Decay:</span>
                      <span className="font-medium">0.01</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="flex justify-end">
              <Button variant="outline" className="flex items-center">
                <Download className="mr-2 h-4 w-4" />
                Export Model Performance
              </Button>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </Card>
  );
};

export default TransformerVisualization;