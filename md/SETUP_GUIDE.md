# Setup Guide - ML Pipeline

Complete setup instructions for the Antibiotic Resistance Prediction system.

## ⚡ Quick Setup (5 Minutes)

### Step 1: Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file (optional for now)
# You can skip Qdrant and Supabase for initial testing
echo "FRONTEND_URL=http://localhost:5173" > .env
echo "MODEL_STORAGE_PATH=./trained_models" >> .env

# Start backend server
python run_server.py
```

✅ Backend should now be running at `http://localhost:8000`

### Step 2: Frontend Setup

```bash
# Open a NEW terminal
# Navigate to project root
cd <project-root>

# Install dependencies
npm install

# Create environment file
echo "VITE_API_URL=http://localhost:8000" > .env

# Start frontend
npm run dev
```

✅ Frontend should now be running at `http://localhost:5173`

### Step 3: Test the System

1. Open browser to `http://localhost:5173`
2. You should see 4 tabs:
   - Genome Upload
   - Results Dashboard
   - **Model Training** ← Start here
   - Training Status

3. Click **Model Training** tab
4. Try uploading sample files (if you have them)

## 📋 Detailed Setup

### Prerequisites Check

```bash
# Check Python version (need 3.9+)
python --version

# Check Node.js version (need 18+)
node --version

# Check npm
npm --version
```

If any are missing or outdated, install/update them first.

### Backend Detailed Setup

#### 1. Install Python Dependencies

The `requirements.txt` includes:
- FastAPI & Uvicorn (API framework)
- XGBoost (ML models)
- Transformers & PyTorch (for DNABERT)
- Pandas & NumPy (data processing)
- Scikit-learn (metrics)
- Qdrant client (vector DB - optional)
- Supabase (metadata storage - optional)

```bash
cd backend
pip install -r requirements.txt
```

This may take 5-10 minutes as it downloads PyTorch and other large packages.

#### 2. Configure Environment

Create `backend/.env`:

**Minimal (for testing)**:
```bash
FRONTEND_URL=http://localhost:5173
MODEL_STORAGE_PATH=./trained_models
```

**Full (for production)**:
```bash
# Required
FRONTEND_URL=http://localhost:5173
MODEL_STORAGE_PATH=./trained_models

# Optional - Qdrant (for similarity search)
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_api_key

# Optional - Supabase (for model metadata)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
```

#### 3. Verify Installation

```bash
# Test import
python -c "import fastapi, xgboost, transformers; print('All imports successful!')"

# Start server
python run_server.py
```

Visit `http://localhost:8000/docs` - you should see the API documentation.

### Frontend Detailed Setup

#### 1. Install Node Dependencies

```bash
# From project root
npm install
```

This installs:
- React & TypeScript
- Vite (build tool)
- Tailwind CSS (styling)
- shadcn/ui (components)
- Lucide icons
- Framer Motion (animations)

#### 2. Configure Environment

Create `.env` in project root:
```bash
VITE_API_URL=http://localhost:8000
```

#### 3. Start Development Server

```bash
npm run dev
```

Visit `http://localhost:5173` - you should see the application.

## 🗂️ Preparing Training Data

### K-mer Data Format

Create a TSV file with k-mer frequencies:

**For XGBoost (k=10)**:
```tsv
GCA_000001.1	Bacteria	10	AAAAAAAAAA	0.001	0.005
GCA_000001.1	Bacteria	10	AAAAAAAAAC	0.002	0.006
GCA_000002.1	Bacteria	10	AAAAAAAAAA	0.001	0.004
```

**For DNABERT (k=6)**:
```tsv
GCA_000001.1	Bacteria	6	AAAAAA	0.001	0.005
GCA_000001.1	Bacteria	6	AAAAAC	0.002	0.006
```

Columns:
1. Genome ID (must match phenotype file)
2. Domain (e.g., "Bacteria")
3. K-mer size
4. K-mer sequence
5. Probability 1 (not used currently)
6. Probability 2 (used as frequency)

### Phenotype Data Format

Create a CSV file with resistance labels:

```csv
Genome Name,Antibiotic,Resistant Phenotype
GCA_000001.1,ampicillin,Resistant
GCA_000001.1,ciprofloxacin,Susceptible
GCA_000002.1,ampicillin,Intermediate
GCA_000002.1,tetracycline,Resistant
```

Required columns:
- **Genome Name**: Must match genome IDs in k-mer file
- **Antibiotic**: Drug name (lowercase)
- **Resistant Phenotype**: S, I, R (or full words)

Optional columns (ignored but can be present):
- Measurement Sign, Measurement Value, Measurement Units
- Lab typing Method, Computational Method
- Evidence, Pubmed

## 🎯 Testing the Training Pipeline

### Create Sample Data

**Tiny sample k-mer file** (`sample_kmers.tsv`):
```tsv
genome_001	Bacteria	10	ACCCCGCGCG	0.0001	0.01
genome_001	Bacteria	10	ACCGCCGCCG	0.0002	0.02
genome_002	Bacteria	10	ACCCCGCGCG	0.0001	0.015
genome_002	Bacteria	10	TTTTTTTTTT	0.0003	0.03
```

**Tiny sample phenotype file** (`sample_phenotypes.csv`):
```csv
Genome Name,Antibiotic,Resistant Phenotype
genome_001,ampicillin,Resistant
genome_001,ciprofloxacin,Susceptible
genome_002,ampicillin,Susceptible
genome_002,ciprofloxacin,Resistant
```

### Run Training

1. Go to **Model Training** tab
2. Select **XGBoost**
3. Upload `sample_kmers.tsv`
4. Upload `sample_phenotypes.csv`
5. Name it "test_model"
6. Click **Start Training**
7. Go to **Training Status** tab
8. Watch progress bar

Expected result: Training completes in <1 minute with metrics displayed.

## 🔧 Troubleshooting

### Backend Issues

**"Module not found" errors**:
```bash
# Ensure virtual environment is activated
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Reinstall
pip install -r requirements.txt
```

**"Port 8000 already in use"**:
```bash
# Find and kill process
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac:
lsof -ti:8000 | xargs kill -9
```

**"Permission denied" on Windows**:
Run terminal as Administrator

### Frontend Issues

**"Command not found: npm"**:
Install Node.js from https://nodejs.org

**"EACCES" permission errors**:
```bash
# Fix npm permissions
npm config set prefix ~/.npm-global
export PATH=~/.npm-global/bin:$PATH
```

**Build errors**:
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Training Issues

**"No genomes found in both files"**:
- Check genome IDs match exactly between k-mer and phenotype files
- Verify file encodings (should be UTF-8)

**"Insufficient data for antibiotic"**:
- Need at least 10 samples per antibiotic
- Check for typos in antibiotic names

**Out of memory**:
- Reduce data size for testing
- Close other applications
- Add more RAM or use smaller k

### Connection Issues

**"Failed to fetch"**:
- Verify backend is running: `curl http://localhost:8000/health`
- Check CORS configuration in `backend/main.py`
- Verify `VITE_API_URL` in frontend `.env`

## 🚀 Next Steps

After successful setup:

1. **Train Real Models**: Use your actual k-mer and phenotype data
2. **Test Predictions**: Upload FASTA files in "Genome Upload" tab
3. **Monitor Performance**: View metrics in training results
4. **Deploy**: Follow deployment guide in README_ML_PIPELINE.md

## 📞 Getting Help

If you encounter issues:

1. Check console output for error messages
2. Verify all prerequisites are installed
3. Review the troubleshooting section
4. Check API docs at `http://localhost:8000/docs`
5. Review backend logs for detailed errors

## ✅ Success Checklist

- [ ] Python 3.9+ installed
- [ ] Node.js 18+ installed
- [ ] Backend dependencies installed
- [ ] Frontend dependencies installed
- [ ] Backend running on port 8000
- [ ] Frontend running on port 5173
- [ ] Can access UI in browser
- [ ] Can see 4 tabs in interface
- [ ] Can navigate to Model Training tab

When all checked, you're ready to use the system! 🎉

