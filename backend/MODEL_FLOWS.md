# Model Pipelines Overview

This doc summarizes how each model in the backend works, from raw data to predictions.

Models covered:

- XGBoost (k-mer features)
- Transformer (DNABERT gene-level)
- Ensemble (combining both)

---

## 1. XGBoost pipeline (k-mer features)

Training:

```mermaid
graph TD
    A[Raw genomes (FASTA)] --> B[Generate k-mer TSV (k=10)]
    B --> C[Load k-mer matrix (Taxon ID / Genome ID x k-mers)]
    D[Phenotype table (MIC / SIR)] --> E[Align genomes with k-mer rows]
    C --> E
    E --> F[Build feature matrix X (genomes x k-mers)
    + label vector y per antibiotic]
    F --> G[Per-antibiotic XGBoost training
    (binary or 3-class S/I/R)]
    G --> H[Save trained models
    + feature metadata
    + explainability JSON]
```

Prediction:

```mermaid
graph TD
    P[Input genome FASTA] --> Q[Extract k-mers (k=10)]
    Q --> R[Build feature vector
    using stored k-mer vocabulary]
    R --> S[Load XGBoost models]
    S --> T[Per-antibiotic prediction
    (S/I/R + probabilities)]
    T --> U[Return JSON response]
```

---

## 2. Transformer pipeline (DNABERT gene-level)

Training:

```mermaid
graph TD
    A[Raw genomes (FASTA) or k-mer TSV] --> B[Reconstruct pseudo-genes
    per genome (DNABERTProcessor)]
    C[Phenotype table (S/I/R)] --> D[Align phenotypes
    to genome IDs]
    B --> E[Create gene-level dataset
    (gene_sequence, antibiotic, label)]
    D --> E
    E --> F[Chunk genomes if max_genomes set
    + subsample genes per antibiotic]
    F --> G[DNABERTTrainer
    - tokenize genes into k-mers (k=6)
    - fine-tune DNABERT per antibiotic
    - early stopping & metrics]
    G --> H[Save Transformer models
    + metadata]
    F --> I[Optional: build genome embeddings
    and store in Qdrant
    for similarity search]
```

Prediction:

```mermaid
graph TD
    P[Input genome FASTA] --> Q[Extract genes (split genome into ~gene-sized chunks)]
    Q --> R[Tokenize all genes once
    using DNABERT tokenizer]
    R --> S[For each antibiotic model:
    - forward pass on all genes
    - per-gene class probabilities]
    S --> T[Aggregate gene predictions
    to genome-level S/I/R]
    T --> U[Return JSON response
    (+ optional gene-level details)]
```

---

## 3. Ensemble pipeline (XGBoost + Transformer)

High-level:

```mermaid
graph TD
    A[Input genome FASTA] --> B1[XGBoost branch
    (k-mer features)]
    A --> B2[DNABERT branch
    (gene-based)]

    B1 --> C1[Per-antibiotic S/I/R
    + XGBoost confidences]
    B2 --> C2[Per-antibiotic S/I/R
    + Transformer confidences]

    C1 --> D[Ensemble combiner]
    C2 --> D

    D --> E[Final per-antibiotic prediction
    (S/I/R + combined confidence)]
    E --> F[Return JSON response
    including branch-wise scores
    where available]
```

Notes:

- If only one model type is available (XGBoost or Transformer), the ensemble
  falls back to that branch alone.
- The exact combining rule can be adjusted (e.g. weighted average of probabilities,
  priority to a specific model, etc.).
