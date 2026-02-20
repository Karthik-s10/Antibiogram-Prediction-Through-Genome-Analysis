# SHAP Integration Guide

## Overview

This guide explains the SHAP (SHapley Additive exPlanations) integration for the antibiotic resistance prediction system. SHAP provides model explainability by showing how each feature contributes to predictions.

## Architecture

### Backend Components

#### 1. Explainability Module (`backend/explainability/`)
- **`shap_utils.py`**: Core utilities for SHAP calculations and data formatting
- **`xgboost_explainer.py`**: XGBoost-specific SHAP explainer using TreeExplainer
- **`transformer_explainer.py`**: DNABERT-specific SHAP explainer using GradientExplainer

#### 2. API Endpoints (`backend/api/explanations.py`)
- **`/api/explanations/single`**: Generate explanation for single sample
- **`/api/explanations/batch`**: Generate explanations for batch of samples
- **`/api/explanations/global-importance`**: Get global feature importance
- **`/api/explanations/summary`**: Get cross-antibiotic explanation summary
- **`/api/explanations/models`**: List available models
- **`/api/explanations/cache`**: Clear explanation cache

### Frontend Components

#### 1. Visualization Components (`src/components/explanation/`)
- **`ShapVisualization.tsx`**: Main SHAP visualization with tabs
- **`ForcePlot.tsx`**: Interactive force plot visualization
- **`ComparativeExplanation.tsx`**: Side-by-side model comparison
- **`index.ts`**: Component exports

## Usage

### Backend Usage

#### Single Sample Explanation (XGBoost)
```python
from backend.explainability import XGBoostExplainer

explainer = XGBoostExplainer()
explanation = explainer.explain_single_sample(
    antibiotic="amikacin",
    features=[0.1, 0.2, 0.3, ...],  # k-mer features
    prediction="R",
    probability=0.75
)
```

#### Single Sample Explanation (DNABERT)
```python
from backend.explainability import TransformerExplainer

explainer = TransformerExplainer()
explanation = explainer.explain_single_sample(
    antibiotic="amikacin",
    sequence="ATCGATCGATCGATCG",
    prediction="S",
    probability=0.82
)
```

#### Batch Explanations
```python
# XGBoost batch
explanations = explainer.explain_batch(
    antibiotic="amikacin",
    features_batch=[[0.1, 0.2, ...], [0.3, 0.4, ...], ...],
    predictions=["R", "S", ...],
    probabilities=[0.75, 0.82, ...]
)

# DNABERT batch
explanations = explainer.explain_batch(
    antibiotic="amikacin",
    sequences=["ATCG...", "GCTA...", ...],
    predictions=["R", "S", ...],
    probabilities=[0.75, 0.82, ...]
)
```

### Frontend Usage

#### Basic SHAP Visualization
```tsx
import { ShapVisualization } from '@/components/explanation';

function ExplanationPanel({ explanation }) {
  return (
    <ShapVisualization 
      explanation={explanation}
      isLoading={false}
      onRefresh={() => {/* refresh logic */}}
    />
  );
}
```

#### Force Plot
```tsx
import { ForcePlot } from '@/components/explanation';

<ForcePlot 
  explanation={explanation}
  className="w-full"
/>
```

#### Comparative Analysis
```tsx
import { ComparativeExplanation } from '@/components/explanation';

<ComparativeExplanation 
  xgboostExplanation={xgbExp}
  transformerExplanation={transformerExp}
  antibiotic="amikacin"
/>
```

### API Usage

#### Generate Single Explanation
```bash
curl -X POST "http://localhost:8000/api/explanations/single" \
  -H "Content-Type: application/json" \
  -d '{
    "antibiotic": "amikacin",
    "model_type": "xgboost",
    "features": [0.1, 0.2, 0.3, ...],
    "prediction": "R",
    "probability": 0.75
  }'
```

#### Generate Batch Explanations
```bash
curl -X POST "http://localhost:8000/api/explanations/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "antibiotic": "amikacin",
    "model_type": "transformer",
    "sequences": ["ATCG...", "GCTA..."],
    "predictions": ["R", "S"],
    "probabilities": [0.75, 0.82]
  }'
```

## Data Structures

### SHAPExplanation Object
```typescript
interface SHAPExplanation {
  shap_values: number[][];
  feature_names: string[];
  base_values: number | number[];
  data: any;
  prediction: string;
  probability?: number;
  model_type: string;
  antibiotic: string;
  explanation_type: string;
  metadata?: any;
}
```

### Formatted Explanation (Frontend)
```typescript
interface FormattedExplanation {
  shap_values: number[][];
  feature_names: string[];
  base_values: number | number[];
  prediction: string;
  probability?: number;
  model_type: string;
  antibiotic: string;
  explanation_type: string;
  metadata: any;
  force_plot_data: ForcePlotData;
  waterfall_plot_data: WaterfallPlotData;
}
```

## Performance Considerations

### Memory Management
- **XGBoost Models**: ~50-100MB per model
- **DNABERT Models**: ~400-500MB per model
- **SHAP Cache**: Automatically cleared when memory is constrained
- **Batch Processing**: More efficient than individual requests

### Optimization Tips
1. **Use batch processing** for multiple samples
2. **Clear cache** periodically with `DELETE /api/explanations/cache`
3. **Limit features** to top N most important for visualization
4. **Use GPU acceleration** for DNABERT explanations

### Expected Performance
- **XGBoost explanation**: < 1 second per sample
- **DNABERT explanation**: 2-5 seconds per sample (GPU), 10-30 seconds (CPU)
- **Batch processing**: 2-5x faster than individual requests

## Features

### XGBoost Explainer Features
- **TreeExplainer**: Exact SHAP values for tree models
- **K-mer feature importance**: Biological interpretation
- **Global importance**: Cross-sample feature analysis
- **Multi-class support**: S/I/R predictions

### DNABERT Explainer Features
- **GradientExplainer**: Token-level explanations
- **Sequence importance**: DNA segment contributions
- **Attention integration**: Combine with attention visualization
- **Biological context**: Map tokens to genes/mutations

### Visualization Features
- **Interactive force plots**: Real-time exploration
- **Waterfall plots**: Cumulative contribution visualization
- **Feature ranking**: Top N important features
- **Comparative analysis**: XGBoost vs DNABERT comparison
- **Export capabilities**: Download explanation data

## Integration Steps

### 1. Install Dependencies
```bash
cd backend
pip install shap==0.44.0 plotly==5.17.0
```

### 2. Train Models
```bash
# Train XGBoost models
python -m models.xgboost_trainer

# Train DNABERT models  
python -m models.transformer_trainer
```

### 3. Test Integration
```bash
cd backend
python test_shap_integration.py
```

### 4. Start Backend
```bash
cd backend
python main.py
```

### 5. Access API Documentation
Visit `http://localhost:8000/docs` for interactive API documentation.

## Troubleshooting

### Common Issues

#### Model Not Found
```
Error: Model not found: trained_models/xgboost/xgboost_amikacin.pkl
```
**Solution**: Train the required models first using the training scripts.

#### Memory Issues
```
CUDA out of memory
```
**Solution**: 
- Clear SHAP cache: `DELETE /api/explanations/cache`
- Use CPU mode for DNABERT
- Reduce batch size

#### Slow Performance
```
Explanation generation taking > 30 seconds
```
**Solution**:
- Use GPU acceleration
- Implement batch processing
- Limit feature count

#### API Errors
```
404 Not Found on /api/explanations/models
```
**Solution**: Ensure explanations router is properly registered in main.py.

### Debug Mode
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

### Planned Features
1. **Biological Context Integration**: Map features to resistance genes
2. **Real-time Explanations**: WebSocket-based streaming
3. **Advanced Visualizations**: 3D force plots, interactive heatmaps
4. **Model Comparison**: Ensemble explanation methods
5. **Export Formats**: PDF, SVG, JSON report generation

### Research Opportunities
1. **Cross-antibiotic Patterns**: Identify common resistance mechanisms
2. **Novel Biomarker Discovery**: Find new resistance indicators
3. **Clinical Decision Support**: Actionable insights for healthcare
4. **Regulatory Compliance**: Meet medical AI explainability standards

## Support

For questions or issues:
1. Check the test results: `python test_shap_integration.py`
2. Review API documentation: `http://localhost:8000/docs`
3. Examine logs in `backend/backend.log`
4. Check model availability in `trained_models/` directories

## References

- [SHAP Documentation](https://shap.readthedocs.io/)
- [XGBoost SHAP Integration](https://xgboost.readthedocs.io/en/latest/tutorials/shap.html)
- [Transformer SHAP Methods](https://huggingface.co/docs/transformers/model_explanation)
- [Medical AI Explainability](https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-machine-learning-aiml)
