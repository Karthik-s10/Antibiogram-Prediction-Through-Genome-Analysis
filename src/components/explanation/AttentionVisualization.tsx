import React, { useState } from 'react';

interface AttentionVisualizationProps {
  attention: number[][][];  // [layer][head][from][to]
  tokens: string[];
  sequence: string;
  width?: number;
  height?: number;
}

export const AttentionVisualization: React.FC<AttentionVisualizationProps> = ({
  attention,
  tokens,
  sequence,
  width = 800,
  height = 400
}) => {
  const [selectedLayer, setSelectedLayer] = useState(0);
  const [selectedHead, setSelectedHead] = useState(0);

  if (!attention || attention.length === 0) {
    return <div>No attention data available</div>;
  }

  // Get attention matrix for selected layer and head
  const attentionMatrix = attention[selectedLayer]?.[selectedHead];
  const numLayers = attention.length;
  const numHeads = attention[0]?.length || 0;
  
  // Check if attentionMatrix is valid
  if (!attentionMatrix || !Array.isArray(attentionMatrix)) {
    return <div>Invalid attention data for selected layer and head</div>;
  }

  // Get max value for normalization
  const maxValue = Math.max(
    ...attentionMatrix.reduce((acc, row) => {
      if (Array.isArray(row)) {
        return [...acc, ...row];
      }
      return acc;
    }, []).map(v => typeof v === 'number' ? v : 0)
  );

  return (
    <div className="w-full">
      <h4 className="text-lg font-semibold mb-4">
        Attention Visualization - Layer {selectedLayer + 1}, Head {selectedHead + 1}
      </h4>
      
      {/* Controls */}
      <div className="mb-4 space-y-2">
        <div className="flex items-center space-x-4">
          <span className="text-sm font-medium">Layer:</span>
          <div className="flex space-x-1">
            {[...Array(numLayers)].map((_, i) => (
              <button
                key={i}
                onClick={() => {
                  setSelectedLayer(i);
                  setSelectedHead(0);
                }}
                className={`px-2 py-1 text-xs rounded ${
                  i === selectedLayer
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {i + 1}
              </button>
            ))}
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          <span className="text-sm font-medium">Head:</span>
          <div className="flex space-x-1">
            {[...Array(numHeads)].map((_, i) => (
              <button
                key={i}
                onClick={() => setSelectedHead(i)}
                className={`px-2 py-1 text-xs rounded ${
                  i === selectedHead
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {i + 1}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Attention Matrix */}
      <div className="overflow-auto max-h-96 border border-gray-300 rounded">
        <table className="min-w-full">
          <thead>
            <tr>
              <th className="p-2 text-xs font-medium bg-gray-50">From \ To</th>
              {tokens.map((token, i) => (
                <th key={i} className="p-2 text-xs font-medium bg-gray-50 rotate-45">
                  {token}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {attentionMatrix.map((row, i) => (
              <tr key={i}>
                <td className="p-2 text-xs font-medium bg-gray-50">{tokens[i]}</td>
                {Array.isArray(row) ? row.map((value, j) => (
                  <td
                    key={j}
                    className="p-1 text-center"
                    style={{
                      backgroundColor: `rgba(59, 130, 246, ${value / maxValue})`,
                      color: value / maxValue > 0.5 ? 'white' : 'black'
                    }}
                    title={`From: ${tokens[i]}, To: ${tokens[j]}, Attention: ${value.toFixed(4)}`}
                  >
                    <span className="text-xs">{value.toFixed(2)}</span>
                  </td>
                )) : (
                  <td colSpan={tokens.length} className="p-2 text-center text-gray-500">
                    Invalid row data
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      <div className="mt-4 text-sm text-gray-600">
        <p>Attention weights show how the model focuses on different parts of the sequence.</p>
        <p>Darker blue indicates higher attention weights.</p>
      </div>
    </div>
  );
};
