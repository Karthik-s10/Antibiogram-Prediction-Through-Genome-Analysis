# Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Test Data Preprocessing (Optional but Recommended)

Verify your data files are correctly aligned:

```powershell
python test_preprocessing.py
```

**What this does:**
- Loads your 3 data files
- Maps IDs between phenotype and k-mer data
- Creates aligned matrices
- Saves cache for fast future runs

**Expected time:** 10-30 minutes (first run), 5 seconds (cached)

---

### Step 2: Start the Training API

```powershell
.\start_training_api.ps1
```

**What this does:**
- Activates virtual environment
- Installs dependencies (if needed)
- Starts FastAPI server on http://localhost:8000

**API Documentation:** http://localhost:8000/docs

---

### Step 3: Train Your Models

**Option A: Use the Interactive API Docs (Easiest)**

1. Open http://localhost:8000/docs
2. Click on `POST /api/training/train`
3. Click "Try it out"
4. Fill in the request body:
   ```json
   {
     "phenotype_file": "BVBRC_genome_amr.txt",
     "kmer_file": "DATA/SIGNIFICANT_DNA_KMERS_BACTERIA",
     "rosetta_file": "BVBRC_genome.txt",
     "model_type": "parallel"
   }
   ```
5. Click "Execute"
6. Copy the `job_id` from the response
7. Monitor progress at `GET /api/training/status/{job_id}`

**Option B: Use PowerShell**

```powershell
# Start training
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/training/train" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{
    "phenotype_file": "BVBRC_genome_amr.txt",
    "kmer_file": "DATA/SIGNIFICANT_DNA_KMERS_BACTERIA",
    "rosetta_file": "BVBRC_genome.txt",
    "model_type": "parallel"
  }'

$jobId = $response.job_id
Write-Host "Job ID: $jobId"

# Check status
Invoke-RestMethod -Uri "http://localhost:8000/api/training/status/$jobId"
```

---

## 📊 What Happens During Training

### Phase 1: Data Preprocessing (0-40%)
- Loads ID mapping file
- Maps PATRIC IDs to GenBank Accessions
- Creates feature matrix (X) from k-mers
- Creates label matrix (Y) from phenotypes
- Aligns matrices using inner join
- **Cached after first run!**

### Phase 2: Model Training (40-100%)
- **XGBoost**: Trains one model per antibiotic
- **Transformer**: Fine-tunes DNABERT (simplified version)
- Both run in parallel if `model_type: "parallel"`
- Progress updates every few seconds

### Phase 3: Model Saving (95-100%)
- Saves trained models to `./trained_models/`
- Saves metadata (antibiotics, features, metrics)
- Returns training results

---

## 📁 Required Files

Ensure these files exist:

```
Antibiogram-Prediction-Through-Genome-Analysis/
├── BVBRC_genome.txt                    # ID mapping (Rosetta Stone)
├── BVBRC_genome_amr.txt                # Phenotype labels
└── DATA/
    └── SIGNIFICANT_DNA_KMERS_BACTERIA  # K-mer features
```

---

## 🎯 Expected Results

After training completes, you'll see:

```json
{
  "job_id": "abc-123-def",
  "status": "completed",
  "progress": 1.0,
  "result": {
    "xgboost": {
      "model_path": "./trained_models/xgboost_amr_model",
      "metrics": {
        "avg_accuracy": 0.87,
        "avg_f1": 0.85,
        "per_antibiotic": { ... }
      }
    },
    "transformer": { ... },
    "n_genomes": 1234,
    "n_features": 567890,
    "n_antibiotics": 15,
    "antibiotics": ["amikacin", "ampicillin", ...]
  }
}
```

---

## ⚡ Performance Tips

### First Run
- **Time**: 10-30 minutes (data preprocessing)
- **RAM**: 8-16 GB recommended
- **Disk**: 2-5 GB for cache

### Subsequent Runs
- **Time**: 5-10 minutes (uses cache)
- **RAM**: 4-8 GB
- **Disk**: Minimal

### Speed Up Training
1. ✅ **Use cache** - Preprocessing is cached automatically
2. ✅ **GPU acceleration** - Automatically detected and used
3. ✅ **Parallel training** - XGBoost + Transformer run together
4. ⚠️ **Close other apps** - Free up RAM and CPU

---

## 🔍 Monitoring Progress

### Real-time Status Checks

```powershell
# Poll every 10 seconds
while ($true) {
    $status = Invoke-RestMethod -Uri "http://localhost:8000/api/training/status/$jobId"
    Write-Host "Progress: $($status.progress * 100)% - $($status.message)"
    
    if ($status.status -eq "completed" -or $status.status -eq "failed") {
        break
    }
    
    Start-Sleep -Seconds 10
}
```

### Check Logs

```powershell
# View backend logs
Get-Content backend\backend.log -Tail 50 -Wait
```

---

## 🐛 Troubleshooting

### "Module not found" error
```powershell
cd backend
pip install -r requirements.txt
```

### "File not found" error
Check file paths are correct relative to project root:
- `BVBRC_genome.txt` (root)
- `BVBRC_genome_amr.txt` (root)
- `DATA/SIGNIFICANT_DNA_KMERS_BACTERIA` (in DATA folder)

### "No matching genomes" error
- ID mapping file may be incorrect
- Run `test_preprocessing.py` to diagnose

### Out of memory error
- Close other applications
- Use smaller dataset for testing
- Increase system RAM

### Cache issues
```powershell
# Clear cache and retry
Remove-Item -Recurse data_cache
python test_preprocessing.py
```

---

## 📚 Next Steps

1. ✅ **Train models** (you are here)
2. 🔄 **Evaluate performance** - Check metrics in results
3. 🔄 **Make predictions** - Use trained models on new genomes
4. 🔄 **Deploy to production** - Set up prediction API

---

## 🆘 Need Help?

1. **Check logs**: `backend/backend.log`
2. **Test preprocessing**: `python test_preprocessing.py`
3. **Read full guide**: `PREPROCESSING_GUIDE.md`
4. **API docs**: http://localhost:8000/docs
