# Antibiotic Resistance Prediction - Backend API

FastAPI backend for training and predicting antibiotic resistance from bacterial genome sequences.

## Features

- **XGBoost Training**: Fast baseline models with k=10 k-mer features
- **Transformer Training**: DNABERT models for advanced genomic analysis (k=6)
- **Async Job Management**: Non-blocking training with real-time progress updates
- **Vector Database**: Qdrant integration for genome similarity search
- **Model Registry**: Supabase for metadata storage and model versioning

## Setup

### Prerequisites

- Python 3.9+
- pip or conda
- **Windows Users**: Visual C++ Redistributables (required for PyTorch GPU support)
  - Download: [vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe)
  - See [REQUIREMENTS_WINDOWS.md](REQUIREMENTS_WINDOWS.md) for details

### Installation

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On Linux/Mac
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   # IMPORTANT: Make sure you're in the backend directory!
   cd backend
   
   # Option 1: Use install script (easiest - does both steps automatically)
   # The script will automatically change to the correct directory
   install.bat        # Windows
   # or
   .\install.ps1      # PowerShell
   
   # Option 2: Manual installation (must be in backend directory)
   cd backend
   pip install -r requirements.txt
   python -c "import install_vc_redist; install_vc_redist.main()"
   ```
   
   The install script will automatically:
   - Install all Python packages
   - Check if Visual C++ Redistributables are installed
   - Download vc_redist.x64.exe to your venv directory
   - Prompt to install (installs system-wide, but .exe stored in venv)
   
   **Verify installation:**
   ```bash
   python check_system_requirements.py
   ```
   
   **Note**: The requirements.txt includes PyTorch with GPU support (CUDA 12.1) by default.
   - If you have CUDA 11.8, edit `requirements.txt` and change `cu121` to `cu118` on line 14
   - If you only have CPU, remove the `--extra-index-url` line from requirements.txt
   - After installation, verify GPU support: `python -c "import torch; print('CUDA available:', torch.cuda.is_available())"`

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your credentials:
   ```
   QDRANT_URL=https://your-cluster.qdrant.io
   QDRANT_API_KEY=your_key
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_key
   FRONTEND_URL=http://localhost:5173
   
   # BLAST Configuration (Optional)
   # 'off' | 'ncbi' | 'local'
   BLAST_MODE=off
   # For 'ncbi' mode:
   NCBI_EMAIL=your.email@example.com
   # For 'local' mode:
   BLAST_LOCAL_DB=/path/to/nt_database
   ```
   
### BLAST Integration (Optional)
To provide detailed gene markers for Transformer predictions, the application can use BLAST to assign identities. This is toggled in the UI, but requires server configuration:
1. **NCBI Mode** (`BLAST_MODE=ncbi`): Queries the public NCBI `qblast` API. Slower, and requires a valid `NCBI_EMAIL` in `.env` to prevent throttling.
2. **Local Mode** (`BLAST_MODE=local`): Requires installing the standalone **NCBI BLAST+** tool suite and downloading a local nucleotide (`nt`) database. Point `BLAST_LOCAL_DB` to the built database path. Fast and reliable for large batches.

### Running the Server

**Development mode**:
```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

**API Documentation**: Visit `http://localhost:8000/docs` for interactive Swagger UI

## API Endpoints

### Training

#### POST `/api/train/xgboost`
Train an XGBoost model.

**Request**:
- `kmer_file`: K-mer TSV file (k=10)
- `phenotype_file`: Phenotype CSV file
- `model_name`: Optional model name
- `max_depth`: Max tree depth (default: 6)
- `learning_rate`: Learning rate (default: 0.1)
- `n_estimators`: Number of trees (default: 100)

**Response**:
```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "Training job created",
  "model_name": "model_name"
}
```

#### POST `/api/train/transformer`
Train a DNABERT Transformer model.

**Request**:
- `kmer_file`: K-mer TSV file (k=6 for DNABERT)
- `phenotype_file`: Phenotype CSV file
- `model_name`: Optional model name
- `epochs`: Training epochs (default: 3)
- `batch_size`: Batch size (default: 16)
- `learning_rate`: Learning rate (default: 2e-5)

**Response**: Same as XGBoost

### Status Monitoring

#### GET `/api/status/{job_id}`
Get training job status.

**Response**:
```json
{
  "job_id": "uuid",
  "status": "running",
  "progress": 45,
  "current_step": "Training model for ampicillin...",
  "job_type": "xgboost",
  "metrics": {},
  "error": null
}
```

#### GET `/api/status/`
List all training jobs.

#### DELETE `/api/status/{job_id}`
Cancel a running job.

### Prediction

#### POST `/api/predict/`
Predict resistance from genome FASTA file.

**Request**:
- `genome_file`: FASTA format file

**Response**:
```json
{
  "status": "success",
  "genome_name": "sample.fasta",
  "predictions": [
    {
      "antibiotic": "ampicillin",
      "prediction": "R",
      "confidence": 0.95
    }
  ]
}
```

## Data Formats

### K-mer File (TSV)

```
GCA_000002515.1	Bacteria	10	ACCCCGCGCG	1.43e-07	9.83e-03
GCA_000002515.1	Bacteria	10	ACCGCCGCCG	1.43e-07	9.83e-03
```

Columns: `genome_id`, `domain`, `k`, `kmer_sequence`, `prob1`, `prob2`

### Phenotype File (CSV)

```csv
Genome Name,Antibiotic,Resistant Phenotype,Measurement Sign,Measurement Value,Measurement Units,Lab typing Method,Computational Method,Evidence,Pubmed
Salmonella enterica A038_2016,azithromycin,Susceptible,<,4,mg/L,MIC,Laboratory Method,,35651495
Escherichia coli strain 372-13,ciprofloxacin,Resistant,,,,,Disk diffusion,Laboratory Method,,30092762
```

Required columns: `Genome Name`, `Antibiotic`, `Resistant Phenotype`

## Project Structure

```
backend/
├── main.py                 # FastAPI app entry point
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── models/
│   ├── xgboost_trainer.py    # XGBoost training
│   └── model_registry.py     # Model management
├── preprocessing/
│   ├── kmer_processor.py     # K-mer feature extraction
│   └── phenotype_parser.py   # Label processing
├── api/
│   ├── training_routes.py    # Training endpoints
│   ├── prediction_routes.py  # Prediction endpoints
│   └── status_routes.py      # Status endpoints
├── services/
│   ├── qdrant_service.py     # Vector database
│   ├── supabase_service.py   # Metadata storage
│   └── storage_service.py    # Model storage
└── jobs/
    ├── training_job.py       # Training execution
    └── job_manager.py        # Job queue management
```

## Training Workflow

1. **Upload Files**: Send k-mer and phenotype files to `/api/train/xgboost`
2. **Job Created**: Receive `job_id` for tracking
3. **Monitor Progress**: Poll `/api/status/{job_id}` every 2 seconds
4. **View Results**: When status is `completed`, see metrics in response
5. **Use Model**: Trained model is automatically saved and ready for predictions

## Model Storage

Trained models are saved to `./trained_models/` by default:

```
trained_models/
├── model_name/
│   ├── model.pkl           # Pickled model
│   ├── metadata.json       # Training info
│   └── features.json       # Feature dictionary
```

## Error Handling

All errors return JSON with:
```json
{
  "detail": "Error message here"
}
```

Common issues:
- **File format errors**: Check TSV/CSV structure
- **Missing data**: Ensure genome IDs match between files
- **Memory issues**: Large k-mer files may require more RAM

## Performance

- **XGBoost Training**: ~2-10 minutes depending on data size
- **Prediction**: <1 second per genome
- **Concurrent Jobs**: Supported via async background tasks

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
black .
flake8 .
```

### Adding New Features

1. Create new module in appropriate directory
2. Add routes to `api/` package
3. Update `main.py` to include router
4. Document in this README

## Deployment

### Local Development
Already set up - just run `python main.py`

### Production (Render)

1. Create new Web Service on Render
2. Connect GitHub repository
3. Set build command: `cd backend && pip install -r requirements.txt`
4. Set start command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env`

### Docker (Optional)

```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Support

For issues or questions:
- Check `/docs` endpoint for API documentation
- Review logs in console output
- Ensure all dependencies are installed correctly

## License

Part of the Antibiotic Resistance Prediction project.

