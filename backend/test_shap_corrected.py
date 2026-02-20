"""
Corrected SHAP test for actual model structure.
Works with job-based model naming (xgboost_f0849bdd.pkl).
"""
import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path
import json
import pickle
import shap

# Add to path
sys.path.append(str(Path(__file__).parent))

from explainability import SHAPUtils

def test_xgboost_shap_direct():
    """Test SHAP directly with the XGBoost model."""
    print("🌳 Testing XGBoost SHAP (Direct Approach)...")
    
    # Load the actual model
    model_path = Path("trained_models/xgboost_f0849bdd.pkl")
    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        return None
    
    print(f"📦 Loading model: {model_path}")
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    print(f"✅ Model loaded!")
    print(f"   - Type: {type(model_data)}")
    
    # Check if it's a single model or dictionary of models
    if isinstance(model_data, dict):
        print(f"   - Dictionary with {len(model_data)} keys")
        print(f"   - Keys: {list(model_data.keys())[:5]}...")
        
        # Try to get a specific model
        if 'amikacin' in model_data:
            model = model_data['amikacin']
            antibiotic = 'amikacin'
        else:
            # Use first available model
            first_key = list(model_data.keys())[0]
            model = model_data[first_key]
            antibiotic = first_key
            print(f"   - Using first model: {antibiotic}")
    else:
        model = model_data
        antibiotic = "unknown"
        print(f"   - Single model loaded")
    
    print(f"   - Model type: {type(model)}")
    
    # Load feature names
    features_path = Path("trained_models/xgboost_f0849bdd_features.json")
    if features_path.exists():
        with open(features_path, 'r') as f:
            features_data = json.load(f)
            feature_names = features_data.get('feature_names', [])
            print(f"   - Features loaded: {len(feature_names)}")
    else:
        # Generate generic feature names based on model
        if hasattr(model, 'n_features_in_'):
            n_features = model.n_features_in_
        else:
            n_features = 155211  # From the error message
        
        feature_names = [f"kmer_{i}" for i in range(n_features)]
        print(f"   - Generated {len(feature_names)} feature names")
    
    # Create SHAP explainer
    try:
        print(f"\n🧪 Creating SHAP TreeExplainer...")
        explainer = shap.TreeExplainer(model)
        print(f"✅ SHAP explainer created!")
        
        # Generate sample features
        sample_features = np.random.rand(len(feature_names))
        # Add some realistic patterns
        sample_features[0] = 0.8  # Important k-mer
        sample_features[1] = 0.6
        sample_features[2] = 0.9
        sample_features[10] = 0.7
        sample_features[50] = 0.4
        
        print(f"📊 Sample features: {len(sample_features)} dimensions")
        
        # Generate SHAP values
        print(f"🔍 Computing SHAP values...")
        shap_values = explainer.shap_values(sample_features.reshape(1, -1))
        
        print(f"✅ SHAP values computed!")
        print(f"   - Shape: {shap_values.shape}")
        print(f"   - Base value: {explainer.expected_value}")
        
        # Get prediction
        prediction_proba = model.predict_proba(sample_features.reshape(1, -1))[0]
        prediction_class = np.argmax(prediction_proba)
        classes = ['S', 'I', 'R']  # Susceptible, Intermediate, Resistant
        prediction = classes[prediction_class]
        confidence = float(prediction_proba[prediction_class])
        
        print(f"   - Prediction: {prediction}")
        print(f"   - Confidence: {confidence:.3f}")
        
        # Rank features
        if len(shap_values.shape) > 1:
            shap_vals = shap_values[0]
        else:
            shap_vals = shap_values
        
        feature_importance = []
        for i, (name, val) in enumerate(zip(feature_names, shap_vals)):
            feature_importance.append((name, abs(val), val))
        
        feature_importance.sort(key=lambda x: x[1], reverse=True)
        top_features = feature_importance[:15]
        
        print(f"\n📈 Top 15 K-mer Features:")
        for i, (feature, importance, direction) in enumerate(top_features):
            arrow = "↑" if direction > 0 else "↓"
            print(f"   {i+1:2d}. {feature[:20]:20}: {direction:+.4f} {arrow}")
        
        # Create explanation object
        from explainability.shap_utils import SHAPExplanation
        explanation = SHAPExplanation(
            shap_values=shap_values,
            feature_names=feature_names,
            base_values=explainer.expected_value,
            data=sample_features,
            prediction=prediction,
            probability=confidence,
            model_type="XGBoost",
            antibiotic=antibiotic,
            explanation_type="feature_importance",
            metadata={
                'job_id': 'f0849bdd',
                'model_path': str(model_path),
                'feature_count': len(feature_names),
                'top_features': top_features
            }
        )
        
        # Save explanation
        output_dir = Path(__file__).parent / "data_cache" / "shap_explanations"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save formatted explanation
        utils = SHAPUtils()
        formatted_exp = utils.format_explanation_for_frontend(explanation)
        
        with open(output_dir / "xgboost_working_explanation.json", 'w') as f:
            json.dump(formatted_exp, f, indent=2)
        
        print(f"💾 Saved: {output_dir / 'xgboost_working_explanation.json'}")
        
        return explanation
        
    except Exception as e:
        print(f"❌ SHAP error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_transformer_shap_direct():
    """Test SHAP with DNABERT model (direct approach)."""
    print("\n🤖 Testing DNABERT SHAP (Direct Approach)...")
    
    model_path = Path("trained_models/transformer_ce13dcc6")
    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        return None
    
    print(f"📂 Model directory: {model_path}")
    
    # List model files
    model_files = list(model_path.rglob("*"))
    print(f"📁 Files found: {len(model_files)}")
    
    # Look for key files
    config_file = None
    model_file = None
    
    for file in model_files:
        if file.name == "config.json":
            config_file = file
            print(f"✅ Config found: {file.name}")
        elif file.name in ["pytorch_model.bin", "model.safetensors"]:
            model_file = file
            print(f"✅ Model weights found: {file.name}")
    
    if not config_file:
        print("❌ No config.json found")
        # List what files are actually there
        print("📋 Available files:")
        for file in model_files[:10]:  # Show first 10
            print(f"   - {file.name}")
        if len(model_files) > 10:
            print(f"   ... and {len(model_files) - 10} more")
        return None
    
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        
        print(f"🔧 Loading tokenizer and model...")
        tokenizer = AutoTokenizer.from_pretrained(str(model_path))
        model = AutoModelForSequenceClassification.from_pretrained(str(model_path))
        
        print(f"✅ DNABERT model loaded!")
        print(f"   - Model type: {type(model).__name__}")
        print(f"   - Classes: {model.config.num_labels}")
        print(f"   - Hidden size: {model.config.hidden_size}")
        
        # Create SHAP explainer
        print(f"\n🧪 Creating SHAP GradientExplainer...")
        
        # Create background data
        background_sequences = [
            "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
            "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA",
            "CCCCGGGGAAAATTTTCCCCGGGGAAAATTTTCCCC"
        ]
        
        # Tokenize background
        background_inputs = tokenizer(
            background_sequences,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        
        # Create explainer
        explainer = shap.GradientExplainer(model, background_inputs)
        print(f"✅ SHAP explainer created!")
        
        # Test sequence
        test_sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
        
        # Tokenize test sequence
        test_inputs = tokenizer(
            test_sequence,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        
        print(f"🧬 Test sequence: {len(test_sequence)} bp")
        print(f"📊 Tokenized shape: {test_inputs['input_ids'].shape}")
        
        # Generate SHAP values
        print(f"🔍 Computing SHAP values...")
        shap_values = explainer.shap_values(test_inputs)
        
        print(f"✅ SHAP values computed!")
        print(f"   - Shape: {shap_values.shape}")
        
        # Get tokens
        tokens = tokenizer.convert_ids_to_tokens(test_inputs['input_ids'][0])
        print(f"   - Tokens: {len(tokens)}")
        
        # Get prediction
        with torch.no_grad():
            outputs = model(**test_inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=-1)
            pred_class = torch.argmax(probabilities, dim=-1)
            
            classes = ['S', 'I', 'R']
            prediction = classes[pred_class[0].item()]
            confidence = probabilities[0][pred_class[0]].item()
        
        print(f"   - Prediction: {prediction}")
        print(f"   - Confidence: {confidence:.3f}")
        
        # Get top tokens
        if len(shap_values.shape) > 2:
            shap_vals = shap_values[0]  # Remove batch dimension
        else:
            shap_vals = shap_values
        
        if len(shap_vals.shape) > 1:
            shap_vals = shap_vals[0]  # Remove class dimension
        
        token_importance = []
        for i, (token, val) in enumerate(zip(tokens, shap_vals)):
            clean_token = token.replace('Ġ', '')  # Remove special token prefix
            token_importance.append((clean_token, abs(val), val))
        
        token_importance.sort(key=lambda x: x[1], reverse=True)
        top_tokens = token_importance[:15]
        
        print(f"\n📈 Top 15 DNA Tokens:")
        for i, (token, importance, direction) in enumerate([(t[0], t[1], t[2]) for t in top_tokens]):
            arrow = "↑" if direction > 0 else "↓"
            print(f"   {i+1:2d}. {token:15}: {direction:+.4f} {arrow}")
        
        # Create explanation object
        from explainability.shap_utils import SHAPExplanation
        explanation = SHAPExplanation(
            shap_values=shap_values,
            feature_names=[f"token_{i}_{token}" for i, token in enumerate(tokens)],
            base_values=explainer.expected_value,
            data=test_sequence,
            prediction=prediction,
            probability=confidence,
            model_type="DNABERT",
            antibiotic="amikacin",
            explanation_type="token_importance",
            metadata={
                'job_id': 'ce13dcc6',
                'model_path': str(model_path),
                'sequence_length': len(test_sequence),
                'token_count': len(tokens),
                'top_tokens': top_tokens
            }
        )
        
        # Save explanation
        output_dir = Path(__file__).parent / "data_cache" / "shap_explanations"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save formatted explanation
        utils = SHAPUtils()
        formatted_exp = utils.format_explanation_for_frontend(explanation)
        
        with open(output_dir / "transformer_working_explanation.json", 'w') as f:
            json.dump(formatted_exp, f, indent=2)
        
        print(f"💾 Saved: {output_dir / 'transformer_working_explanation.json'}")
        
        return explanation
        
    except Exception as e:
        print(f"❌ DNABERT SHAP error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def generate_final_summary(xgb_exp, transformer_exp):
    """Generate final summary report."""
    print(f"\n🎉 SHAP Integration Final Summary")
    print("=" * 60)
    
    summary = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'status': {
            'xgboost_working': xgb_exp is not None,
            'transformer_working': transformer_exp is not None,
            'overall_working': (xgb_exp is not None) or (transformer_exp is not None)
        },
        'models': {
            'xgboost': {
                'job_id': 'f0849bdd',
                'prediction': xgb_exp.prediction if xgb_exp else None,
                'confidence': xgb_exp.probability if xgb_exp else None,
                'features': len(xgb_exp.feature_names) if xgb_exp else 0
            },
            'transformer': {
                'job_id': 'ce13dcc6',
                'prediction': transformer_exp.prediction if transformer_exp else None,
                'confidence': transformer_exp.probability if transformer_exp else None,
                'tokens': len(transformer_exp.feature_names) if transformer_exp else 0
            }
        },
        'comparison': {
            'agreement': xgb_exp.prediction == transformer_exp.prediction if (xgb_exp and transformer_exp) else None,
            'confidence_diff': abs((xgb_exp.probability or 0) - (transformer_exp.probability or 0)) if (xgb_exp and transformer_exp) else None
        }
    }
    
    # Save summary
    output_dir = Path(__file__).parent / "data_cache" / "shap_explanations"
    with open(output_dir / "final_shap_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✅ Summary saved: {output_dir / 'final_shap_summary.json'}")
    
    # Status report
    print(f"\n📊 Integration Status:")
    print(f"   XGBoost SHAP: {'✅ WORKING' if xgb_exp else '❌ FAILED'}")
    print(f"   DNABERT SHAP: {'✅ WORKING' if transformer_exp else '❌ FAILED'}")
    print(f"   Overall: {'✅ SUCCESS' if (xgb_exp or transformer_exp) else '❌ FAILED'}")
    
    if xgb_exp:
        print(f"\n🌳 XGBoost Results:")
        print(f"   - Prediction: {xgb_exp.prediction}")
        print(f"   - Confidence: {xgb_exp.probability:.3f}")
        print(f"   - Features: {len(xgb_exp.feature_names)}")
    
    if transformer_exp:
        print(f"\n🤖 DNABERT Results:")
        print(f"   - Prediction: {transformer_exp.prediction}")
        print(f"   - Confidence: {transformer_exp.probability:.3f}")
        print(f"   - Tokens: {len(transformer_exp.feature_names)}")
    
    print(f"\n🔧 Next Steps:")
    print(f"   1. Start backend: python main.py")
    print(f"   2. Test API: http://localhost:8000/api/explanations/models")
    print(f"   3. View explanations in frontend")
    print(f"   4. Check saved files in: {output_dir}")

def main():
    """Main function."""
    print("🚀 SHAP Integration Test - Corrected Version")
    print("Testing with actual trained models from your jobs")
    print("=" * 60)
    
    # Test XGBoost
    xgb_exp = test_xgboost_shap_direct()
    
    # Test DNABERT
    transformer_exp = test_transformer_shap_direct()
    
    # Generate summary
    generate_final_summary(xgb_exp, transformer_exp)

if __name__ == "__main__":
    main()
