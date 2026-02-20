"""
Test SHAP explanations with current trained models.
Checks for existing XGBoost and DNABERT models and generates explanations.
"""
import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path
import json

# Add to path
sys.path.append(str(Path(__file__).parent))

from explainability import SHAPUtils, XGBoostExplainer, TransformerExplainer

def check_model_directories():
    """Check what models are available."""
    print("🔍 Checking Model Directories...")
    
    base_dirs = [
        "trained_models",
        "backend/trained_models", 
        "../trained_models",
        "../backend/trained_models"
    ]
    
    found_dirs = []
    for base_dir in base_dirs:
        if Path(base_dir).exists():
            found_dirs.append(Path(base_dir))
            print(f"✅ Found: {base_dir}")
    
    if not found_dirs:
        print("❌ No trained model directories found")
        print("🔍 Searching entire project...")
        
        # Search entire project for model files
        project_root = Path(__file__).parent.parent
        for pkl_file in project_root.rglob("*.pkl"):
            print(f"📦 Found model: {pkl_file}")
        
        for model_dir in project_root.rglob("*transformer*"):
            if model_dir.is_dir():
                print(f"🤖 Found transformer: {model_dir}")
    
    return found_dirs

def check_xgboost_models(models_dir):
    """Check for XGBoost models."""
    print("\n🌳 Checking XGBoost Models...")
    
    xgb_dir = models_dir / "xgboost"
    if not xgb_dir.exists():
        print("❌ XGBoost directory not found")
        return []
    
    # Look for .pkl files
    model_files = list(xgb_dir.glob("*.pkl"))
    print(f"📦 Found {len(model_files)} XGBoost models:")
    
    models = []
    for model_file in model_files:
        antibiotic = model_file.stem.replace("xgboost_", "")
        models.append({
            'antibiotic': antibiotic,
            'file': model_file,
            'size_mb': model_file.stat().st_size / (1024 * 1024)
        })
        print(f"  ✅ {antibiotic}: {model_file.name} ({model_file.stat().st_size / (1024 * 1024):.1f} MB)")
    
    return models

def check_transformer_models(models_dir):
    """Check for DNABERT transformer models."""
    print("\n🤖 Checking DNABERT Models...")
    
    transformer_dirs = [
        models_dir / "transformer",
        models_dir / "transformer", 
        models_dir / "dnabert",
        models_dir / "transformers"
    ]
    
    models = []
    for transformer_dir in transformer_dirs:
        if transformer_dir.exists():
            print(f"📂 Checking: {transformer_dir}")
            
            # Look for model directories (not files)
            model_dirs = [d for d in transformer_dir.iterdir() if d.is_dir()]
            
            for model_dir in model_dirs:
                # Check if it contains model files
                config_file = model_dir / "config.json"
                pytorch_file = model_dir / "pytorch_model.bin"
                
                if config_file.exists() or pytorch_file.exists():
                    antibiotic = model_dir.name.replace("transformer_", "").replace("dnabert_", "")
                    size = sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file())
                    
                    models.append({
                        'antibiotic': antibiotic,
                        'dir': model_dir,
                        'size_mb': size / (1024 * 1024)
                    })
                    print(f"  ✅ {antibiotic}: {model_dir.name} ({size / (1024 * 1024):.1f} MB)")
    
    if not models:
        print("❌ No DNABERT models found")
    
    return models

def test_xgboost_explanations(xgb_models, models_dir):
    """Test SHAP explanations for XGBoost models."""
    if not xgb_models:
        print("\n⚠️  No XGBoost models to test")
        return
    
    print(f"\n🧪 Testing SHAP for {len(xgb_models)} XGBoost Models...")
    
    try:
        explainer = XGBoostExplainer(str(models_dir / "xgboost"))
        
        # Test first 3 models
        test_models = xgb_models[:3]
        
        for model_info in test_models:
            antibiotic = model_info['antibiotic']
            print(f"\n🔍 Testing: {antibiotic}")
            
            try:
                # Generate sample features (k-mer style)
                n_features = 1000
                features = np.random.rand(n_features)
                
                # Generate explanation
                explanation = explainer.explain_single_sample(
                    antibiotic=antibiotic,
                    features=features,
                    prediction="R",
                    probability=0.75
                )
                
                print(f"  ✅ Explanation generated!")
                print(f"     - Features: {len(explanation.feature_names)}")
                print(f"     - SHAP shape: {explanation.shap_values.shape}")
                print(f"     - Base value: {explanation.base_values}")
                print(f"     - Model type: {explanation.model_type}")
                
                # Get top features
                top_features = explainer.shap_utils.rank_features_by_importance(
                    explanation.shap_values, 
                    explanation.feature_names, 
                    top_k=5
                )
                
                print(f"     - Top 5 features:")
                for i, (feature, importance) in enumerate(top_features):
                    print(f"       {i+1}. {feature}: {importance:.4f}")
                
                # Save explanation
                output_dir = Path(__file__).parent / "data_cache" / "shap_explanations"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                with open(output_dir / f"xgb_{antibiotic}_explanation.json", 'w') as f:
                    json.dump(explainer.__dict__, f, indent=2, default=str)
                
                print(f"     💾 Saved: {output_dir / f'xgb_{antibiotic}_explanation.json'}")
                
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
        
        # Test global importance
        if test_models:
            first_antibiotic = test_models[0]['antibiotic']
            print(f"\n📊 Testing global importance for {first_antibiotic}...")
            
            try:
                importance = explainer.get_global_feature_importance(first_antibiotic)
                top_10 = list(importance.items())[:10]
                
                print(f"  ✅ Global importance generated!")
                print(f"     - Total features: {len(importance)}")
                print(f"     - Top 10 global features:")
                for i, (feature, imp) in enumerate(top_10):
                    print(f"       {i+1}. {feature}: {imp:.4f}")
                    
            except Exception as e:
                print(f"  ❌ Global importance error: {str(e)}")
        
    except Exception as e:
        print(f"❌ XGBoost explainer error: {str(e)}")

def test_transformer_explanations(transformer_models, models_dir):
    """Test SHAP explanations for DNABERT models."""
    if not transformer_models:
        print("\n⚠️  No DNABERT models to test")
        return
    
    print(f"\n🧪 Testing SHAP for {len(transformer_models)} DNABERT Models...")
    
    try:
        explainer = TransformerExplainer(str(models_dir / "transformer"))
        
        # Test first 3 models
        test_models = transformer_models[:3]
        
        for model_info in test_models:
            antibiotic = model_info['antibiotic']
            print(f"\n🔍 Testing: {antibiotic}")
            
            try:
                # Generate sample DNA sequence
                sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
                
                # Generate explanation
                explanation = explainer.explain_single_sample(
                    antibiotic=antibiotic,
                    sequence=sequence,
                    prediction="S",
                    probability=0.82
                )
                
                print(f"  ✅ Explanation generated!")
                print(f"     - Tokens: {len(explanation.feature_names)}")
                print(f"     - SHAP shape: {explanation.shap_values.shape}")
                print(f"     - Base value: {explanation.base_values}")
                print(f"     - Model type: {explanation.model_type}")
                
                # Get top tokens
                if len(explanation.shap_values.shape) > 1:
                    shap_vals = explanation.shap_values[0]
                else:
                    shap_vals = explanation.shap_values
                
                token_importance = []
                for i, (token, val) in enumerate(zip(explanation.feature_names, shap_vals)):
                    token_importance.append((token, abs(val)))
                
                token_importance.sort(key=lambda x: x[1], reverse=True)
                top_tokens = token_importance[:5]
                
                print(f"     - Top 5 tokens:")
                for i, (token, importance) in enumerate(top_tokens):
                    print(f"       {i+1}. {token}: {importance:.4f}")
                
                # Save explanation
                output_dir = Path(__file__).parent / "data_cache" / "shap_explanations"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                with open(output_dir / f"transformer_{antibiotic}_explanation.json", 'w') as f:
                    json.dump(explanation.__dict__, f, indent=2, default=str)
                
                print(f"     💾 Saved: {output_dir / f'transformer_{antibiotic}_explanation.json'}")
                
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
        
        # Test token importance summary
        if test_models:
            first_antibiotic = test_models[0]['antibiotic']
            print(f"\n📊 Testing token importance summary for {first_antibiotic}...")
            
            try:
                sample_sequences = [
                    "ATCGATCGATCGATCG",
                    "GCTAGCTAGCTAGCTA",
                    "CCCCGGGGAAAATTTT"
                ]
                
                summary = explainer.get_token_importance_summary(first_antibiotic, sample_sequences)
                
                print(f"  ✅ Token summary generated!")
                print(f"     - Total sequences: {summary['total_sequences']}")
                print(f"     - Unique tokens: {summary['unique_tokens']}")
                print(f"     - Top 5 tokens:")
                
                top_tokens = list(summary['top_tokens'].items())[:5]
                for i, (token, stats) in enumerate(top_tokens):
                    print(f"       {i+1}. {token}: {stats['mean_importance']:.4f}")
                    
            except Exception as e:
                print(f"  ❌ Token summary error: {str(e)}")
        
    except Exception as e:
        print(f"❌ DNABERT explainer error: {str(e)}")

def generate_summary_report(xgb_models, transformer_models):
    """Generate summary report of available models."""
    print("\n📋 Generating Summary Report...")
    
    report = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'xgboost_models': {
            'total': len(xgb_models),
            'antibiotics': [m['antibiotic'] for m in xgb_models],
            'total_size_mb': sum(m['size_mb'] for m in xgb_models),
            'models': xgb_models
        },
        'transformer_models': {
            'total': len(transformer_models),
            'antibiotics': [m['antibiotic'] for m in transformer_models],
            'total_size_mb': sum(m['size_mb'] for m in transformer_models),
            'models': transformer_models
        },
        'summary': {
            'total_models': len(xgb_models) + len(transformer_models),
            'total_size_mb': sum(m['size_mb'] for m in xgb_models) + sum(m['size_mb'] for m in transformer_models),
            'shap_ready': True
        }
    }
    
    # Save report
    output_dir = Path(__file__).parent / "data_cache"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "model_inventory_report.json", 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Report saved: {output_dir / 'model_inventory_report.json'}")
    
    # Print summary
    print(f"\n📊 SUMMARY REPORT")
    print("=" * 50)
    print(f"XGBoost Models: {len(xgb_models)} ({sum(m['size_mb'] for m in xgb_models):.1f} MB total)")
    print(f"DNABERT Models: {len(transformer_models)} ({sum(m['size_mb'] for m in transformer_models):.1f} MB total)")
    print(f"Total Models: {len(xgb_models) + len(transformer_models)}")
    print(f"Total Size: {sum(m['size_mb'] for m in xgb_models) + sum(m['size_mb'] for m in transformer_models):.1f} MB")
    print("=" * 50)
    
    if xgb_models:
        print(f"XGBoost Antibiotics: {', '.join([m['antibiotic'] for m in xgb_models[:5]])}")
        if len(xgb_models) > 5:
            print(f"                    ... and {len(xgb_models) - 5} more")
    
    if transformer_models:
        print(f"DNABERT Antibiotics: {', '.join([m['antibiotic'] for m in transformer_models[:5]])}")
        if len(transformer_models) > 5:
            print(f"                    ... and {len(transformer_models) - 5} more")

def main():
    """Main function to test SHAP with existing models."""
    print("🚀 Testing SHAP with Current Trained Models")
    print("=" * 60)
    
    # Check model directories
    models_dirs = check_model_directories()
    
    if not models_dirs:
        print("\n❌ No model directories found!")
        print("🔍 Please ensure you have trained models first.")
        print("💡 Use training scripts to generate models.")
        return
    
    # Use first found directory
    models_dir = models_dirs[0]
    print(f"\n📂 Using models directory: {models_dir}")
    
    # Check for models
    xgb_models = check_xgboost_models(models_dir)
    transformer_models = check_transformer_models(models_dir)
    
    # Test SHAP explanations
    if xgb_models:
        test_xgboost_explanations(xgb_models, models_dir)
    
    if transformer_models:
        test_transformer_explanations(transformer_models, models_dir)
    
    # Generate summary
    generate_summary_report(xgb_models, transformer_models)
    
    print(f"\n🎉 SHAP Testing Complete!")
    print(f"📁 Check explanations in: {Path(__file__).parent / 'data_cache' / 'shap_explanations'}")
    print(f"📋 Model inventory: {Path(__file__).parent / 'data_cache' / 'model_inventory_report.json'}")
    
    if not xgb_models and not transformer_models:
        print(f"\n⚠️  No trained models found!")
        print(f"🔧 To train models:")
        print(f"   1. XGBoost: python -m models.xgboost_trainer")
        print(f"   2. DNABERT: python -m models.transformer_trainer")

if __name__ == "__main__":
    main()
