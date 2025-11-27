# Antibiotic Resistance Prediction - ML Pipeline

A complete machine learning pipeline for predicting bacterial antibiotic resistance from whole genome sequences. Features both XGBoost baseline models and advanced Transformer (DNABERT) models with a modern React web interface.

## 🎯 Project Overview

This system enables:
- **Offline Training**: Train models on large datasets of bacterial genomes with lab-verified phenotypes
- **Online Prediction**: Real-time prediction of antibiogram profiles from uploaded FASTA files
- **Dual Architecture**: Choose between fast XGBoost or powerful Transformer models
- **Vector Search**: Qdrant-based similarity search for genome identification
- **Model Registry**: Track and version all trained models

## 🏗️ Architecture

### Frontend (React + TypeScript + Vite)
- Modern UI with Tailwind CSS and shadcn/ui components
- Four main views:
  1. **Genome Upload**: Submit FASTA files for prediction
  2. **Results Dashboard**: View predicted antibiograms with confidence scores
  3. **Model Training**: Upload k-mer + phenotype data to train new models
  4. **Training Status**: Monitor training progress in real-time

### Backend (Python FastAPI)
- Async API with background job processing
- XGBoost and DNABERT training pipelines
- K-mer feature engineering (k=10 for XGBoost, k=6 for DNABERT)
- Phenotype data parsing and alignment
- Model evaluation with F1, Jaccard, and accuracy metrics

### Databases
- **Qdrant Cloud**: Vector database for genome embeddings (free tier)
- **Supabase**: Model metadata and training history (free tier)
- **Local Storage**: Trained model files (.pkl, .pt)

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ (for frontend)
- Python 3.9+ (for backend)
- Git

### 1. Clone Repository
```bash
git clone <repository-url>
cd <project-directory>
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Qdrant and Supabase credentials

# Run server
python main.py
```

Backend will be available at `http://localhost:8000`

### 3. Frontend Setup
```bash
# From project root
npm install

# Create environment file
echo "VITE_API_URL=http://localhost:8000" > .env

# Run development server
npm run dev
```

Frontend will be available at `http://localhost:5173`

## 📊 Data Requirements

### Training Data

#### K-mer File (TSV)
Tab-separated file with k-mer frequencies:
```
GCA_000002515.1	Bacteria	10	ACCCCGCGCG	1.43e-07	9.83e-03
GCA_000002515.1	Bacteria	10	ACCGCCGCCG	1.43e-07	9.83e-03
```
- Use k=10 for XGBoost
- Use k=6 for DNABERT/Transformer

#### Phenotype File (CSV)
Lab-verified resistance data:
```csv
Genome Name,Antibiotic,Resistant Phenotype
Salmonella enterica A038_2016,azithromycin,Susceptible
Escherichia coli strain 372-13,ciprofloxacin,Resistant
```

### Prediction Data
- Standard FASTA format genome sequences
- Can be whole genome or gene sequences
- Accepts `.fasta`, `.fa`, or `.fna` extensions

## 🎓 Usage Guide

### Training a Model

1. Navigate to **Model Training** tab
2. Select model type:
   - **XGBoost**: Fast, interpretable, good for baseline
   - **Transformer**: Slower, captures complex patterns
3. Upload files:
   - K-mer data (TSV)
   - Phenotype data (CSV)
4. (Optional) Adjust hyperparameters
5. Click **Start Training**
6. Monitor progress in **Training Status** tab

Training typically takes:
- XGBoost: 2-10 minutes
- Transformer: 30-120 minutes (depending on data size)

### Making Predictions

1. Navigate to **Genome Upload** tab
2. Drag and drop or browse for FASTA file
3. Wait for analysis (typically 10-30 seconds)
4. View results in **Results Dashboard**:
   - Susceptible (S), Intermediate (I), or Resistant (R) for each antibiotic
   - Confidence scores
   - Genetic markers identified

## 🔬 How It Works

### Training Pipeline

1. **Data Ingestion**: Parse k-mer and phenotype files
2. **Feature Engineering**: Build feature matrix (genomes × k-mers)
3. **Label Alignment**: Match genomes between k-mer and phenotype data
4. **Model Training**: Train separate model for each antibiotic
5. **Evaluation**: Calculate metrics on held-out test set (20%)
6. **Persistence**: Save models, features, and metadata

### Prediction Pipeline

1. **File Upload**: User submits FASTA file
2. **K-mer Extraction**: Extract k-mer features from sequence
3. **Embedding Generation**: Convert to vector representation
4. **Similarity Search**: Query Qdrant to find similar genomes
5. **Model Selection**: Load appropriate trained model
6. **Inference**: Predict resistance for all antibiotics
7. **Results Display**: Show antibiogram with confidence scores

## 📈 Model Performance

XGBoost models typically achieve:
- **Accuracy**: 75-90% per antibiotic
- **F1 Score**: 0.70-0.85 (macro average)
- **Jaccard Score**: 0.65-0.80 (macro average)

Performance varies by:
- Training data size and quality
- Antibiotic class
- Bacterial species
- K-mer size

## 🛠️ Technical Stack

### Frontend
- **React 18** with TypeScript
- **Vite** for fast builds
- **Tailwind CSS** for styling
- **shadcn/ui** for components
- **Framer Motion** for animations
- **Lucide Icons**

### Backend
- **FastAPI** for async API
- **XGBoost** for gradient boosting
- **Transformers (Hugging Face)** for DNABERT
- **PyTorch** for deep learning
- **Pandas** for data manipulation
- **Scikit-learn** for metrics
- **Biopython** for genomics

### Infrastructure
- **Qdrant Cloud** for vector search
- **Supabase** for metadata storage
- **Render** for backend hosting (planned)
- **Vercel/Netlify** for frontend hosting (planned)

## 📁 Project Structure

```
project/
├── backend/                    # Python FastAPI backend
│   ├── main.py                # API entry point
│   ├── config.py              # Configuration
│   ├── requirements.txt       # Dependencies
│   ├── models/                # Training modules
│   ├── preprocessing/         # Data processing
│   ├── api/                   # API routes
│   ├── services/              # External services
│   ├── jobs/                  # Background jobs
│   └── trained_models/        # Saved models
├── src/                       # React frontend
│   ├── components/            # UI components
│   │   ├── GenomeUploader.tsx
│   │   ├── ResultsDashboard.tsx
│   │   ├── TrainingPipeline.tsx
│   │   ├── TrainingStatus.tsx
│   │   └── home.tsx
│   ├── services/              # API clients
│   │   └── apiClient.ts
│   └── lib/                   # Utilities
├── public/                    # Static assets
├── package.json               # Frontend dependencies
└── README.md                  # This file
```

## 🔧 Configuration

### Environment Variables

**Backend (`.env`)**:
```bash
QDRANT_URL=https://xyz.qdrant.io
QDRANT_API_KEY=your_key
SUPABASE_URL=https://xyz.supabase.co
SUPABASE_KEY=your_key
MODEL_STORAGE_PATH=./trained_models
FRONTEND_URL=http://localhost:5173
```

**Frontend (`.env`)**:
```bash
VITE_API_URL=http://localhost:8000
```

## 🧪 Development

### Backend Testing
```bash
cd backend
pytest tests/
```

### Frontend Testing
```bash
npm run test
```

### Code Quality
```bash
# Backend
black backend/
flake8 backend/

# Frontend
npm run lint
```

## 📦 Deployment

### Backend (Render)
1. Create new Web Service
2. Connect repository
3. Set build: `cd backend && pip install -r requirements.txt`
4. Set start: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables

### Frontend (Vercel)
1. Import repository
2. Set build: `npm run build`
3. Set output: `dist`
4. Add `VITE_API_URL` environment variable

## 🐛 Troubleshooting

### Common Issues

**Backend won't start**:
- Check Python version (3.9+)
- Ensure all dependencies installed
- Verify `.env` file exists

**Training fails**:
- Verify file formats (TSV for k-mer, CSV for phenotype)
- Check genome IDs match between files
- Ensure sufficient RAM (4GB+ recommended)

**Frontend can't connect to backend**:
- Verify backend is running on port 8000
- Check `VITE_API_URL` in frontend `.env`
- Ensure CORS is configured correctly

**Prediction is slow**:
- Large FASTA files take longer
- First prediction after startup is slower (model loading)
- Check network connection to Qdrant

## 🤝 Contributing

This is an academic project. Contributions welcome:
1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

## 📄 License

Educational/Research use.

## 📚 References

- K-mer approach inspired by genomic ML literature
- XGBoost: Chen & Guestrin, 2016
- DNABERT: Ji et al., 2021
- Qdrant: https://qdrant.tech
- FastAPI: https://fastapi.tiangolo.com

## 🙏 Acknowledgments

- NCBI for genome data
- BV-BRC for phenotype data
- Hugging Face for pre-trained models
- Open source community

## 📞 Support

For questions or issues:
- Check documentation in `backend/README.md`
- Review API docs at `http://localhost:8000/docs`
- Open GitHub issue

---

**Status**: ✅ XGBoost Pipeline Complete | 🚧 Transformer Pipeline In Progress | 🔜 Prediction API Coming Soon

