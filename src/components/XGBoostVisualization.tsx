import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { BarChart, Cpu, Download, Info } from "lucide-react";

interface FeatureImportance {
  feature: string;
  importance: number;
}

interface XGBoostVisualizationProps {
  modelName?: string;
  accuracy?: number;
  f1Score?: number;
  jaccardScore?: number;
  featureImportance?: FeatureImportance[];
  confusionMatrix?: number[][];
}

const XGBoostVisualization: React.FC<XGBoostVisualizationProps> = ({
  modelName = "XGBoost Antibiogram Predictor",
  accuracy = 0.92,
  f1Score = 0.89,
  jaccardScore = 0.85,
  featureImportance = [
    { feature: "kmer_ACGTA", importance: 0.58 },
    { feature: "kmer_TCGAT", importance: 0.42 },
    { feature: "kmer_GCTAT", importance: 0.37 },
    { feature: "kmer_ATGCA", importance: 0.31 },
    { feature: "kmer_CGATA", importance: 0.28 },
    { feature: "kmer_TAGCT", importance: 0.25 },
    { feature: "kmer_GACTA", importance: 0.22 },
    { feature: "kmer_CTAGA", importance: 0.19 },
    { feature: "kmer_AGCTA", importance: 0.17 },
    { feature: "kmer_TGCAT", importance: 0.15 }
  ],
  confusionMatrix = [
    [45, 3, 2],
    [4, 38, 3],
    [1, 2, 42]
  ]
}) => {
  const [activeTab, setActiveTab] = useState("feature-importance");
  
  // Calculate total samples and accuracy from confusion matrix
  const totalSamples = confusionMatrix.reduce((sum, row) => 
    sum + row.reduce((rowSum, cell) => rowSum + cell, 0), 0);
  
  const correctPredictions = confusionMatrix.reduce((sum, row, i) => 
    sum + row[i], 0);
  
  const matrixAccuracy = correctPredictions / totalSamples;
  
  // Class labels
  const classLabels = ["Susceptible (S)", "Intermediate (I)", "Resistant (R)"];
  
  return (
    <Card className="w-full max-w-4xl mx-auto bg-white shadow-lg">
      <CardHeader className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white">
        <div className="flex justify-between items-center">
          <div>
            <CardTitle className="text-2xl flex items-center">
              <Cpu className="mr-2 h-6 w-6" />
              {modelName}
            </CardTitle>
            <CardDescription className="text-blue-100">
              Gradient Boosting Model for Antibiotic Resistance Prediction
            </CardDescription>
          </div>
          <Badge className="bg-white text-blue-700 text-sm px-3 py-1">
            {(accuracy * 100).toFixed(1)}% Accuracy
          </Badge>
        </div>
      </CardHeader>
      
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid grid-cols-2 w-full">
          <TabsTrigger value="feature-importance">
            <BarChart className="mr-2 h-4 w-4" />
            Feature Importance
          </TabsTrigger>
          <TabsTrigger value="confusion-matrix">
            <Info className="mr-2 h-4 w-4" />
            Confusion Matrix
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="feature-importance" className="p-6">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium mb-4">Feature Importance Analysis</h3>
              <p className="text-sm text-gray-600 mb-6">
                The chart below shows the most important k-mer features that influence the model's predictions.
                Higher values indicate stronger influence on the prediction outcome.
              </p>
              
              <div className="space-y-4">
                {featureImportance.map((feature, index) => (
                  <div key={index} className="space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">{feature.feature}</span>
                      <span className="text-sm text-gray-600">{(feature.importance * 100).toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                      <div 
                        className="bg-gradient-to-r from-blue-500 to-cyan-500 h-2.5 rounded-full" 
                        style={{ width: `${feature.importance * 100}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            <Separator />
            
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                <div className="text-sm text-blue-700 mb-1">Accuracy</div>
                <div className="text-2xl font-bold text-blue-800">{(accuracy * 100).toFixed(1)}%</div>
              </div>
              
              <div className="bg-cyan-50 p-4 rounded-lg border border-cyan-100">
                <div className="text-sm text-cyan-700 mb-1">F1 Score</div>
                <div className="text-2xl font-bold text-cyan-800">{(f1Score * 100).toFixed(1)}%</div>
              </div>
              
              <div className="bg-teal-50 p-4 rounded-lg border border-teal-100">
                <div className="text-sm text-teal-700 mb-1">Jaccard Score</div>
                <div className="text-2xl font-bold text-teal-800">{(jaccardScore * 100).toFixed(1)}%</div>
              </div>
            </div>
            
            <div className="flex justify-end">
              <Button variant="outline" className="flex items-center">
                <Download className="mr-2 h-4 w-4" />
                Export Feature Importance
              </Button>
            </div>
          </div>
        </TabsContent>
        
        <TabsContent value="confusion-matrix" className="p-6">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium mb-4">Confusion Matrix</h3>
              <p className="text-sm text-gray-600 mb-6">
                The confusion matrix shows how well the model predicts each class.
                Diagonal values represent correct predictions, while off-diagonal values are misclassifications.
              </p>
              
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
                            className={`p-3 border text-center ${i === j ? 'bg-green-100 font-medium' : ''}`}
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
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                  <div className="text-sm text-blue-700 mb-1">Matrix Accuracy</div>
                  <div className="text-2xl font-bold text-blue-800">{(matrixAccuracy * 100).toFixed(1)}%</div>
                  <div className="text-xs text-blue-600 mt-1">
                    {correctPredictions} correct out of {totalSamples} samples
                  </div>
                </div>
                
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                  <div className="text-sm text-blue-700 mb-1">Class Distribution</div>
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
            
            <div className="flex justify-end">
              <Button variant="outline" className="flex items-center">
                <Download className="mr-2 h-4 w-4" />
                Export Confusion Matrix
              </Button>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </Card>
  );
};

export default XGBoostVisualization;