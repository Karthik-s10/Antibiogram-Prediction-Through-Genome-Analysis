"""
Prediction API endpoints for antibiotic resistance prediction.
Handles genome uploads and returns antibiogram predictions.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
import logging
from typing import Dict, List, Optional
import numpy as np
import os
import glob

from preprocessing.kmer_processor import KmerProcessor
from preprocessing.dnabert_processor import DNABERTProcessor
from models.xgboost_trainer import XGBoostTrainer
from services.qdrant_service import QdrantService
from services.storage_service import StorageService
from config import settings
import json

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize services
qdrant_service = QdrantService()
storage_service = StorageService()


def generate_mock_prediction(fasta_content: str, filename: str) -> Dict:
    """
    Generate mock/demo prediction data when no trained models exist.
    This helps users test the system before training their own models.
    """
    import random
    
    # Calculate basic stats from FASTA
    sequence = ''.join([line.strip() for line in fasta_content.split('\n') if not line.startswith('>')])
    seq_length = len(sequence)
    gc_content = round((sequence.count('G') + sequence.count('C')) / seq_length * 100, 2) if seq_length > 0 else 0
    
    # Common antibiotics with mock predictions
    antibiotics = [
        "Amoxicillin", "Ampicillin", "Azithromycin", "Ceftriaxone", 
        "Ciprofloxacin", "Doxycycline", "Gentamicin", "Levofloxacin",
        "Meropenem", "Penicillin", "Rifampin", "Streptomycin",
        "Tetracycline", "Trimethoprim", "Vancomycin"
    ]
    
    predictions = {}
    for antibiotic in antibiotics:
        # Generate random but realistic predictions
        resistant_prob = random.uniform(0.1, 0.9)
        susceptible_prob = 1.0 - resistant_prob
        
        predictions[antibiotic] = {
            "prediction": "Resistant" if resistant_prob > 0.5 else "Susceptible",
            "confidence": {
                "Resistant": round(resistant_prob, 3),
                "Susceptible": round(susceptible_prob, 3)
            }
        }
    
    # Generate mock similar genomes
    mock_species = ["Escherichia coli", "Klebsiella pneumoniae", "Staphylococcus aureus", 
                    "Pseudomonas aeruginosa", "Enterococcus faecalis"]
    
    similar_genomes = []
    for i, species in enumerate(mock_species[:3]):
        similar_genomes.append({
            "genome_id": f"MOCK_{i+1:03d}",
            "species": species,
            "similarity_score": round(random.uniform(0.65, 0.95), 3)
        })
    
    return {
        "status": "success",
        "is_mock_data": True,
        "warning": "⚠️ MOCK/DEMO DATA - No trained models found. Please train a model for actual predictions.",
        "filename": filename,
        "predictions": predictions,
        "analysis_summary": {
            "sequence_length": seq_length,
            "gc_content": gc_content,
            "unique_kmers_found": random.randint(5000, 15000),
            "model_used": "Mock Demo Model (Not Real)",
            "n_antibiotics": len(antibiotics),
            "similar_genomes": similar_genomes
        }
    }


def find_best_model() -> Optional[Dict]:
    """
    Find the most recent trained model (XGBoost or DNABERT).
    
    Returns:
        Dictionary with 'model_path', 'model_type', and 'metadata' or None
    """
    try:
        models = storage_service.list_models()
        
        if not models:
            # Fallback: look for any .pkl files
            model_files = glob.glob(os.path.join(settings.model_storage_path, "*/*.pkl"))
            if model_files:
                latest_model = max(model_files, key=os.path.getmtime)
                # Try to determine model type from metadata
                model_dir = os.path.dirname(latest_model)
                metadata_path = os.path.join(model_dir, os.path.basename(latest_model).replace('.pkl', '_metadata.json'))
                model_type = 'xgboost'  # Default
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                            model_type = metadata.get('model_type', 'xgboost')
                    except:
                        pass
                return {
                    'model_path': latest_model,
                    'model_type': model_type,
                    'metadata': {}
                }
            return None
        
        # Sort by modification time (most recent first)
        model_dirs = []
        for model in models:
            model_dir = model.get('model_dir', '')
            if model_dir and os.path.exists(model_dir):
                # Find .pkl file in directory
                pkl_files = glob.glob(os.path.join(model_dir, "*.pkl"))
                if pkl_files:
                    model_path = pkl_files[0]
                    mtime = os.path.getmtime(model_path)
                    metadata = model.get('metadata', {})
                    model_type = metadata.get('model_type', 'xgboost')
                    model_dirs.append({
                        'model_path': model_path,
                        'model_type': model_type,
                        'metadata': metadata,
                        'mtime': mtime
                    })
        
        if not model_dirs:
            return None
        
        # Return most recent model
        latest = max(model_dirs, key=lambda x: x['mtime'])
        return {
            'model_path': latest['model_path'],
            'model_type': latest['model_type'],
            'metadata': latest['metadata']
        }
        
    except Exception as e:
        logger.error(f"Error finding model: {e}")
        return None


@router.post("/")
async def predict_resistance(
    genome_file: UploadFile = File(..., description="Bacterial genome FASTA file")
):
    """
    Predict antibiotic resistance from a genome sequence.
    
    This endpoint:
    1. Extracts k-mers from the uploaded genome
    2. Searches for similar genomes in the training database (via Qdrant)
    3. Loads the appropriate trained model
    4. Predicts resistance for all antibiotics
    5. Returns predictions with similarity information
    
    Args:
        genome_file: FASTA format genome file
    
    Returns:
        Antibiogram predictions with confidence scores and similar genomes
    """
    # Validate file format
    if not genome_file.filename.endswith(('.fasta', '.fa', '.fna')):
        raise HTTPException(
            status_code=400,
            detail="Genome file must be in FASTA format (.fasta, .fa, or .fna)"
        )
    
    try:
        # Step 1: Read FASTA content
        logger.info(f"Processing genome file: {genome_file.filename}")
        content = await genome_file.read()
        fasta_content = content.decode('utf-8')
        
        # Step 2: Find available trained model
        logger.info("Finding trained model...")
        model_info = find_best_model()
        
        if not model_info:
            # Return mock/demo data instead of error
            logger.warning("No trained models found. Returning mock demo data.")
            return generate_mock_prediction(fasta_content, genome_file.filename)
        
        model_path = model_info['model_path']
        model_type = model_info['model_type']
        model_metadata = model_info.get('metadata', {})
        
        logger.info(f"Using {model_type} model: {model_path}")
        
        # Step 3: Load the trained model
        logger.info(f"Loading {model_type} model...")
        trainer = None
        is_transformer = model_type in ['transformer', 'transformer_dnabert', 'dnabert']
        
        try:
            if is_transformer:
                from models.transformer_trainer import DNABERTTrainer
                trainer = DNABERTTrainer.load_models(model_path)
                logger.info("✅ Loaded DNABERT Transformer model")
            else:
                trainer = XGBoostTrainer.load_models(model_path)
                logger.info("✅ Loaded XGBoost model")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load {model_type} model: {str(e)}"
            )
        
        # Step 4: Extract features from uploaded genome
        if is_transformer:
            # For DNABERT: Extract genes from FASTA
            logger.info("Extracting gene sequences from FASTA for DNABERT...")
            dnabert_processor = DNABERTProcessor(k=settings.kmer_size_dnabert, max_length=512)
            gene_sequences = dnabert_processor.extract_genes_from_fasta(fasta_content)
            
            if not gene_sequences or len(gene_sequences) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No valid gene sequences found in genome. Check FASTA format and sequence quality."
                )
            
            logger.info(f"Extracted {len(gene_sequences)} gene sequences")
            
            # For similarity search: Extract k-mers to build feature vector
            kmer_processor = KmerProcessor(k=settings.kmer_size_dnabert)
            kmer_counts = kmer_processor.extract_kmers_from_fasta(fasta_content)
            
            # Build feature vector for similarity search (use k=6 features)
            # We need to get feature names from training - use a generic approach
            # For similarity search, we'll use the k-mer counts directly
            feature_vector = None  # Will be built for similarity search
        else:
            # For XGBoost: Extract k-mers
            logger.info("Extracting k-mers from uploaded genome...")
            kmer_processor = KmerProcessor(k=settings.kmer_size_xgboost)
            
            # Get k-mer counts
            kmer_counts = kmer_processor.extract_kmers_from_fasta(fasta_content)
            
            if not kmer_counts:
                raise HTTPException(
                    status_code=400,
                    detail="No valid k-mers found in genome. Check FASTA format and sequence quality."
                )
            
            logger.info(f"Extracted {len(kmer_counts)} unique k-mers")
            
            # Convert to feature vector matching training data
            feature_vector = kmer_processor.kmer_counts_to_feature_vector(
                kmer_counts,
                trainer.feature_names
            )
        
        # Step 5: SIMILARITY SEARCH (MANDATORY for Transformer, Optional for XGBoost)
        similar_genomes = []
        similarity_search_successful = False
        
        if is_transformer:
            # For Transformer: Similarity search is MANDATORY
            logger.info("🔍 SIMILARITY SEARCH REQUIRED for Transformer model...")
            
            if not qdrant_service.client:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Qdrant vector database is required for Transformer predictions. "
                        "Please configure Qdrant (local or cloud) to enable similarity search. "
                        "Transformer models rely on similarity search for explainability and validation."
                    )
                )
            
            try:
                # Build feature vector from k-mers for similarity search
                # For Transformer models, similarity search uses k-mer feature vectors
                # that are aligned and embedded using PCA (same as training)
                if kmer_counts:
                    # Convert k-mer counts to a feature vector
                    # We need to create a vector that can be embedded consistently
                    # Since we don't have the exact feature names from training,
                    # we'll use all k-mers and let PCA handle dimensionality
                    
                    # Create feature vector from k-mer counts (normalized frequencies)
                    all_kmers = sorted(kmer_counts.keys())  # Sort for consistency
                    kmer_freqs = np.array([kmer_counts[k] for k in all_kmers], dtype=np.float32)
                    
                    # Normalize to frequencies (sum to 1)
                    total = kmer_freqs.sum()
                    if total > 0:
                        kmer_freqs = kmer_freqs / total
                    else:
                        raise ValueError("No valid k-mer counts found")
                    
                    # Generate embedding using same method as training (PCA reduction to 768 dims)
                    from jobs.training_job import _generate_embeddings_from_features
                    feature_vector_2d = kmer_freqs.reshape(1, -1)  # Shape: (1, n_kmers)
                    query_embedding = _generate_embeddings_from_features(feature_vector_2d, target_dim=768)
                    query_embedding = query_embedding[0]  # Get single embedding vector (768,)
                    
                    logger.info(f"Generated query embedding of dimension {len(query_embedding)} for similarity search")
                    
                    similar_genomes = qdrant_service.search_similar_genomes(
                        query_embedding,
                        top_k=5
                    )
                    similarity_search_successful = True
                    logger.info(f"✅ Found {len(similar_genomes)} similar genomes (REQUIRED for Transformer)")
                    
                    if len(similar_genomes) == 0:
                        logger.warning("⚠️  No similar genomes found in database. Predictions may be less reliable.")
                    else:
                        # Log similarity scores for debugging
                        for i, similar in enumerate(similar_genomes[:3]):
                            logger.info(f"  Similar genome {i+1}: {similar.get('genome_id', 'unknown')} "
                                      f"(similarity: {similar.get('score', 0):.3f})")
                else:
                    raise ValueError("Could not extract k-mers for similarity search")
                    
            except Exception as e:
                logger.error(f"Similarity search failed for Transformer: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"Similarity search failed (REQUIRED for Transformer): {str(e)}. "
                        "Transformer models require similarity search for explainability. "
                        "Please ensure Qdrant is properly configured and contains training data embeddings."
                    )
                )
        else:
            # For XGBoost: Similarity search is optional but recommended
            try:
                if qdrant_service.client:
                    logger.info("Searching for similar genomes in database...")
                    # Generate embedding using same method as training (PCA reduction to 768 dims)
                    from jobs.training_job import _generate_embeddings_from_features
                    # Reshape feature vector to 2D array (1 genome × n_features)
                    feature_vector_2d = feature_vector.reshape(1, -1)
                    query_embedding = _generate_embeddings_from_features(feature_vector_2d, target_dim=768)
                    query_embedding = query_embedding[0]  # Get single embedding vector
                    
                    similar_genomes = qdrant_service.search_similar_genomes(
                        query_embedding,
                        top_k=5
                    )
                    similarity_search_successful = True
                    logger.info(f"Found {len(similar_genomes)} similar genomes")
            except Exception as e:
                logger.warning(f"Similarity search failed (non-critical for XGBoost): {e}")
                # Continue without similarity info for XGBoost
        
        # Step 6: Make predictions
        logger.info(f"Making resistance predictions using {model_type} model...")
        
        if is_transformer:
            # Use DNABERT prediction method
            predictions_dict = trainer.predict_genome(gene_sequences)
            
            # For probabilities, we need to get them from the model
            # DNABERT doesn't have a predict_proba method, so we'll estimate from logits
            predictions_proba = {}
            try:
                import torch
                import torch.nn.functional as F
                
                for antibiotic, model in trainer.models.items():
                    # Tokenize genes
                    encodings = trainer._tokenize_sequences(gene_sequences)
                    input_ids = encodings['input_ids'].to(trainer.device)
                    attention_mask = encodings['attention_mask'].to(trainer.device)
                    
                    model.eval()
                    with torch.no_grad():
                        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                        # Get probabilities from logits
                        probs = F.softmax(outputs.logits, dim=-1)
                        # Average probabilities across all genes
                        avg_probs = probs.mean(dim=0).cpu().numpy()
                        predictions_proba[antibiotic] = avg_probs
            except ImportError:
                logger.warning("PyTorch not available for probability calculation. Using default probabilities.")
                # Fallback: use uniform probabilities
                for antibiotic in trainer.antibiotic_names:
                    predictions_proba[antibiotic] = np.array([0.33, 0.33, 0.34])
        else:
            # Use XGBoost prediction methods
            predictions_dict = trainer.predict(feature_vector)
            predictions_proba = trainer.predict_proba(feature_vector)
        
        # Step 7: Format predictions
        prediction_results = []
        resistance_map = {0: 'S', 1: 'I', 2: 'R'}
        
        for antibiotic in trainer.antibiotic_names:
            if antibiotic in predictions_dict:
                pred_class = predictions_dict[antibiotic]
                pred_label = resistance_map.get(pred_class, 'Unknown')
                
                # Get confidence (probability of predicted class)
                if antibiotic in predictions_proba:
                    proba = predictions_proba[antibiotic]
                    if isinstance(proba, np.ndarray) and len(proba) == 3:
                        confidence = float(proba[pred_class])
                        class_probs = {
                            "S": float(proba[0]),
                            "I": float(proba[1]),
                            "R": float(proba[2])
                        }
                    else:
                        confidence = 0.5
                        class_probs = {"S": 0.33, "I": 0.33, "R": 0.34}
                else:
                    confidence = 0.5
                    class_probs = {"S": 0.33, "I": 0.33, "R": 0.34}
                
                # For Transformer: Enhance confidence based on similarity search
                if is_transformer and similar_genomes:
                    # If similar genomes have matching resistance profiles, increase confidence
                    similar_resistance_matches = 0
                    for similar in similar_genomes[:3]:  # Check top 3
                        metadata = similar.get('metadata', {})
                        resistance_profile = metadata.get('resistance_profile', {})
                        if antibiotic in resistance_profile:
                            similar_phenotype = resistance_profile[antibiotic]
                            if (similar_phenotype == 'R' and pred_label == 'R') or \
                               (similar_phenotype == 'S' and pred_label == 'S') or \
                               (similar_phenotype == 'I' and pred_label == 'I'):
                                similar_resistance_matches += 1
                    
                    # Boost confidence if similar genomes agree
                    if similar_resistance_matches >= 2:
                        confidence = min(0.95, confidence + 0.1)
                        logger.info(f"Boosted confidence for {antibiotic} based on similar genomes")
                
                prediction_results.append({
                    "antibiotic": antibiotic,
                    "prediction": pred_label,
                    "confidence": confidence,
                    "class_probabilities": class_probs
                })
        
        # Step 8: Calculate sequence statistics
        sequence = fasta_content.replace('\n', '').replace('>', '')
        sequence_clean = ''.join(c for c in sequence if c in 'ACGTN')
        
        gc_content = (sequence_clean.count('G') + sequence_clean.count('C')) / len(sequence_clean) * 100 if sequence_clean else 0
        
        # Step 9: Format similar genomes with resistance profile information
        formatted_similar_genomes = []
        for g in similar_genomes:
            metadata = g.get('metadata', {})
            resistance_profile = metadata.get('resistance_profile', {})
            
            formatted_similar_genomes.append({
                "genome_id": g.get('genome_id', 'unknown'),
                "similarity_score": round(g.get('score', 0), 3),
                "species": metadata.get('species', 'Unknown'),
                "resistance_profile": resistance_profile,  # Include resistance profile
                "model_type": metadata.get('model_type', 'unknown')
            })
        
        # Step 10: Return comprehensive results
        response = {
            "status": "success",
            "genome_name": genome_file.filename,
            "model_type": model_type,
            "predictions": prediction_results,
            "analysis_summary": {
                "sequence_length": len(sequence_clean),
                "gc_content": round(gc_content, 1),
                "unique_kmers_found": len(kmer_counts) if kmer_counts else 0,
                "n_genes": len(gene_sequences) if is_transformer else None,
                "model_used": os.path.basename(model_path),
                "n_antibiotics": len(prediction_results),
                "similarity_search_performed": similarity_search_successful,
                "similar_genomes": formatted_similar_genomes,
                "similarity_search_required": is_transformer  # Indicate if it was required
            }
        }
        
        # Add warning if Transformer model but no similar genomes found
        if is_transformer and len(similar_genomes) == 0:
            response["warning"] = (
                "⚠️  WARNING: No similar genomes found in database. "
                "Transformer predictions may be less reliable without similarity context."
            )
        
        logger.info(f"Prediction complete: {len(prediction_results)} antibiotics predicted")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing prediction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/models")
async def list_available_models():
    """
    List all available trained models.
    
    Returns:
        List of trained models with metadata
    """
    # TODO: Query from model registry
    return {
        "models": [],
        "message": "Model listing will be implemented after training pipeline"
    }

