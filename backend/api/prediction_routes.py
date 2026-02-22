"""
Prediction API endpoints for antibiotic resistance prediction.
Handles genome uploads and returns antibiogram predictions.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Form  # type: ignore
import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np  # type: ignore
import os
import glob
import time
from pathlib import Path
import subprocess
import tempfile

from preprocessing.kmer_processor import KmerProcessor  # type: ignore
from preprocessing.dnabert_processor import DNABERTProcessor  # type: ignore
from models.xgboost_trainer import XGBoostTrainer  # type: ignore
from services.qdrant_service import QdrantService  # type: ignore
from services.storage_service import StorageService  # type: ignore
from services.embedding_service import EmbeddingService  # type: ignore
from config import settings  # type: ignore
import json

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize services
qdrant_service = QdrantService()
storage_service = StorageService()
# Global DNABERT embedding service for Transformer similarity search.
# This avoids re-loading the DNABERT backbone on every prediction request
# and lets the service auto-detect and reuse GPU if available.
embedding_service = EmbeddingService()


# Cache for XGBoost explainability data (per model path)
_xgb_explain_cache: Dict[str, Dict] = {}


def _load_xgb_explain_data(model_path: str) -> Optional[Dict]:
    """Load XGBoost explainability JSON for a given model path.

    Returns a dict with per-antibiotic top_features, or None if unavailable.
    """
    if model_path in _xgb_explain_cache:
        return _xgb_explain_cache[model_path]

    try:
        p = Path(model_path)
        explain_path = p.with_name(p.stem + "_explainability.json")
        if not explain_path.exists():
            logger.warning(f"XGBoost explainability file not found for model: {explain_path}")
            _xgb_explain_cache[model_path] = None  # type: ignore[assignment]
            return None

        with open(explain_path, "r") as f:
            data = json.load(f) or {}
        if not isinstance(data, dict):
            logger.warning(f"Unexpected explainability JSON structure at {explain_path}")
            data = {}

        _xgb_explain_cache[model_path] = data
        return data
    except Exception as e:
        logger.warning(f"Failed to load XGBoost explainability for {model_path}: {e}")
        _xgb_explain_cache[model_path] = None  # type: ignore[assignment]
        return None


def _compute_xgb_markers_for_sample(
    model_path: str,
    kmer_counts: Dict[str, int],
    top_k: int = 5,
) -> Dict[str, List[Dict]]:
    """Compute XGBoost k-mer markers per antibiotic for a single genome.

    Uses the per-antibiotic top_features from the explainability JSON and
    intersects them with the k-mers actually present in the uploaded genome.
    """
    if not kmer_counts:
        return {}

    explain_data = _load_xgb_explain_data(model_path)
    if not explain_data:
        return {}

    antibiotics_data = explain_data.get("antibiotics", {})
    if not isinstance(antibiotics_data, dict):
        return {}

    markers_by_ab: Dict[str, List[Dict]] = {}

    for ab_name, ab_info in antibiotics_data.items():
        if not isinstance(ab_info, dict):
            continue
        top_features = ab_info.get("top_features") or []
        if not isinstance(top_features, list):
            continue

        hits: List[Dict] = []
        for feat in top_features:
            if not isinstance(feat, dict):
                continue
            kmer = str(feat.get("feature", "")).strip()
            try:
                importance = float(feat.get("importance", 0.0) or 0.0)
            except (TypeError, ValueError):
                importance = 0.0

            if not kmer or importance <= 0.0:
                continue

            count = int(kmer_counts.get(kmer, 0))
            if count <= 0:
                continue

            hits.append(
                {
                    "kmer": kmer,
                    "importance": importance,
                    "count": count,
                }
            )

        if not hits:
            continue

        # Sort by importance and select top_k markers
        hits.sort(key=lambda m: float(m.get("importance", 0.0)), reverse=True)
        # Add `type: ignore` since Pyre has trouble understanding slicing on dict views
        selected = hits[:top_k]  # type: ignore

        total_imp = sum(float(m.get("importance", 0.0)) for m in selected) or 0.0
        if total_imp > 0.0:
            for m in selected:
                m["normalized_importance"] = float(m.get("importance", 0.0)) / total_imp
        else:
            for m in selected:
                m["normalized_importance"] = 0.0

        markers_by_ab[ab_name] = selected

    return markers_by_ab


def _compute_transformer_markers_for_sample(
    trainer,
    gene_sequences: List[str],
    max_genes_per_ab: int = 3,
    blast_mode_override: Optional[str] = None,
) -> Dict[str, List[Dict]]:
    """Compute Level-A Transformer gene markers (genes predicted R/I).

    Uses DNABERTTrainer.gene_level_predictions, which stores per-gene
    predicted classes (0=S, 1=I, 2=R) for each antibiotic after
    predict_genome_with_proba has been called.

    When BLAST is enabled (settings.blast_mode = 'ncbi' or 'local'), this
    will also attach best BLAST hit information for a small number of top
    R/I genes per antibiotic (Level B naming).
    """
    markers_by_ab: Dict[str, List[Dict]] = {}

    if not gene_sequences:
        return {}

    gene_map = getattr(trainer, "gene_level_predictions", {}) or {}
    if not isinstance(gene_map, dict):
        return {}

    # Optional per-gene probability matrix per antibiotic: shape (n_genes, 3)
    prob_map = getattr(trainer, "gene_level_probabilities", {}) or {}

    resistance_map = {0: "S", 1: "I", 2: "R"}

    for ab_name, gene_preds in gene_map.items():
        try:
            arr = np.array(gene_preds, dtype=int)  # type: ignore
        except Exception:
            continue

        candidates: List[Dict] = []
        probs_arr = None
        try:
            probs_arr = prob_map.get(ab_name)  # type: ignore
        except Exception:
            probs_arr = None

        for idx, cls_idx in enumerate(arr):
            if cls_idx in (1, 2):
                # Use probability of the predicted class as a per-gene importance score
                importance = 0.0
                try:
                    if isinstance(probs_arr, np.ndarray) and probs_arr.ndim == 2:  # type: ignore
                        if 0 <= idx < probs_arr.shape[0] and 0 <= cls_idx < probs_arr.shape[1]:  # type: ignore
                            importance = float(probs_arr[idx, cls_idx])  # type: ignore
                except Exception:
                    importance = 0.0

                candidates.append(
                    {
                        "gene_index": int(idx),
                        "class_index": int(cls_idx),
                        "class_label": resistance_map.get(int(cls_idx), "Unknown"),
                        "importance": importance,
                    }
                )

        if not candidates:
            continue

        # Prioritize by importance (descending), then Resistant (2) over Intermediate (1), then by gene index
        for m in candidates:
            if "importance" not in m:
                m["importance"] = 0.0
        candidates.sort(
            key=lambda m: (
                -float(m.get("importance", 0.0)),
                0 if m["class_index"] == 2 else 1,
                m["gene_index"],
            )
        )
        # Add `type: ignore` since Pyre has trouble understanding slicing on dict views
        selected = candidates[:max_genes_per_ab]  # type: ignore

        # Normalize importance scores within this antibiotic, similar to XGBoost markers
        total_imp = sum(float(m.get("importance", 0.0)) for m in selected) or 0.0
        if total_imp > 0.0:
            for m in selected:
                m["normalized_importance"] = float(m.get("importance", 0.0)) / total_imp
        else:
            for m in selected:
                m["normalized_importance"] = 0.0

        markers_by_ab[ab_name] = selected

    # If BLAST is disabled, return plain Level-A markers
    mode = blast_mode_override if blast_mode_override is not None else getattr(settings, "blast_mode", "off")
    if mode not in ("ncbi", "local"):
        return markers_by_ab

    # Level B: annotate selected markers with best BLAST hit when possible
    try:
        _load_blast_cache()
    except Exception:
        pass

    for ab_name, markers in markers_by_ab.items():
        for m in markers:
            idx = m.get("gene_index")
            if idx is None or not isinstance(idx, int):
                continue
            if idx < 0 or idx >= len(gene_sequences):
                continue

            seq = gene_sequences[idx]  # type: ignore
            if not seq:
                continue

            cache_key = f"gene:{seq}"
            hits = _blast_cache.get(cache_key) if "_blast_cache" in globals() else None

            if hits is None:
                if mode == "ncbi":
                    hits = _run_blast_ncbi(seq, max_hits=1)
                elif mode == "local":
                    hits = _run_blast_local(seq, max_hits=1)
                else:
                    hits = []

                try:
                    _blast_cache[cache_key] = hits or []
                    _save_blast_cache()
                except Exception:
                    pass

            if hits:
                best = hits[0]
                try:
                    m["best_hit_id"] = best.get("hit_id")
                    # Both NCBI and local helpers set "title" as the descriptive field
                    m["best_hit_title"] = best.get("title")
                    m["best_hit_identity"] = best.get("identity")
                except Exception:
                    continue

    return markers_by_ab


def _adjust_confidence_with_similarity(
    antibiotic: str,
    pred_label: str,
    confidence: float,
    class_probs: Dict[str, float],
    similar_genomes: List[Dict[str, Any]],
) -> Tuple[float, Dict[str, float]]:
    if not similar_genomes:
        return confidence, class_probs

    agree_weight = 0.0
    disagree_weight = 0.0

    for similar in similar_genomes[:5]:  # type: ignore
        metadata = similar.get("metadata", {}) or {}
        resistance_profile = metadata.get("resistance_profile", {}) or {}
        if not isinstance(resistance_profile, dict):
            continue
        if antibiotic not in resistance_profile:
            continue
        similar_phenotype = resistance_profile[antibiotic]
        if similar_phenotype not in ("S", "I", "R"):
            continue
        try:
            score = float(similar.get("score", 0.0) or 0.0)
        except (TypeError, ValueError):
            score = 0.0
        if score <= 0.0:
            continue
        if similar_phenotype == pred_label:
            agree_weight += float(score)  # type: ignore
        else:
            disagree_weight += float(score)  # type: ignore

    total_weight = float(agree_weight) + float(disagree_weight)  # type: ignore
    if total_weight <= 0.0:
        return confidence, class_probs

    agreement_ratio = float(agree_weight) / float(total_weight)  # type: ignore
    disagreement_ratio = float(disagree_weight) / float(total_weight)  # type: ignore

    new_conf = confidence
    new_probs = dict(class_probs)

    if agreement_ratio >= 0.7 and agree_weight >= 1.0:
        if agreement_ratio >= 0.9:
            delta = 0.3
        else:
            delta = 0.2
        new_conf = min(0.99, confidence + delta)

        prob_vec = [
            float(new_probs.get("S", 0.0)),
            float(new_probs.get("I", 0.0)),
            float(new_probs.get("R", 0.0)),
        ]
        label_index = {"S": 0, "I": 1, "R": 2}.get(pred_label)
        if label_index is not None:
            beta = 0.7
            one_hot = [0.0, 0.0, 0.0]
            one_hot[label_index] = 1.0
            blended = [beta * p + (1.0 - beta) * h for p, h in zip(prob_vec, one_hot)]
            total = sum(blended)
            if total > 0.0:
                blended = [p / total for p in blended]
            new_probs = {
                "S": blended[0],
                "I": blended[1],
                "R": blended[2],
            }
    elif disagreement_ratio >= 0.7 and disagree_weight >= 1.0:
        new_conf = max(0.05, confidence - 0.2)

    return new_conf, new_probs


def _extract_query_hints_from_fasta(fasta_content: str, filename: str) -> Dict[str, Optional[str]]:
    """Extract simple species / accession hints from FASTA header and filename.

    This is heuristic and best-effort. It does NOT affect core predictions,
    only how we re-rank similarity search results.
    """
    header_line: Optional[str] = None
    for line in fasta_content.split('\n'):
        line = line.strip()
        if line.startswith('>'):
            header_line = line
            break

    species_hint: Optional[str] = None
    accession_hint: Optional[str] = None

    if header_line:
        header_text = header_line.lstrip('>').strip()  # type: ignore
        # Overall accession-like token (first token)
        tokens = header_text.split()
        if tokens:
            accession_hint = tokens[0]

        # For headers like ENA|AP011121|AP011121.1 Acetobacter pasteurianus ...
        # take the segment after the last '|' and then the first two words
        parts = header_text.split('|')
        tail = parts[-1].strip() if parts else header_text
        tail_tokens = tail.split()
        if len(tail_tokens) >= 3:
            # tail_tokens[0] is often accession; [1] [2] are Genus species
            genus = tail_tokens[1]
            species = tail_tokens[2]
            species_hint = f"{genus} {species}"

    # Filename stem as an additional weak hint
    try:
        name_hint = Path(filename).stem
    except Exception:
        name_hint = None

    return {
        'species_hint': species_hint,
        'accession_hint': accession_hint,
        'name_hint': name_hint,
    }


def _rerank_similar_genomes(
    similar_genomes: List[Dict[str, Any]],
    hints: Dict[str, Optional[str]],
) -> List[Dict[str, Any]]:
    """Re-rank similarity results using simple metadata hints.

    Boost genomes whose metadata (species / names / genome_id) matches hints
    extracted from the FASTA header or filename.
    """
    if not similar_genomes or not hints:
        return similar_genomes

    species_hint = (hints.get('species_hint') or '').lower()  # type: ignore
    accession_hint = (hints.get('accession_hint') or '').lower()  # type: ignore
    name_hint = (hints.get('name_hint') or '').lower()  # type: ignore

    if not (species_hint or accession_hint or name_hint):
        return similar_genomes

    reranked: List[Tuple[float, Dict[str, Any]]] = []

    for g in similar_genomes:
        base_score = 0.0
        try:
            base_score = float(g.get('score', 0.0) or 0.0)
        except (TypeError, ValueError):
            base_score = 0.0

        boost = 1.0

        metadata = g.get('metadata', {}) or {}
        meta_text_parts: List[str] = []
        for key in ('species', 'organism_name', 'genome_name', 'strain'):
            val = metadata.get(key)  # type: ignore
            if isinstance(val, str):
                meta_text_parts.append(val)
        genome_id_val = g.get('genome_id') or metadata.get('genome_id')  # type: ignore
        if isinstance(genome_id_val, str):
            meta_text_parts.append(genome_id_val)

        meta_text = ' '.join(meta_text_parts).lower()

        if species_hint and species_hint in meta_text:
            boost += 0.25
        if accession_hint and accession_hint in meta_text:
            boost += 0.15
        if name_hint and name_hint in meta_text:
            boost += 0.10

        new_score = base_score * boost
        # Update score so downstream weighting (e.g. confidence adjust) uses it
        g['score'] = new_score
        reranked.append((new_score, g))

    # Sort by boosted score descending
    reranked.sort(key=lambda t: t[0], reverse=True)
    return [g for _, g in reranked]


def generate_mock_prediction(fasta_content: str, filename: str) -> Dict:
    """
    Generate mock/demo prediction data when no trained models exist.
    This helps users test the system before training their own models.
    """
    import random
    
    # Calculate basic stats from FASTA
    sequence = ''.join([line.strip() for line in fasta_content.split('\n') if not line.startswith('>')])
    seq_length = len(sequence)
    gc_content = round((sequence.count('G') + sequence.count('C')) / seq_length * 100, 2) if seq_length > 0 else 0  # type: ignore
    
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
                "Resistant": round(resistant_prob, 3),  # type: ignore
                "Susceptible": round(susceptible_prob, 3)  # type: ignore
            }
        }
    
    # Generate mock similar genomes
    mock_species = ["Escherichia coli", "Klebsiella pneumoniae", "Staphylococcus aureus", 
                    "Pseudomonas aeruginosa", "Enterococcus faecalis"]
    
    similar_genomes = []
    for i, species in enumerate(mock_species[:3]):  # type: ignore
        similar_genomes.append({
            "genome_id": f"MOCK_{i+1:03d}",
            "species": species,
            "similarity_score": round(random.uniform(0.65, 0.95), 3)  # type: ignore
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


def find_best_model(preferred_types: Optional[List[str]] = None) -> Optional[Dict]:
    """Find the most recent trained model.

    If preferred_types is provided, only models whose metadata.model_type is in
    that list are considered. Otherwise, all models are candidates.

    Returns:
        Dictionary with 'model_path', 'model_type', and 'metadata' or None
    """
    try:
        # Collect candidate models from both storage_service directories and
        # root-level .pkl files in the model storage path. This ensures that
        # user-trained models saved as transformer_*.pkl are considered and
        # typically preferred over built-in demo models.

        model_candidates = []

        # 1) Models registered via StorageService (subdirectories under model_storage_path)
        models = storage_service.list_models()
        for model in models:
            model_dir = model.get('model_dir', '')
            model_name = model.get('model_name', '')

            if not model_dir or not os.path.exists(model_dir):
                continue

            # Find .pkl files in this directory
            pkl_files = glob.glob(os.path.join(model_dir, "*.pkl"))
            for pkl_path in pkl_files:
                try:
                    mtime = os.path.getmtime(pkl_path)
                except OSError:
                    continue

                metadata = model.get('metadata', {}) or {}
                model_type = metadata.get('model_type', 'xgboost')

                model_candidates.append({
                    'model_path': pkl_path,
                    'model_type': model_type,
                    'metadata': metadata,
                    'mtime': mtime,
                    'source': f"dir:{model_name}",
                })

        # 2) Root-level .pkl files directly under model_storage_path
        root_pkl_files = glob.glob(os.path.join(settings.model_storage_path, "*.pkl"))
        for pkl_path in root_pkl_files:
            base = os.path.basename(pkl_path)
            base_name, _ = os.path.splitext(base)

            metadata_path = os.path.join(settings.model_storage_path, f"{base_name}_metadata.json")
            metadata = {}
            model_type = 'xgboost'
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f) or {}
                    model_type = metadata.get('model_type', model_type)
                except Exception:
                    # If metadata is unreadable, fall back to default type
                    metadata = {}

            try:
                mtime = os.path.getmtime(pkl_path)
            except OSError:
                continue

            model_candidates.append({
                'model_path': pkl_path,
                'model_type': model_type,
                'metadata': metadata,
                'mtime': mtime,
                'source': 'root',
            })

        # If we still have no candidates, there are no saved models
        if not model_candidates:
            return None

        # Optionally filter by preferred model types
        if preferred_types:
            filtered = [m for m in model_candidates if m['model_type'] in preferred_types]  # type: ignore
            if not filtered:
                return None
            model_candidates = filtered

        # Prefer the most recently modified model among remaining candidates
        latest = max(model_candidates, key=lambda x: x['mtime'])

        logger.info(
            f"Selected model for prediction: {latest['model_path']} "
            f"(type={latest['model_type']}, source={latest.get('source', 'unknown')})"
        )

        return {
            'model_path': latest['model_path'],
            'model_type': latest['model_type'],
            'metadata': latest.get('metadata', {}),
        }

    except Exception as e:
        logger.error(f"Error finding model: {e}")
        return None


def validate_xgboost_model(trainer: XGBoostTrainer, metadata: Dict, model_path: str) -> None:
    """Sanity-check an XGBoost model against saved metadata and feature info.

    Ensures that the number of features and, when available, the k-mer size
    used during training match the current prediction configuration.
    """
    try:
        expected_features = metadata.get("n_features")
        actual_features = len(getattr(trainer, "feature_names", []) or [])

        if expected_features is not None and actual_features != expected_features:
            logger.error(
                "XGBoost model feature count mismatch: expected %d features from metadata, got %d from model",
                expected_features,
                actual_features,
            )
            raise HTTPException(
                status_code=500,
                detail=(
                    "Incompatible XGBoost model: feature count does not match training metadata. "
                    "Please retrain the model or ensure you are using the correct model file."
                ),
            )

        model_name = metadata.get("model_name") or Path(model_path).stem
        features_path = os.path.join(settings.model_storage_path, f"{model_name}_features.json")

        if os.path.exists(features_path):
            try:
                with open(features_path, "r") as f:
                    info = json.load(f) or {}
            except Exception as e:
                logger.warning(
                    f"Failed to read XGBoost feature info at {features_path}: {e}"
                )
            else:
                k_saved = info.get("k")
                n_features_saved = info.get("n_features")

                if k_saved is not None and k_saved != settings.kmer_size_xgboost:
                    logger.error(
                        "XGBoost k-mer size mismatch: model was trained with k=%d but current setting is k=%d",
                        k_saved,
                        settings.kmer_size_xgboost,
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=(
                            "Incompatible XGBoost model: k-mer size used during training does not match "
                            "the current server configuration. Please align k-mer size or retrain the model."
                        ),
                    )

                if n_features_saved is not None and n_features_saved != actual_features:
                    logger.error(
                        "XGBoost feature info mismatch: feature_info reports %d features but model has %d",
                        n_features_saved,
                        actual_features,
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=(
                            "Incompatible XGBoost model: feature information does not match the loaded model. "
                            "Please retrain or regenerate the model and feature info."
                        ),
                    )

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"XGBoost model sanity checks failed with non-fatal error: {e}")


@router.post("/")
async def predict_resistance(
    genome_file: UploadFile = File(..., description="Bacterial genome FASTA file"),
    prediction_model_mode: str = Form(
        "auto",
        alias="model_mode",
        description=(
            "Which trained model to use: 'auto' (latest), 'xgboost', 'transformer', or 'both' "
            "(run both XGBoost and Transformer and return combined results)."
        ),
    ),
    enable_blast: bool = Form(
        False,
        description=(
            "Enable BLAST-based naming for Transformer gene markers (may add latency). "
            "When false, only Level-A Transformer markers are computed."
        ),
    ),
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

        # Extract simple species/accession hints from FASTA header + filename
        query_hints = _extract_query_hints_from_fasta(fasta_content, genome_file.filename)

        model_mode = (prediction_model_mode or "auto").lower()

        # Determine effective BLAST mode for this request. When enable_blast is
        # false, we always disable BLAST regardless of global settings.
        effective_blast_mode: Optional[str] = "off"
        if enable_blast:
            effective_blast_mode = getattr(settings, "blast_mode", "off")
            # If the user toggled "Use BLAST" in the UI but the server config
            # is "off" (the default), upgrade it to "ncbi" so the feature works.
            if effective_blast_mode == "off":
                effective_blast_mode = "ncbi"

        # Special ensemble mode: run both XGBoost and Transformer (if available)
        if model_mode == "both":
            logger.info("Model mode = both: attempting to load best XGBoost and Transformer models")

            xgb_info = find_best_model(preferred_types=["xgboost"])
            tr_info = find_best_model(preferred_types=["transformer", "transformer_dnabert", "dnabert"])

            if not xgb_info and not tr_info:
                logger.warning("No XGBoost or Transformer models found. Returning mock demo data.")
                return generate_mock_prediction(fasta_content, genome_file.filename)

            # Prepare containers
            similar_genomes = []
            similarity_search_successful = False
            ensemble_details: Dict[str, Any] = {
                "mode": "both",
                "xgboost_model": xgb_info,
                "transformer_model": tr_info,
                "per_antibiotic": {},
            }

            # 1) Transformer predictions + similarity search (main model)
            tr_predictions_dict: Dict[str, int] = {}
            tr_predictions_proba: Dict[str, np.ndarray] = {}
            gene_sequences: Optional[List[str]] = None

            if tr_info:
                try:
                    from models.transformer_trainer import DNABERTTrainer  # type: ignore

                    tr_model_path = tr_info["model_path"]
                    logger.info(f"Loading Transformer model for ensemble: {tr_model_path}")
                    tr_trainer = DNABERTTrainer.load_models(tr_model_path)

                    # Extract genes from FASTA
                    logger.info("[ensemble] Extracting gene sequences from FASTA for DNABERT...")
                    dnabert_processor = DNABERTProcessor(k=settings.kmer_size_dnabert, max_length=512)
                    gene_sequences = dnabert_processor.extract_genes_from_fasta(fasta_content)

                    if not gene_sequences or len(gene_sequences) == 0:
                        logger.warning(
                            "[ensemble] No valid gene sequences found in genome for Transformer part. "
                            "Transformer predictions will be skipped."
                        )
                        gene_sequences = None
                    else:
                        logger.info(f"[ensemble] Extracted {len(gene_sequences)} gene sequences")

                        # Similarity search (mandatory for Transformer)
                        if not qdrant_service.client:
                            logger.warning(
                                "Qdrant not available; skipping similarity search for Transformer in ensemble mode."
                            )
                        else:
                            try:
                                query_embedding = np.array(
                                    embedding_service.embed_fasta(fasta_content),
                                    dtype=np.float32,
                                )
                                logger.info(
                                    f"[ensemble] Generated DNABERT query embedding of dimension {len(query_embedding)}"
                                )
                                similar_genomes = qdrant_service.search_similar_genomes(
                                    query_embedding,
                                    top_k=5,
                                )
                                # Use header/filename hints to nudge ordering
                                similar_genomes = _rerank_similar_genomes(similar_genomes, query_hints)
                                similarity_search_successful = True
                                logger.info(
                                    f"[ensemble] ✅ Found {len(similar_genomes)} similar genomes for Transformer"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"[ensemble] Similarity search failed for Transformer (non-fatal in ensemble): {e}"
                                )

                        if gene_sequences is not None:
                            t_start_pred = time.time()
                            try:
                                tr_predictions_dict, tr_predictions_proba = tr_trainer.predict_genome_with_proba(
                                    gene_sequences
                                )
                            except ImportError:
                                logger.warning(
                                    "PyTorch not fully available for Transformer probabilities in ensemble. "
                                    "Using genome-level predictions only with default probabilities."
                                )
                                tr_predictions_dict = tr_trainer.predict_genome(gene_sequences)
                                tr_predictions_proba = {
                                    a: np.array([0.33, 0.33, 0.34])
                                    for a in tr_trainer.antibiotic_names
                                }

                            t_pred = time.time() - t_start_pred
                            logger.info(
                                f"[ensemble] DNABERT predictions computed for {len(gene_sequences)} genes "
                                f"in {t_pred/60:.2f} min"
                            )
                except Exception as e:
                    logger.error(f"[ensemble] Failed to run Transformer part: {e}")

            # 2) XGBoost predictions (baseline model)
            xgb_predictions_dict: Dict[str, int] = {}
            xgb_predictions_proba: Dict[str, np.ndarray] = {}
            kmer_counts = None
            xgb_markers_by_ab: Dict[str, List[Dict]] = {}

            if xgb_info:
                try:
                    xgb_model_path = xgb_info["model_path"]
                    logger.info(f"Loading XGBoost model for ensemble: {xgb_model_path}")
                    xgb_trainer = XGBoostTrainer.load_models(xgb_model_path)
                    validate_xgboost_model(xgb_trainer, xgb_info.get("metadata", {}), xgb_model_path)

                    logger.info("[ensemble] Extracting k-mers from uploaded genome for XGBoost...")
                    kmer_processor = KmerProcessor(k=settings.kmer_size_xgboost)
                    kmer_counts = kmer_processor.extract_kmers_from_fasta(fasta_content)

                    if not kmer_counts:
                        logger.warning(
                            "[ensemble] No valid k-mers found in genome for XGBoost part. "
                            "XGBoost predictions will be skipped."
                        )
                    else:
                        logger.info(f"[ensemble] Extracted {len(kmer_counts)} unique k-mers")
                        feature_vector = kmer_processor.kmer_counts_to_feature_vector(
                            kmer_counts,
                            xgb_trainer.feature_names,
                        )
                        xgb_predictions_dict = xgb_trainer.predict(feature_vector)
                        xgb_predictions_proba = xgb_trainer.predict_proba(feature_vector)
                except Exception as e:
                    logger.error(f"[ensemble] Failed to run XGBoost part: {e}")

            # 2.5) Compute XGBoost markers if possible (after k-mer extraction)
            if xgb_info and kmer_counts:
                try:
                    xgb_markers_by_ab = _compute_xgb_markers_for_sample(xgb_model_path, kmer_counts)
                except Exception as e:
                    logger.warning(f"[ensemble] Failed to compute XGBoost markers: {e}")

            # 3) Combine per-antibiotic results
            resistance_map = {0: 'S', 1: 'I', 2: 'R'}
            final_predictions = []

            antibiotics = set()
            if xgb_predictions_dict:
                antibiotics.update(xgb_predictions_dict.keys())
            if tr_predictions_dict:
                antibiotics.update(tr_predictions_dict.keys())

            # Compute Level-A/B Transformer markers (genes predicted R/I, with optional BLAST naming) if available
            tr_markers_by_ab: Dict[str, List[Dict]] = {}
            try:
                if tr_info and gene_sequences is not None and tr_predictions_dict:
                    tr_markers_by_ab = _compute_transformer_markers_for_sample(
                        tr_trainer,
                        gene_sequences,
                        blast_mode_override=effective_blast_mode,
                    )
            except Exception as e:
                logger.warning(f"[ensemble] Failed to compute Transformer gene markers: {e}")

            for antibiotic in sorted(antibiotics):
                # Transformer component
                tr_entry = None
                if antibiotic in tr_predictions_dict:  # type: ignore
                    tr_class = tr_predictions_dict[antibiotic]  # type: ignore
                    tr_label = resistance_map.get(tr_class, 'Unknown')
                    tr_proba = None
                    if isinstance(tr_predictions_proba, dict) and antibiotic in tr_predictions_proba:
                        tr_proba = tr_predictions_proba[antibiotic]
                    if tr_proba is not None and isinstance(tr_proba, np.ndarray) and len(tr_proba) == 3:  # type: ignore
                        tr_conf = float(tr_proba[tr_class])  # type: ignore
                        tr_probs_dict = {
                            'S': float(tr_proba[0]),
                            'I': float(tr_proba[1]),
                            'R': float(tr_proba[2]),
                        }
                    else:
                        tr_conf = 0.5
                        tr_probs_dict = {'S': 0.33, 'I': 0.33, 'R': 0.34}
                    if similar_genomes:
                        tr_conf, tr_probs_dict = _adjust_confidence_with_similarity(
                            antibiotic,
                            tr_label,
                            tr_conf,
                            tr_probs_dict,
                            similar_genomes,
                        )
                    tr_entry = {
                        'prediction': tr_label,
                        'confidence': tr_conf,
                        'class_probabilities': tr_probs_dict,
                    }

                # XGBoost component
                xgb_entry = None
                if antibiotic in xgb_predictions_dict:  # type: ignore
                    xgb_class = xgb_predictions_dict[antibiotic]  # type: ignore
                    xgb_label = resistance_map.get(xgb_class, 'Unknown')
                    xgb_proba = None
                    if isinstance(xgb_predictions_proba, dict) and antibiotic in xgb_predictions_proba:
                        xgb_proba = xgb_predictions_proba[antibiotic]
                    if xgb_proba is not None and isinstance(xgb_proba, np.ndarray) and len(xgb_proba) == 3:  # type: ignore
                        xgb_conf = float(xgb_proba[xgb_class])  # type: ignore
                        xgb_probs_dict = {
                            'S': float(xgb_proba[0]),
                            'I': float(xgb_proba[1]),
                            'R': float(xgb_proba[2]),
                        }
                    else:
                        xgb_conf = 0.5
                        xgb_probs_dict = {'S': 0.33, 'I': 0.33, 'R': 0.34}
                    xgb_entry = {
                        'prediction': xgb_label,
                        'confidence': xgb_conf,
                        'class_probabilities': xgb_probs_dict,
                    }

                # Choose final prediction: Transformer is main model when available
                if tr_entry is not None:
                    final_label = tr_entry['prediction']
                    final_conf = tr_entry['confidence']
                    final_probs = tr_entry['class_probabilities']
                elif xgb_entry is not None:
                    final_label = xgb_entry['prediction']
                    final_conf = xgb_entry['confidence']
                    final_probs = xgb_entry['class_probabilities']
                else:
                    # Should not happen, but guard anyway
                    continue

                xgb_markers = xgb_markers_by_ab.get(antibiotic, [])
                tr_markers = tr_markers_by_ab.get(antibiotic, [])

                final_predictions.append({
                    'antibiotic': antibiotic,
                    'prediction': final_label,
                    'confidence': final_conf,
                    'class_probabilities': final_probs,
                    'xgboost_markers': xgb_markers,
                    'transformer_markers': tr_markers,
                })

                ensemble_details['per_antibiotic'][antibiotic] = {
                    'final': {
                        'prediction': final_label,
                        'confidence': final_conf,
                    },
                    'xgboost': xgb_entry,
                    'transformer': tr_entry,
                    'xgboost_markers': xgb_markers,
                    'transformer_markers': tr_markers,
                }

            # Step 8/9: sequence statistics & response formatting (shared with single-model path)
            sequence = fasta_content.replace('\n', '').replace('>', '')
            sequence_clean = ''.join(c for c in sequence if c in 'ACGTN')
            gc_content = (
                (sequence_clean.count('G') + sequence_clean.count('C')) / len(sequence_clean) * 100
                if sequence_clean
                else 0
            )

            formatted_similar_genomes = []
            for g in similar_genomes:
                metadata = g.get('metadata', {})
                resistance_profile = metadata.get('resistance_profile', {})
                formatted_similar_genomes.append({
                    'genome_id': g.get('genome_id', 'unknown'),
                    'similarity_score': round(g.get('score', 0), 3),
                    'species': metadata.get('species', 'Unknown'),
                    'organism_name': metadata.get('organism_name') or metadata.get('genome_name'),
                    'strain': metadata.get('strain'),
                    'resistance_profile': resistance_profile,
                    'model_type': metadata.get('model_type', 'unknown'),
                })

            response = {
                'status': 'success',
                'genome_name': genome_file.filename,
                'model_type': 'ensemble',
                'models_used': {
                    'xgboost': xgb_info,
                    'transformer': tr_info,
                },
                'predictions': final_predictions,
                'analysis_summary': {
                    'sequence_length': len(sequence_clean),
                    'gc_content': round(float(gc_content), 1),  # type: ignore
                    'unique_kmers_found': len(kmer_counts) if kmer_counts else 0,  # type: ignore
                    'n_genes': len(gene_sequences) if gene_sequences is not None else None,  # type: ignore
                    'model_used': 'Ensemble (XGBoost + Transformer)' if xgb_info and tr_info
                    else 'Transformer only' if tr_info
                    else 'XGBoost only',
                    'n_antibiotics': len(final_predictions),
                    'similarity_search_performed': similarity_search_successful,
                    'similar_genomes': formatted_similar_genomes,
                    'similarity_search_required': bool(tr_info),
                    'ensemble_details': ensemble_details,
                },
            }

            logger.info(f"[ensemble] Prediction complete: {len(final_predictions)} antibiotics predicted")
            return response

        # ===== Single-model modes: auto / xgboost / transformer =====

        # Step 2: Find available trained model
        logger.info("Finding trained model...")

        preferred_types: Optional[List[str]] = None
        if model_mode == 'xgboost':
            preferred_types = ['xgboost']
        elif model_mode == 'transformer':
            preferred_types = ['transformer', 'transformer_dnabert', 'dnabert']

        model_info = find_best_model(preferred_types=preferred_types)

        if not model_info:
            # Return mock/demo data instead of error
            logger.warning("No trained models found for requested mode. Returning mock demo data.")
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
                from models.transformer_trainer import DNABERTTrainer  # type: ignore
                trainer = DNABERTTrainer.load_models(model_path)
                logger.info("✅ Loaded DNABERT Transformer model")
            else:
                trainer = XGBoostTrainer.load_models(model_path)
                validate_xgboost_model(trainer, model_metadata, model_path)
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
                # Use DNABERT-based embeddings for similarity search so that
                # training genomes and query genomes share the same embedding base.
                # Reuse the global EmbeddingService instance (typically on GPU).
                query_embedding = np.array(embedding_service.embed_fasta(fasta_content), dtype=np.float32)

                logger.info(
                    f"Generated DNABERT query embedding of dimension {len(query_embedding)} for similarity search"
                )
                
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
                        logger.info(
                            f"  Similar genome {i+1}: {similar.get('genome_id', 'unknown')} "
                            f"(similarity: {similar.get('score', 0):.3f})"
                        )
                    
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
                    from jobs.training_job import _generate_embeddings_from_features  # type: ignore
                    # Reshape feature vector to 2D array (1 genome × n_features)
                    feature_vector_2d = feature_vector.reshape(1, -1)  # type: ignore
                    query_embedding = _generate_embeddings_from_features(feature_vector_2d, target_dim=768)
                    query_embedding = query_embedding[0]  # Get single embedding vector
                    
                    similar_genomes = qdrant_service.search_similar_genomes(
                        query_embedding,
                        top_k=5
                    )
                    # Re-rank using header/filename hints
                    similar_genomes = _rerank_similar_genomes(similar_genomes, query_hints)
                    similarity_search_successful = True
                    logger.info(f"Found {len(similar_genomes)} similar genomes")
            except Exception as e:
                logger.warning(f"Similarity search failed (non-critical for XGBoost): {e}")
                # Continue without similarity info for XGBoost
        
        # Step 6: Make predictions
        logger.info(f"Making resistance predictions using {model_type} model...")
        
        if is_transformer:
            t_start_pred = time.time()
            try:
                # Use optimized helper to compute genome-level predictions and
                # per-class probabilities in a single DNABERT pass per antibiotic.
                predictions_dict, predictions_proba = trainer.predict_genome_with_proba(gene_sequences)
            except ImportError:
                # Fallback: only genome-level predictions if torch/softmax not available
                logger.warning("PyTorch not fully available for probability calculation. "
                               "Using genome-level predictions only with default probabilities.")
                predictions_dict = trainer.predict_genome(gene_sequences)
                predictions_proba = {a: np.array([0.33, 0.33, 0.34]) for a in trainer.antibiotic_names}

            t_pred = time.time() - t_start_pred
            logger.info(
                f"DNABERT genome-level predictions and probabilities computed for "
                f"{len(gene_sequences)} genes in {t_pred/60:.2f} min"
            )
        else:
            # Use XGBoost prediction methods
            predictions_dict = trainer.predict(feature_vector)
            predictions_proba = trainer.predict_proba(feature_vector)
        
        # Compute markers for this sample
        xgb_markers_by_ab: Dict[str, List[Dict]] = {}
        tr_markers_by_ab: Dict[str, List[Dict]] = {}

        if not is_transformer:
            try:
                xgb_markers_by_ab = _compute_xgb_markers_for_sample(model_path, kmer_counts)
            except Exception as e:
                logger.warning(f"Failed to compute XGBoost markers for single-model prediction: {e}")
        else:
            try:
                tr_markers_by_ab = _compute_transformer_markers_for_sample(
                    trainer,
                    gene_sequences,
                    blast_mode_override=effective_blast_mode,
                )
            except Exception as e:
                logger.warning(f"Failed to compute Transformer gene markers for single-model prediction: {e}")
        
        # Step 7: Format predictions
        prediction_results = []
        resistance_map = {0: 'S', 1: 'I', 2: 'R'}
        
        for antibiotic in trainer.antibiotic_names:  # type: ignore
            if antibiotic in predictions_dict:  # type: ignore
                pred_class = predictions_dict[antibiotic]  # type: ignore
                pred_label = resistance_map.get(pred_class, 'Unknown')
                
                # Get confidence (probability of predicted class)
                if antibiotic in predictions_proba:  # type: ignore
                    proba = predictions_proba[antibiotic]  # type: ignore
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
                    confidence, class_probs = _adjust_confidence_with_similarity(
                        antibiotic,
                        pred_label,
                        confidence,
                        class_probs,
                        similar_genomes,
                    )
                
                xgb_markers = xgb_markers_by_ab.get(antibiotic, [])
                tr_markers = tr_markers_by_ab.get(antibiotic, [])

                prediction_results.append({
                    "antibiotic": antibiotic,
                    "prediction": pred_label,
                    "confidence": confidence,
                    "class_probabilities": class_probs,
                    "xgboost_markers": xgb_markers,
                    "transformer_markers": tr_markers,
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
                "gc_content": round(float(gc_content), 1),  # type: ignore
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


@router.get("/xgboost_explainability/{model_name}")
async def get_xgboost_explainability(model_name: str):
    """Return the XGBoost explainability report for a given model name.

    The report is generated during training and saved as a JSON file alongside
    the trained model. This endpoint simply reads and returns that JSON.
    """
    root_dir = settings.model_storage_path

    primary_path = os.path.join(root_dir, f"{model_name}_explainability.json")
    alt_path = os.path.join(root_dir, model_name, "model_explainability.json")

    explain_path = None
    if os.path.exists(primary_path):
        explain_path = primary_path
    elif os.path.exists(alt_path):
        explain_path = alt_path
    else:
        raise HTTPException(
            status_code=404,
            detail="Explainability report not found for requested model.",
        )

    try:
        with open(explain_path, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Failed to read XGBoost explainability report at {explain_path}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to read explainability report.",
        )


_blast_cache: Dict[str, List[Dict]] = {}
_blast_cache_loaded: bool = False
_blast_cache_path: str = os.path.join(settings.model_storage_path, "blast_kmer_cache.json")


def _load_blast_cache() -> None:
    global _blast_cache_loaded, _blast_cache
    if _blast_cache_loaded:
        return
    if os.path.exists(_blast_cache_path):
        try:
            with open(_blast_cache_path, "r") as f:
                data = json.load(f) or {}
                if isinstance(data, dict):
                    _blast_cache = data
        except Exception as e:
            logger.warning(f"Failed to load BLAST cache from {_blast_cache_path}: {e}")
            _blast_cache = {}
    _blast_cache_loaded = True


def _save_blast_cache() -> None:
    if not _blast_cache_loaded:
        return
    try:
        with open(_blast_cache_path, "w") as f:
            json.dump(_blast_cache, f)
    except Exception as e:
        logger.warning(f"Failed to save BLAST cache to {_blast_cache_path}: {e}")


def _run_blast_ncbi(kmer: str, max_hits: int = 1) -> List[Dict[str, Any]]:
    """Run BLAST against NCBI nt using Biopython (remote)."""
    try:
        from Bio.Blast import NCBIWWW, NCBIXML  # type: ignore
        import urllib.error
        import time
        try:
            from Bio import Entrez  # type: ignore
            email = getattr(settings, "ncbi_email", None)
            if email:
                Entrez.email = email
        except Exception:
            pass

        handle = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                handle = NCBIWWW.qblast("blastn", "nt", kmer, hitlist_size=max_hits)
                break
            except urllib.error.HTTPError as e:
                logger.warning(f"NCBI BLAST HTTP error on attempt {attempt+1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)  # 2s, 4s, 6s backoff
                else:
                    raise

        if handle is None:
            return []

        record = NCBIXML.read(handle)

        hits: List[Dict] = []
        for alignment in record.alignments[:max_hits]:
            if not alignment.hsps:
                continue
            hsp = alignment.hsps[0]
            identity = None
            try:
                if hsp.align_length:
                    identity = float(hsp.identities) / float(hsp.align_length)
            except Exception:
                identity = None

            hits.append(
                {
                    "hit_id": getattr(alignment, "hit_id", ""),
                    "title": getattr(alignment, "hit_def", ""),
                    "length": int(getattr(alignment, "length", 0)) if getattr(alignment, "length", None) else None,
                    "evalue": float(getattr(hsp, "expect", 0.0)) if getattr(hsp, "expect", None) else None,
                    "identity": identity,
                }
            )

        return hits
    except ImportError:
        logger.warning("Biopython not installed; NCBI BLAST integration is disabled.")
        return []
    except Exception as e:
        logger.warning(f"NCBI BLAST query failed for k-mer {kmer}: {e}")
        return []


def _run_blast_local(kmer: str, max_hits: int = 1) -> List[Dict[str, Any]]:
    """Run local BLAST+ (blastn) against a configured database."""
    db = settings.blast_local_db
    exe = settings.blast_local_exe or "blastn"
    if not db:
        logger.warning("Local BLAST requested but blast_local_db is not configured.")
        return []

    tmp_fasta = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".fasta", delete=False) as tmp:
            tmp.write(">query\n")
            tmp.write(kmer + "\n")
            tmp_fasta = tmp.name

        outfmt = "6 sseqid stitle length pident evalue"
        cmd = [
            exe,
            "-query",
            tmp_fasta,
            "-db",
            db,
            "-outfmt",
            outfmt,
            "-max_target_seqs",
            str(max_hits),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(
                "Local BLAST command failed (code %s): %s",
                result.returncode,
                result.stderr.strip(),
            )
            return []

        hits: List[Dict[str, Any]] = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            
            # parts is typing as list[str], ensure Pyre knows this explicitly
            hit_id: str = parts[0]
            title: str = parts[1]
            length_str: str = parts[2]
            pident_str: str = parts[3]
            evalue_str: str = parts[4]
            
            try:
                length = int(length_str)
            except ValueError:
                length = None
            try:
                pident = float(pident_str)
                identity = pident / 100.0
            except ValueError:
                identity = None
            try:
                evalue = float(evalue_str)
            except ValueError:
                evalue = None

            hits.append(
                {
                    "hit_id": hit_id,
                    "title": title,
                    "length": length,
                    "evalue": evalue,
                    "identity": identity,
                }
            )

        return hits
    except FileNotFoundError:
        logger.warning(
            "Local BLAST executable '%s' not found. Please install BLAST+ and ensure it is on PATH.",
            exe,
        )
        return []
    except Exception as e:
        logger.warning(f"Local BLAST query failed for k-mer {kmer}: {e}")
        return []
    finally:
        if tmp_fasta and os.path.exists(tmp_fasta):
            try:
                os.remove(tmp_fasta)
            except Exception:
                pass
                
    return []


def _run_blast_for_kmer(kmer: str, max_hits: int = 1) -> List[Dict[str, Any]]:
    """Config-driven BLAST with simple JSON cache.

    Respects settings.blast_mode:
      - "off":  return [] without querying any BLAST backend
      - "ncbi": use remote NCBI nt via Biopython (NCBIWWW)
      - "local": use local BLAST+ binary against settings.blast_local_db
    """
    _load_blast_cache()
    key = kmer

    if key in _blast_cache:
        return _blast_cache[key]

    mode = (settings.blast_mode or "off").lower()
    if mode == "off":
        logger.info("BLAST mode is 'off'; skipping BLAST for k-mer.")
        hits: List[Dict] = []
    elif mode == "local":
        hits = _run_blast_local(kmer, max_hits=max_hits)
    elif mode == "ncbi":
        hits = _run_blast_ncbi(kmer, max_hits=max_hits)
    else:
        logger.warning(f"Unknown BLAST mode '{settings.blast_mode}'. Treating as 'off'.")
        hits = []

    _blast_cache[key] = hits
    _save_blast_cache()
    return hits


@router.post("/xgboost_blast_kmers")
async def xgboost_blast_kmers(payload: Dict):
    """Run BLAST for a list of k-mers and return best hits per sequence.

    Request JSON body:
        {
          "kmers": ["ACGT...", ...],
          "max_hits": 1  # optional
        }
    """
    kmers = payload.get("kmers") or []
    max_hits = int(payload.get("max_hits", 1))

    if not isinstance(kmers, list) or not kmers:
        raise HTTPException(
            status_code=400,
            detail="'kmers' must be a non-empty list of sequences.",
        )

    results: Dict[str, List[Dict]] = {}
    for seq in kmers:
        if not isinstance(seq, str) or not seq:
            continue
        hits = _run_blast_for_kmer(seq, max_hits=max_hits)
        results[seq] = hits

    return {"kmers": results}

