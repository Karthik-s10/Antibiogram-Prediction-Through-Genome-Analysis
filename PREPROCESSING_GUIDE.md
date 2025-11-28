# Data Preprocessing Implementation Guide

## Overview

This implementation solves the **ID mismatch problem** between your phenotype and k-mer data files by using a "Rosetta Stone" mapping file to align the datasets.

## The Problem

- **Phenotype file** (`BVBRC_genome_amr.txt`): Uses PATRIC Genome IDs (e.g., `562.144628`)
- **K-mer file** (`SIGNIFICANT_DNA_KMERS_BACTERIA`): Uses GenBank Accession IDs (e.g., `GCA_000002515.1`)
- **Solution**: Use `BVBRC_genome.txt` to map between these ID formats

## Implementation Architecture

### 1. Data Preprocessor (`backend/preprocessing/data_preprocessor.py`)

The core preprocessing module that:
- Loads the ID mapping from `BVBRC_genome.txt`
- Maps PATRIC IDs to GenBank Accessions
- Creates aligned feature (X) and label (Y) matrices
- Uses caching to avoid reprocessing on subsequent runs

**Key Features:**
- ✅ Chunked file reading for large datasets
- ✅ Memory-efficient processing
- ✅ Automatic caching (saves hours on re-runs)
- ✅ Inner join alignment (only keeps matching genomes)
- ✅ Handles S/I/R encoding (0/1/2)

### 2. Training Integration

The preprocessor is integrated into the training pipeline:
- **`backend/jobs/training_job.py`**: Calls preprocessor before training
- **`backend/api/training_routes.py`**: Exposes training endpoints
- **`backend/main.py`**: FastAPI application

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Load ID Mapping (BVBRC_genome.txt)                       │
│    PATRIC ID → GenBank Accession                            │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 2. Load Phenotype Data (BVBRC_genome_amr.txt)               │
│    - Filter for Laboratory Method evidence                  │
│    - Map PATRIC IDs to GenBank Accessions                   │
│    - Encode S/I/R → 0/1/2                                    │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 3. Pivot to Label Matrix (Y)                                │
│    Rows: GenBank Accessions                                 │
│    Cols: Antibiotics                                         │
│    Values: 0/1/2 (S/I/R)                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 4. Load K-mer Data (SIGNIFICANT_DNA_KMERS_BACTERIA)         │
│    - Chunked reading for large files                        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 5. Pivot to Feature Matrix (X)                              │
│    Rows: GenBank Accessions                                 │
│    Cols: K-mer sequences                                    │
│    Values: K-mer probabilities                              │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 6. Align X and Y (Inner Join)                               │
│    Keep only genomes present in BOTH datasets               │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 7. Output: X_final, Y_final                                 │
│    Ready for model training!                                │
└─────────────────────────────────────────────────────────────┘
```

## File Structure

```
Antibiogram-Prediction-Through-Genome-Analysis/
├── BVBRC_genome.txt                    # ID mapping file
├── BVBRC_genome_amr.txt                # Phenotype data
├── DATA/
│   └── SIGNIFICANT_DNA_KMERS_BACTERIA  # K-mer data
├── backend/
│   ├── preprocessing/
│   │   └── data_preprocessor.py        # ✨ NEW: Core preprocessing
│   ├── jobs/
│   │   ├── job_manager.py              # Job tracking
│   │   └── training_job.py             # Training orchestration
│   ├── models/
│   │   ├── xgboost_trainer.py          # XGBoost training
│   │   └── transformer_trainer.py      # Transformer training
│   ├── api/
│   │   └── training_routes.py          # API endpoints
│   └── main.py                         # FastAPI app
├── data_cache/                         # ✨ NEW: Cached aligned data
├── test_preprocessing.py               # ✨ NEW: Test script
└── start_training_api.ps1              # ✨ NEW: API startup script
```

## Usage

### Option 1: Test Preprocessing Only

Run the test script to verify data preprocessing works:

```powershell
python test_preprocessing.py
```

This will:
1. Load and map the data
2. Create aligned X and Y matrices
3. Save to cache for future use
4. Display summary statistics

**Expected Output:**
```
Aligned Genomes: XXXX
Features (K-mers): XXXXXX
Labels (Antibiotics): XX
Antibiotics: ['amikacin', 'ampicillin', ...]
```

### Option 2: Start Training API

Start the FastAPI server:

```powershell
.\start_training_api.ps1
```

Then use the API to train models:

**Via API Documentation (Recommended):**
1. Open http://localhost:8000/docs
2. Use the `/api/training/train` endpoint
3. Provide file paths and model type

**Via cURL:**
```bash
curl -X POST "http://localhost:8000/api/training/train" \
  -H "Content-Type: application/json" \
  -d '{
    "phenotype_file": "BVBRC_genome_amr.txt",
    "kmer_file": "DATA/SIGNIFICANT_DNA_KMERS_BACTERIA",
    "rosetta_file": "BVBRC_genome.txt",
    "model_type": "parallel"
  }'
```

**Monitor Progress:**
```bash
curl "http://localhost:8000/api/training/status/{job_id}"
```

## Caching Mechanism

The preprocessor uses intelligent caching:

- **First run**: Processes all data (may take 5-30 minutes depending on file size)
- **Subsequent runs**: Loads from cache (takes seconds)
- **Cache location**: `./data_cache/aligned_data_cache.pkl`

**To force reprocessing:**
```python
preprocessor.preprocess_data(
    phenotype_file="...",
    kmer_file="...",
    use_cache=False  # Force reprocessing
)
```

## Performance Considerations

### Memory Usage
- K-mer pivot operation is memory-intensive
- Estimated RAM needed: 8-16 GB for large datasets
- Uses chunked reading to minimize peak memory

### Processing Time
- **ID Mapping**: ~30 seconds
- **Phenotype Processing**: ~1-2 minutes
- **K-mer Processing**: ~5-20 minutes (depends on file size)
- **Alignment**: ~10 seconds
- **Total (first run)**: ~10-30 minutes
- **Total (cached)**: ~5-10 seconds

### Optimization Tips
1. **Use caching**: Always enable caching for development
2. **Subset data**: For testing, create smaller sample files
3. **Monitor memory**: Use Task Manager to watch RAM usage
4. **SSD recommended**: Faster I/O for large file operations

## API Endpoints

### Training Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/training/train` | POST | Start training job |
| `/api/training/status/{job_id}` | GET | Get job status |
| `/api/training/jobs` | GET | List all jobs |
| `/api/training/jobs/{job_id}` | DELETE | Delete job |
| `/api/training/cleanup` | POST | Clean old jobs |

### Training Request Format

```json
{
  "phenotype_file": "BVBRC_genome_amr.txt",
  "kmer_file": "DATA/SIGNIFICANT_DNA_KMERS_BACTERIA",
  "rosetta_file": "BVBRC_genome.txt",
  "model_type": "parallel",
  "xgboost_model_name": "xgboost_amr_model",
  "transformer_model_name": "dnabert_amr_model"
}
```

**Model Types:**
- `"xgboost"`: Train only XGBoost
- `"transformer"`: Train only Transformer
- `"parallel"`: Train both in parallel (recommended)

## Troubleshooting

### Issue: "File not found"
**Solution:** Ensure all data files are in the correct locations:
- `BVBRC_genome.txt` in project root
- `BVBRC_genome_amr.txt` in project root
- `SIGNIFICANT_DNA_KMERS_BACTERIA` in `DATA/` folder

### Issue: "No matching genomes found"
**Solution:** Check that:
1. ID mapping file has correct column names
2. Genome IDs match between files
3. Files are not corrupted

### Issue: "Memory error during pivot"
**Solution:**
1. Close other applications
2. Increase system RAM
3. Use a subset of data for testing
4. Process in smaller chunks (modify chunk_size parameter)

### Issue: "Cache is stale"
**Solution:** Delete cache and reprocess:
```powershell
Remove-Item -Recurse data_cache
python test_preprocessing.py
```

## Next Steps

After successful preprocessing:

1. ✅ **Data is aligned** - X and Y matrices match
2. ✅ **Cache is created** - Future runs are fast
3. ✅ **Ready for training** - Models can now be trained
4. 🔄 **Train models** - Use API or direct training
5. 🔄 **Evaluate results** - Check model performance
6. 🔄 **Deploy models** - Use for predictions

## Technical Details

### ID Mapping Strategy
```python
# BVBRC_genome.txt structure:
# Genome Name | Genome ID (PATRIC) | GenBank Accession
# Maps: "562.144628" → "GCA_000002515.1"
```

### Encoding Scheme
```python
resistance_map = {
    'Susceptible': 0,
    'Intermediate': 1,
    'Resistant': 2
}
```

### Alignment Logic
```python
# Inner join: Keep only genomes in BOTH X and Y
X_final, Y_final = X.align(Y, join='inner', axis=0)
```

## Support

For issues or questions:
1. Check this guide
2. Review logs in `backend.log`
3. Test with `test_preprocessing.py`
4. Check API docs at http://localhost:8000/docs
