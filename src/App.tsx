import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Brain, Search, Database, Github, Dna } from 'lucide-react';
import ModelTrainer from '@/components/ModelTrainer';
import GenomePredictor from '@/components/GenomePredictor';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('predict');
  const [trainingResults, setTrainingResults] = useState<any>(null);
  const [targetAntibiotic, setTargetAntibiotic] = useState('ciprofloxacin');
  
  // Handle training completion
  const handleTrainingComplete = (results: any) => {
    setTrainingResults(results);
    setTargetAntibiotic(results.targetAntibiotic);
  };
  
  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-gradient-to-r from-blue-700 to-purple-700 text-white py-6 px-4 shadow-md">
        <div className="container mx-auto flex justify-between items-center">
          <div className="flex items-center">
            <Dna className="h-8 w-8 mr-3" />
            <div>
              <h1 className="text-2xl font-bold">Antibiogram Predictor</h1>
              <p className="text-sm text-blue-100">
                Predict antibiotic resistance from bacterial genomes
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <a 
              href="https://github.com/yourusername/antibiogram-predictor" 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center text-sm hover:text-blue-200 transition-colors"
            >
              <Github className="h-4 w-4 mr-1" />
              GitHub
            </a>
            
            <Button variant="outline" className="text-white border-white hover:bg-white hover:text-blue-700">
              Documentation
            </Button>
          </div>
        </div>
      </header>
      
      <main className="container mx-auto py-8 px-4">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2 max-w-md mx-auto mb-8">
            <TabsTrigger value="predict" className="flex items-center">
              <Search className="mr-2 h-4 w-4" />
              Predict
            </TabsTrigger>
            <TabsTrigger value="train" className="flex items-center">
              <Brain className="mr-2 h-4 w-4" />
              Train Models
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="predict">
            <GenomePredictor targetAntibiotic={targetAntibiotic} />
          </TabsContent>
          
          <TabsContent value="train">
            <ModelTrainer onTrainingComplete={handleTrainingComplete} />
          </TabsContent>
        </Tabs>
      </main>
      
      <footer className="bg-gray-800 text-gray-300 py-6 px-4 mt-12">
        <div className="container mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-4 md:mb-0">
              <div className="flex items-center">
                <Dna className="h-6 w-6 mr-2" />
                <span className="font-bold">Antibiogram Predictor</span>
              </div>
              <p className="text-xs mt-1">
                Predicting antibiotic resistance from whole genome sequences
              </p>
            </div>
            
            <div className="text-xs">
              <p>Built with XGBoost and DNABERT</p>
              <p>© 2023 Antibiogram Predictor</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;