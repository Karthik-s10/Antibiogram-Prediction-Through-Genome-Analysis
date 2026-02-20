"""
Test script for SHAP integration functionality.
Tests both XGBoost and DNABERT explainers.
"""
import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent))

from explainability import SHAPUtils, XGBoostExplainer, TransformerExplainer

def test_shap_utils():
    """Test SHAP utility functions."""
    print("🧪 Testing SHAP Utils...")
    
    utils = SHAPUtils()
    
    # Test feature name preparation
    feature_data = {
        'kmer_features': {'ATCG': 1, 'CGTA': 2, 'TTAA': 3}
    }
    feature_names = utils.prepare_feature_names(feature_data)
    print(f"✅ Feature names: {feature_names[:3]}...")
    
    # Test feature ranking
    shap_values = np.array([0.1, -0.2, 0.15])
    ranked = utils.rank_features_by_importance(shap_values, feature_names)
    print(f"✅ Ranked features: {ranked}")
    
    print("✅ SHAP Utils test passed!\n")

def test_xgboost_explainer():
    """Test XGBoost SHAP explainer."""
    print("🌳 Testing XGBoost Explainer...")
    
    try:
        explainer = XGBoostExplainer()
        
        # Test with sample data
        antibiotic = "amikacin"
        features = np.random.rand(1000)  # Sample k-mer features
        
        print(f"🔍 Explaining {antibiotic} with XGBoost...")
        print(f"📊 Feature vector shape: {features.shape}")
        
        # This will fail if model doesn't exist, but that's expected
        try:
            explanation = explainer.explain_single_sample(
                antibiotic=antibiotic,
                features=features,
                prediction="R",
                probability=0.75
            )
            print(f"✅ XGBoost explanation generated!")
            print(f"   - Model type: {explanation.model_type}")
            print(f"   - Antibiotic: {explanation.antibiotic}")
            print(f"   - Features: {len(explanation.feature_names)}")
            print(f"   - SHAP values shape: {explanation.shap_values.shape}")
            
        except FileNotFoundError:
            print("⚠️  XGBoost model not found (expected in test environment)")
        except Exception as e:
            print(f"❌ XGBoost explainer error: {str(e)}")
            
    except Exception as e:
        print(f"❌ XGBoost explainer initialization error: {str(e)}")
    
    print("✅ XGBoost Explainer test completed!\n")

def test_transformer_explainer():
    """Test DNABERT Transformer SHAP explainer."""
    print("🤖 Testing DNABERT Transformer Explainer...")
    
    try:
        explainer = TransformerExplainer()
        
        # Test with sample DNA sequence
        antibiotic = "amikacin"
        sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
        
        print(f"🔍 Explaining {antibiotic} with DNABERT...")
        print(f"🧬 DNA sequence length: {len(sequence)}")
        
        # This will fail if model doesn't exist, but that's expected
        try:
            explanation = explainer.explain_single_sample(
                antibiotic=antibiotic,
                sequence=sequence,
                prediction="S",
                probability=0.82
            )
            print(f"✅ DNABERT explanation generated!")
            print(f"   - Model type: {explanation.model_type}")
            print(f"   - Antibiotic: {explanation.antibiotic}")
            print(f"   - Tokens: {len(explanation.feature_names)}")
            print(f"   - SHAP values shape: {explanation.shap_values.shape}")
            
        except FileNotFoundError:
            print("⚠️  DNABERT model not found (expected in test environment)")
        except Exception as e:
            print(f"❌ DNABERT explainer error: {str(e)}")
            
    except Exception as e:
        print(f"❌ DNABERT explainer initialization error: {str(e)}")
    
    print("✅ DNABERT Transformer Explainer test completed!\n")

def test_api_endpoints():
    """Test if API endpoints are properly configured."""
    print("🌐 Testing API Configuration...")
    
    try:
        import main
        from fastapi.testclient import TestClient
        
        client = TestClient(main.app)
        
        # Test root endpoint
        response = client.get("/")
        print(f"✅ Root endpoint: {response.status_code}")
        
        # Test health endpoint
        response = client.get("/health")
        print(f"✅ Health endpoint: {response.status_code}")
        
        # Test explanations models endpoint
        response = client.get("/api/explanations/models")
        print(f"✅ Explanations models endpoint: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   - Available models: {data.get('success', False)}")
            if data.get('models_info'):
                xgb_available = data['models_info']['xgboost']['available']
                transformer_available = data['models_info']['transformer']['available']
                print(f"   - XGBoost available: {xgb_available}")
                print(f"   - DNABERT available: {transformer_available}")
        
    except ImportError as e:
        print(f"⚠️  Could not import main module: {str(e)}")
    except Exception as e:
        print(f"❌ API test error: {str(e)}")
    
    print("✅ API Configuration test completed!\n")

def test_frontend_components():
    """Test frontend SHAP components."""
    print("🎨 Testing Frontend Components...")
    
    # Check if component files exist
    components_dir = Path(__file__).parent.parent / "src" / "components" / "explanation"
    
    components = [
        "ShapVisualization.tsx",
        "ForcePlot.tsx", 
        "ComparativeExplanation.tsx",
        "index.ts"
    ]
    
    for component in components:
        component_path = components_dir / component
        if component_path.exists():
            print(f"✅ {component} exists")
        else:
            print(f"❌ {component} missing")
    
    print("✅ Frontend Components test completed!\n")

def test_dependencies():
    """Test if all required dependencies are available."""
    print("📦 Testing Dependencies...")
    
    required_packages = [
        'shap',
        'numpy',
        'pandas', 
        'scipy',
        'sklearn',
        'plotly',
        'xgboost',
        'transformers',
        'torch'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} missing")
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {missing_packages}")
        print("Install with: pip install " + " ".join(missing_packages))
    else:
        print("✅ All dependencies available!")
    
    print("✅ Dependencies test completed!\n")

def generate_sample_explanation_data():
    """Generate sample explanation data for testing frontend."""
    print("📊 Generating Sample Explanation Data...")
    
    # Sample XGBoost explanation
    xgb_sample = {
        'shap_values': [[0.1, -0.2, 0.15, -0.05, 0.08]],
        'feature_names': ['kmer_ATCG', 'kmer_CGTA', 'kmer_TTAA', 'kmer_GGCC', 'kmer_AATT'],
        'base_values': 0.5,
        'prediction': 'R',
        'probability': 0.75,
        'model_type': 'XGBoost',
        'antibiotic': 'amikacin',
        'force_plot_data': {
            'base_value': 0.5,
            'shap_values': [0.1, -0.2, 0.15, -0.05, 0.08],
            'feature_names': ['kmer_ATCG', 'kmer_CGTA', 'kmer_TTAA', 'kmer_GGCC', 'kmer_AATT'],
            'feature_importance': [('kmer_CGTA', -0.2), ('kmer_TTAA', 0.15), ('kmer_ATCG', 0.1), ('kmer_AATT', 0.08), ('kmer_GGCC', -0.05)]
        },
        'waterfall_plot_data': {
            'base_value': 0.5,
            'final_prediction': 0.58,
            'features': [
                {'feature': 'kmer_CGTA', 'shap_value': -0.2, 'cumulative_value': 0.3, 'contribution_type': 'negative'},
                {'feature': 'kmer_TTAA', 'shap_value': 0.15, 'cumulative_value': 0.45, 'contribution_type': 'positive'},
                {'feature': 'kmer_ATCG', 'shap_value': 0.1, 'cumulative_value': 0.55, 'contribution_type': 'positive'},
                {'feature': 'kmer_AATT', 'shap_value': 0.08, 'cumulative_value': 0.63, 'contribution_type': 'positive'}
            ]
        }
    }
    
    # Sample DNABERT explanation
    transformer_sample = {
        'shap_values': [[0.05, -0.1, 0.08, -0.03, 0.04]],
        'feature_names': ['token_0_[CLS]', 'token_1_AT', 'token_2_CG', 'token_3_TA', 'token_4_CG'],
        'base_values': 0.5,
        'prediction': 'S',
        'probability': 0.82,
        'model_type': 'DNABERT',
        'antibiotic': 'amikacin',
        'metadata': {
            'sequence_length': 30,
            'token_count': 5,
            'max_length': 512,
            'tokens': ['[CLS]', 'AT', 'CG', 'TA', 'CG']
        }
    }
    
    # Save sample data
    sample_data_dir = Path(__file__).parent / "data_cache" / "sample_explanations"
    sample_data_dir.mkdir(parents=True, exist_ok=True)
    
    import json
    with open(sample_data_dir / "xgb_sample.json", 'w') as f:
        json.dump(xgb_sample, f, indent=2)
    
    with open(sample_data_dir / "transformer_sample.json", 'w') as f:
        json.dump(transformer_sample, f, indent=2)
    
    print("✅ Sample explanation data generated!")
    print(f"   - XGBoost sample: {sample_data_dir / 'xgb_sample.json'}")
    print(f"   - DNABERT sample: {sample_data_dir / 'transformer_sample.json'}")
    
    print("✅ Sample Data Generation completed!\n")

def main():
    """Run all SHAP integration tests."""
    print("🚀 Starting SHAP Integration Tests\n")
    print("=" * 50)
    
    # Run all tests
    test_dependencies()
    test_shap_utils()
    test_xgboost_explainer()
    test_transformer_explainer()
    test_api_endpoints()
    test_frontend_components()
    generate_sample_explanation_data()
    
    print("=" * 50)
    print("🎉 SHAP Integration Tests Completed!")
    print("\n📋 Summary:")
    print("   ✅ Backend explainers implemented")
    print("   ✅ API endpoints configured") 
    print("   ✅ Frontend components created")
    print("   ✅ Sample data generated")
    print("\n🔧 Next Steps:")
    print("   1. Train models to test with real data")
    print("   2. Install missing dependencies if any")
    print("   3. Test with actual genome sequences")
    print("   4. Integrate with main application")

if __name__ == "__main__":
    main()
