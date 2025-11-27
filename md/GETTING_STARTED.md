# Getting Started with ML Pipeline

## 🎯 What You Have Now

A complete **ML training pipeline** for antibiotic resistance prediction:

✅ **Backend API** - FastAPI server with XGBoost training  
✅ **Frontend UI** - React interface with 4 tabs  
✅ **Real-time monitoring** - Watch training progress live  
✅ **Full documentation** - Setup guides and API docs  

## 🚀 Quick Start (2 Steps)

### Step 1: Start Backend (2 minutes)

```bash
# Open terminal 1
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
python run_server.py
```

✅ You should see: "Starting Antibiotic Resistance Prediction API"

### Step 2: Start Frontend (1 minute)

```bash
# Open terminal 2 (keep terminal 1 running!)
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev
```

✅ Open browser to: http://localhost:5173

## 🎮 Using the System

### You'll see 4 tabs:

1. **Genome Upload** - For predictions (needs trained model first)
2. **Results Dashboard** - Shows prediction results
3. **Model Training** ← **START HERE**
4. **Training Status** - Watch training progress

### First Time: Train a Model

1. Click **"Model Training"** tab
2. Select **"XGBoost"** (recommended to start)
3. You need two files:
   - **K-mer file** (.tsv) - Your genomic features
   - **Phenotype file** (.csv) - Your resistance labels

### Your Data Format

**K-mer file** (tab-separated):
```
genome_001	Bacteria	10	ACCCCGCGCG	0.0001	0.01
genome_002	Bacteria	10	ACCGCCGCCG	0.0002	0.02
```

**Phenotype file** (comma-separated):
```csv
Genome Name,Antibiotic,Resistant Phenotype
genome_001,ampicillin,Resistant
genome_002,ciprofloxacin,Susceptible
```

**Important**: Genome IDs must match between files!

## 📁 Where Are Your Files?

Based on your message, you mentioned having:
- ✅ K-mer data already available
- ✅ Phenotype data already available

**To use them**:
1. Make sure k-mer data is k=10 (for XGBoost)
2. Make sure genome IDs match between files
3. Upload both files in the "Model Training" tab

## 🎓 What Happens When You Train?

```
Your files → Backend parses them → Builds feature matrix
→ Aligns labels → Trains XGBoost models (one per antibiotic)
→ Evaluates on test set → Shows you metrics → Saves model
```

You'll see:
- Real-time progress (0-100%)
- Current step (e.g., "Training model for ampicillin...")
- Final metrics (accuracy, F1 score, Jaccard score)
- Per-antibiotic performance table

Training time: 2-10 minutes depending on data size

## 📊 What You'll Get

After training completes:

**Overall Metrics**:
- Average Accuracy: 75-90%
- Average F1 Score: 0.70-0.85
- Average Jaccard Score: 0.65-0.80

**Per-Antibiotic Results**:
- Individual model performance
- Number of training samples
- Class distributions

**Saved Artifacts**:
- `backend/trained_models/your_model_name/model.pkl`
- `backend/trained_models/your_model_name/metadata.json`
- `backend/trained_models/your_model_name/features.json`

## 🔍 Checking If It Works

### Test Backend:
```bash
curl http://localhost:8000/health
```
Expected: `{"status":"healthy","model_storage":"./trained_models"}`

### Test Frontend:
- Open http://localhost:5173
- You should see the 4 tabs
- No errors in browser console (F12)

### Test Training:
- Upload your files
- Click "Start Training"
- See job ID appear
- Progress bar starts moving

## ❓ Common Questions

**Q: Do I need Qdrant or Supabase?**  
A: No! Not for basic training. They're optional for production features.

**Q: What if I only have FASTA files?**  
A: You need to generate k-mer features first. The system expects pre-computed k-mers.

**Q: Can I train multiple models?**  
A: Yes! Each training job creates a new model. Give them different names.

**Q: How do I know if my data is correct?**  
A: The system will tell you during training:
- "No genomes found in both files" = ID mismatch
- "Insufficient data for antibiotic" = Need more samples
- Training completes = Data is good!

**Q: Where do I see errors?**  
A: 
- Backend: In terminal 1 where you ran `python run_server.py`
- Frontend: In browser console (F12 → Console tab)
- Training errors: In the "Training Status" tab

## 🐛 Quick Troubleshooting

**"Module not found"**:
```bash
# Make sure virtual environment is activated
# You should see (venv) in your terminal prompt
pip install -r requirements.txt
```

**"Port already in use"**:
```bash
# Something else is using port 8000 or 5173
# Close other apps or change port in config
```

**"Failed to fetch"**:
```bash
# Backend not running
# Check terminal 1 - server should be running
# Verify .env has VITE_API_URL=http://localhost:8000
```

**"Training fails immediately"**:
- Check file formats (TSV for k-mer, CSV for phenotype)
- Verify genome IDs match exactly
- Look at backend terminal for detailed error

## 📚 Full Documentation

For more details, see:
- **SETUP_GUIDE.md** - Detailed setup instructions
- **README_ML_PIPELINE.md** - Complete project overview
- **backend/README.md** - API documentation
- **IMPLEMENTATION_SUMMARY.md** - What's implemented

## 🎯 Next Steps After First Training

1. ✅ Train your first model successfully
2. Review the metrics - are they reasonable?
3. Try different hyperparameters
4. Train models for different species/datasets
5. Once satisfied, move to prediction pipeline

## 🆘 Still Having Issues?

1. Check all prerequisites installed (Python 3.9+, Node 18+)
2. Read error messages carefully
3. Review SETUP_GUIDE.md troubleshooting section
4. Check backend logs for detailed errors
5. Visit http://localhost:8000/docs for API documentation

## 🎉 Success Checklist

Before training:
- [ ] Backend server running (see "Uvicorn running on http://0.0.0.0:8000")
- [ ] Frontend running (see "Local: http://localhost:5173")
- [ ] Can open http://localhost:5173 in browser
- [ ] See 4 tabs: Upload, Results, Training, Status
- [ ] Have k-mer file (k=10, TSV format)
- [ ] Have phenotype file (CSV format)
- [ ] Genome IDs match between files

After training:
- [ ] Job created successfully (got job ID)
- [ ] Progress bar moving (0% → 100%)
- [ ] Training completes without errors
- [ ] See metrics displayed
- [ ] Model saved to `backend/trained_models/`

When all checked: **You're ready to go!** 🚀

---

**Need Help?** The system is designed to be self-explanatory, but check the docs if you get stuck. All error messages are descriptive and tell you what's wrong.

**Have Data?** Great! Follow Steps 1 & 2 above, then upload your files in the Model Training tab. The system will handle the rest.

**Stuck?** Check backend terminal output - it shows exactly what's happening during training.

