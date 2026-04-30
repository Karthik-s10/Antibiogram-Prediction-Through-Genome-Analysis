# 🧬 Antibiogram Prediction Through Genome Analysis

> Predict antibiotic resistance (AMR) from bacterial whole-genome sequences using machine learning — combining **XGBoost** (k-mer features) and **DNABERT** (transformer) models with a vector database for genome similarity search.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi)
![PyTorch](https://img.shields.io/badge/PyTorch-2.5-EE4C2C?logo=pytorch)
![Qdrant](https://img.shields.io/badge/Qdrant-Cloud-6C63FF)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [How It Works](#how-it-works)
- [Data Sources](#data-sources)
- [CI/CD](#cicd)

---

## Overview

This system takes a bacterial genome in FASTA format and predicts whether the organism is **Susceptible (S)**, **Intermediate (I)**, or **Resistant (R)** to up to **134 antibiotics**. It supports two prediction models:

| Model | Method | Speed | Explainability |
|-------|--------|-------|----------------|
| **XGBoost** | K-mer frequency counting + gradient boosting | Fast | SHAP values |
| **DNABERT** | Fine-tuned DNA language model (gene-level) | Slower (GPU recommended) | Attention weights |
| **Ensemble** | Both models combined | Moderate | Both |

Predictions are enriched with **similar genome lookup** via a Qdrant vector database seeded with 2,928+ bacterial genomes.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                   │
│         Upload FASTA → View Antibiogram → Explainability    │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP (REST)
┌────────────────────────▼────────────────────────────────────┐
│                  FastAPI Backend (Python)                    │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  /api/train  │  │ /api/predict │  │ /api/explanations│  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                   │             │
│  ┌──────▼───────────────────────────────────▼─────────┐    │
│  │           ML Models & Processing Pipeline           │    │
│  │  XGBoostTrainer │ DNABERTTrainer │ KmerProcessor    │    │
│  └──────────────────────────┬──────────────────────────┘    │
│                             │                               │
│  ┌──────────────────────────▼──────────────────────────┐    │
│  │              Qdrant Vector DB (Cloud)                │    │
│  │          2,928+ genome embeddings (768-dim)          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Features

- 🔬 **Dual-model prediction** — XGBoost and DNABERT with ensemble mode
- 🗄️ **Vector similarity search** — Find the 5 most genetically similar known bacteria
- 💡 **Explainability** — SHAP values (XGBoost) and attention weights (DNABERT) showing which k-mers/genes drive resistance
- 📊 **Training UI** — Train new models directly from the web interface by uploading your own data
- ⚡ **Async job tracking** — Long training runs are managed as background jobs with real-time status
- 🔄 **GitHub Action** — Scheduled Qdrant collection maintenance every 5 days
- 🧪 **Mock mode** — Returns demo predictions when no trained model is present

---

## Project Structure

```
├── backend/                    # Python FastAPI backend
│   ├── api/                    # Route handlers
│   │   ├── prediction_routes.py   # POST /api/predict/
│   │   ├── training_routes.py     # POST /api/train/xgboost|transformer
│   │   ├── status_routes.py       # GET  /api/status/{job_id}
│   │   └── explanations.py        # POST /api/explanations/
│   ├── models/
│   │   ├── xgboost_trainer.py     # XGBoost multi-label trainer
│   │   └── transformer_trainer.py # DNABERT fine-tuning trainer
│   ├── preprocessing/
│   │   ├── data_preprocessor.py   # K-mer + phenotype pipeline
│   │   ├── kmer_processor.py      # K-mer extraction from FASTA
│   │   └── dnabert_processor.py   # Gene extraction for DNABERT
│   ├── services/
│   │   ├── qdrant_service.py      # Vector DB insert/search
│   │   └── embedding_service.py   # FASTA → 768-dim embedding
│   ├── scripts/
│   │   ├── populate_qdrant_vectors.py   # Seed vector DB from k-mer dataset
│   │   └── populate_qdrant_dnabert.py   # Seed DB using DNABERT embeddings
│   ├── jobs/                      # Background training job management
│   ├── explainability/            # SHAP + attention explainers
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Settings (env vars)
│   └── requirements.txt
│
├── src/                        # React + TypeScript frontend
│   ├── components/             # UI components
│   └── services/               # API client calls
│
├── DATA/                       # Training datasets (not committed)
│   ├── BVBRC_genome_amr.txt       # BV-BRC phenotype labels
│   ├── BVBRC_genome.txt           # Genome metadata (Rosetta mapping)
│   └── kmer_dataset_taxon_k10_p1e-5_all.txt  # Pre-computed k-mers (1.8 GB)
│
├── .github/workflows/
│   └── maintain_qdrant_collection.yml  # Scheduled DB maintenance
│
├── START.ps1                   # One-click start (Windows)
├── start.sh                    # One-click start (Linux/macOS)
└── .env                        # Environment variables (not committed)
```

---

## Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **GPU** (optional but strongly recommended for DNABERT training — CUDA 12.1)
- **Qdrant Cloud** account (free tier works)
- **NCBI API Key** (for genome downloads)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/Antibiogram-Prediction-Through-Genome-Analysis.git
cd Antibiogram-Prediction-Through-Genome-Analysis
```

### 2. Backend setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

# Install dependencies (includes PyTorch with CUDA 12.1)
pip install -r requirements.txt
```

> **Note (Windows):** If XGBoost or PyTorch fail to load, install Visual C++ Redistributables:
> ```
> python install_vc_redist.py
> ```

### 3. Frontend setup

```bash
# From the project root
npm install
```

---

## Configuration

Create a `.env` file in the project root:

```env
# Backend API URL (for frontend)
VITE_API_URL=http://localhost:8000

# NCBI API Key (for genome downloads)
NCBI_API_KEY=your_ncbi_api_key_here
VITE_NCBI_API_KEY=your_ncbi_api_key_here

# Qdrant Cloud
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key_here
QDRANT_COLLECTION_NAME=bacterial_genomes
```

> **Security:** `QDRANT_URL` and `QDRANT_API_KEY` are also stored as **GitHub Repository Secrets** for use in CI/CD workflows. Never commit these values directly.

Get your NCBI API key at: https://www.ncbi.nlm.nih.gov/account/

---

## Running the Application

### Windows (one command)

```powershell
.\START.ps1
```

### Linux / macOS

```bash
chmod +x start.sh
./start.sh
```

### Manual start

```bash
# Terminal 1 — Backend
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
npm run dev
```

The app will be available at:
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs

---

## API Reference

### Prediction

```
POST /api/predict/
  Body: multipart/form-data
    genome_file: <FASTA file>
    model_mode: "auto" | "xgboost" | "transformer" | "both"
    enable_blast: false

GET  /api/predict/models
POST /api/predict/xgboost_blast_kmers
GET  /api/predict/xgboost_explainability/{model_name}
```

### Training

```
POST /api/train/xgboost      # Train XGBoost models
POST /api/train/transformer  # Fine-tune DNABERT
POST /api/train/parallel     # Train both simultaneously
```

### Job Status

```
GET    /api/status/           # List all jobs
GET    /api/status/{job_id}   # Job status + progress
DELETE /api/status/{job_id}   # Delete a job
POST   /api/status/{job_id}/pin
POST   /api/status/{job_id}/unpin
```

### Explainability

```
POST /api/explanations/single           # Explain one prediction
POST /api/explanations/batch            # Batch explanations
POST /api/explanations/global-importance
POST /api/explanations/summary
GET  /api/explanations/models
GET  /api/explanations/attention        # DNABERT attention weights
DELETE /api/explanations/cache
```

---

## How It Works

### XGBoost Pipeline

```
FASTA file
  → K-mer extraction (k=10, overlapping windows)
  → Feature vector (137,681 dimensions — one per unique k-mer)
  → XGBoost classifier (one per antibiotic, 134 total)
  → S / I / R label + confidence score
  → SHAP values for explainability
```

### DNABERT Pipeline

```
FASTA file
  → Gene sequence extraction (ORF detection)
  → K-mer tokenization per gene (k=6, space-separated)
  → DNABERT forward pass (pre-trained: zhihan1996/DNA_bert_6)
  → Per-gene classification: S / I / R
  → Genome-level aggregation:
      if ANY gene → R: genome = Resistant
      elif ANY gene → I: genome = Intermediate
      else: genome = Susceptible
  → Attention weights for explainability
```

### Similarity Search

```
FASTA file
  → PCA embedding (768 dimensions)
  → Qdrant cosine similarity search
  → Top 5 most similar known genomes
  → Re-ranked by species hints from FASTA header
```

---

## Data Sources

| Dataset | Source | Description |
|---------|--------|-------------|
| `BVBRC_genome_amr.txt` | [BV-BRC](https://www.bv-brc.org/) | AMR phenotype labels (S/I/R) per genome per antibiotic |
| `BVBRC_genome.txt` | [BV-BRC](https://www.bv-brc.org/) | Genome metadata and ID mappings |
| K-mer dataset | Pre-computed | 10-mer frequencies for 3,204 bacterial genomes |
| FASTA genomes | [NCBI Datasets](https://www.ncbi.nlm.nih.gov/datasets/) | Downloaded via NCBI API (one per Taxon ID) |

**Training coverage:** 2,928 genomes × 134 antibiotics

---

## CI/CD

A GitHub Actions workflow (`.github/workflows/maintain_qdrant_collection.yml`) runs every 5 days to:
- Verify the Qdrant collection is healthy
- Re-seed any missing vectors

Secrets required in GitHub Repository Settings:
- `QDRANT_URL`
- `QDRANT_API_KEY`

---

## References

- [Large-scale k-mer-based analysis of the...](./Large-scale%20k-mer-based%20analysis%20of%20the.pdf) — core methodology paper
- [Machine Learning for Antimicrobial Resistance Prediction](./Machine%20Learning%20for%20Antimicrobial%20Resistance%20Prediction.pdf)
- [DNABERT](https://github.com/jerryji1993/DNABERT) — Pre-trained DNA language model

---

## License

This project is for academic and research use.
