import React from 'react';

interface ShapVisualizationProps {
  explanation: {
    shap_values: number[][];
    feature_names: string[];
    class_names: string[];
  };
}

export function ShapVisualization({ explanation }: ShapVisualizationProps) {
  if (!explanation || !explanation.shap_values || !explanation.feature_names) {
    return <div>No SHAP data available</div>;
  }

  // Prepare data for visualization
  const features = explanation.feature_names;
  const values = explanation.shap_values[0]; // First class
  const data = features.map((f, i) => ({
    feature: f,
    value: values[i],
    absValue: Math.abs(values[i]),
    sign: values[i] > 0 ? 'positive' : 'negative'
  }))
  .sort((a, b) => b.absValue - a.absValue)
  .slice(0, 10); // Top 10 features

  const maxValue = Math.max(...data.map(d => Math.abs(d.value)));

  return (
    <div className="w-full">
      <h4 className="text-lg font-semibold mb-4">Top 10 Feature Contributions</h4>
      <div className="space-y-2">
        {data.map((item, index) => (
          <div key={index} className="flex items-center space-x-3">
            <span className="text-sm font-medium w-32 truncate" title={item.feature}>
              {item.feature}
            </span>
            <div className="flex-1 bg-gray-200 rounded-full h-6 relative overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  item.sign === 'positive' ? 'bg-red-500' : 'bg-green-500'
                }`}
                style={{
                  width: `${(Math.abs(item.value) / maxValue) * 100}%`,
                  marginLeft: item.sign === 'negative' ? 'auto' : '0',
                  marginRight: item.sign === 'positive' ? 'auto' : '0'
                }}
              />
            </div>
            <span className={`text-sm font-mono w-16 text-right ${
              item.sign === 'positive' ? 'text-red-600' : 'text-green-600'
            }`}>
              {item.sign === 'positive' ? '+' : ''}{item.value.toFixed(3)}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-4 text-sm text-gray-600">
        <p>SHAP values show how each feature contributes to the prediction.</p>
        <p>Red bars indicate features that increase resistance, green bars indicate features that decrease resistance.</p>
      </div>
    </div>
  );
}
