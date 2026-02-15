import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';
import { AttentionVisualization } from './AttentionVisualization';
import { ShapVisualization } from './ShapVisualization';

interface ModelExplanationProps {
  sampleData: Record<string, any>;
  sequence?: string;
  modelType: 'xgboost' | 'dnabert';
  featureNames?: string[];
  classNames?: string[];
}

export function ModelExplanation({ 
  sampleData, 
  sequence, 
  modelType,
  featureNames,
  classNames = ['Susceptible', 'Intermediate', 'Resistant']
}: ModelExplanationProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [explanation, setExplanation] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('shap');

  const fetchExplanation = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/explanations/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sample_data: sampleData,
          sequence: sequence,
          model_type: modelType,
          class_names: classNames,
          feature_names: featureNames
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate explanation');
      }
      
      const data = await response.json();
      setExplanation(data.explanation);
    } catch (error) {
      console.error('Error fetching explanation:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="mt-4">
      <CardHeader>
        <div className="flex justify-between items-center">
          <div>
            <CardTitle>Model Explanation</CardTitle>
            <CardDescription>
              {modelType === 'dnabert' 
                ? 'DNABERT attention and feature importance' 
                : 'XGBoost feature importance'}
            </CardDescription>
          </div>
          <Button 
            onClick={fetchExplanation} 
            disabled={isLoading}
            variant="outline"
            size="sm"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              'Explain Prediction'
            )}
          </Button>
        </div>
      </CardHeader>
      
      <CardContent>
        {explanation ? (
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="shap">Feature Importance</TabsTrigger>
              {modelType === 'dnabert' && (
                <TabsTrigger value="attention">Attention Map</TabsTrigger>
              )}
            </TabsList>
            
            <TabsContent value="shap" className="mt-4">
              {explanation.shap && (
                <ShapVisualization explanation={explanation.shap} />
              )}
            </TabsContent>
            
            {modelType === 'dnabert' && (
              <TabsContent value="attention" className="mt-4">
                {explanation.attention ? (
                  <div className="overflow-x-auto">
                    <AttentionVisualization
                      attention={explanation.attention.attention}
                      tokens={explanation.attention.tokens}
                      sequence={explanation.attention.sequence}
                    />
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    No attention data available
                  </div>
                )}
              </TabsContent>
            )}
          </Tabs>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            {isLoading ? (
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="h-8 w-8 animate-spin" />
                <p>Generating explanation...</p>
              </div>
            ) : (
              <p>Click "Explain Prediction" to see how the model made its decision</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
