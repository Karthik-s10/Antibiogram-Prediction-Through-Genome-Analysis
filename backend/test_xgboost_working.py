"""
Simple test to verify XGBoost SHAP integration works.
Tests with your actual multi-antibiotic model from job f0849bdd.
"""
import sys
import numpy as np
from pathlib import Path

# Add to path
sys.path.append(str(Path(__file__).parent))

def test_xgboost_shap():
    """Test XGBoost SHAP with your actual model."""
    print("🌳 Testing XGBoost SHAP Integration...")
    
    # Load model
    model_path = Path("trained_models/xgboost_f0849bdd.pkl")
    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        return False
    
    print(f"📦 Loading model: {model_path}")
    import pickle
    with open(model_path, 'rb') as f:
        model_dict = pickle.load(f)
    
    print(f"✅ Model loaded! Type: {type(model_dict)}")
    
    # Check structure
    if 'models' in model_dict:
        models = model_dict['models']
        print(f"📋 Found {len(models)} antibiotic models")
        
        # Test with first available antibiotic
        first_antibiotic = list(models.keys())[0]
        model = models[first_antibiotic]
        
        print(f"🔑 Testing {first_antibiotic} model...")
        print(f"   - Model type: {type(model)}")
        
        # Test SHAP
        try:
            import shap
            explainer = shap.TreeExplainer(model)
            print(f"   ✅ SHAP explainer created!")
            
            # Generate sample features
            n_features = 1000
            sample_features = np.random.rand(n_features)
            
            # Generate SHAP values
            shap_values = explainer.shap_values(sample_features.reshape(1, -1))
            print(f"   ✅ SHAP values computed! Shape: {shap_values.shape}")
            
            # Get prediction
            prediction_proba = model.predict_proba(sample_features.reshape(1, -1))[0]
            prediction_class = np.argmax(prediction_proba)
            classes = ['S', 'I', 'R']
            prediction = classes[prediction_class]
            confidence = float(prediction_proba[prediction_class])
            
            print(f"   🎯 Prediction: {prediction} ({confidence:.3f})")
            print(f"   📈 Base value: {explainer.expected_value}")
            
            print(f"   ✅ XGBoost SHAP Integration: SUCCESS!")
            return True
            
        except Exception as e:
            print(f"   ❌ SHAP error: {str(e)}")
            return False
    else:
        print(f"❌ No 'models' key found in model dictionary")
        return False

def main():
    """Main function."""
    print("🚀 XGBoost SHAP Integration Test")
    print("Testing with your actual model from job f0849bdd")
    print("=" * 50)
    
    success = test_xgboost_shap()
    
    if success:
        print(f"\n🎉 XGBoost SHAP Integration: WORKING!")
        print(f"   ✅ Model loaded from job f0849bdd")
        print(f"   ✅ SHAP explainer created")
        print(f"   ✅ Feature importance computed")
        print(f"   ✅ Ready for frontend integration")
        print(f"\n📁 Next Steps:")
        print(f"   1. Test API: http://localhost:8000/api/explanations/models")
        print(f"   2. Use ShapVisualization component")
        print(f"   3. Test with real genome sequences")
    else:
        print(f"\n❌ XGBoost SHAP Integration: FAILED")
        print(f"   - Check model file structure")
        print(f"   - Verify SHAP dependencies")

if __name__ == "__main__":
    main()
