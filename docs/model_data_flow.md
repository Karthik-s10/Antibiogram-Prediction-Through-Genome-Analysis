# Model Data Flow: XGBoost, DNABERT, and Qdrant

This document summarizes how data moves through the project:

- From offline k-mer and phenotype files into **training** (XGBoost and DNABERT).
- From an uploaded **FASTA** genome into **prediction**.

It focuses on the two main model families:

- **XGBoost** (classical ML, bag-of-k-mers).
- **DNABERT** (Transformer classifier + embedding for similarity search).

---

## 1. Training Data Flow

### 1.1 Inputs

- `DATA/SIGNIFICANT_DNA_KMERS_BACTERIA`
  - TSV: `genome_id\tdomain\tk\tkmer_sequence\tprob1\tprob2`
  - Example: `GCA_000002515.1\tBacteria\t10\tACCCCGCGCG\t1.43e-07\t9.83e-03`

- `DATA/BVBRC_genome_amr.txt`
  - Phenotype file from BV-BRC (S/I/R labels).
  - Combined with `BVBRC_genome.txt` (Rosetta) to map PATRIC IDs → GCA IDs.

### 1.2 XGBoost training

```text
SIGNIFICANT_DNA_KMERS_BACTERIA              BVBRC_genome_amr.txt
(genome_id, domain, k, kmer_seq, ...)       (Genome ID, Antibiotic, Phenotype, ...)
                 │                                         │
                 │ load_kmer_data()                        │ load_and_map_phenotypes() + Rosetta
                 ▼                                         ▼
           kmer_df (k-mer rows)                      mapped_pheno_df (with GCA IDs)
                 │                                         │
                 └───────────────┬─────────────────────────┘
                                 │ create_label_matrix()
                                 ▼
                        Y_df (genome × antibiotics)
                                 │
          create_feature_matrix(kmer_df, target_genomes = Y_df.index)
                                 ▼
                     X_df (genome × k-mers)
                                 │
                     align X_df and Y_df
                                 ▼
                        X_aligned, y
                                 │
                   [chunking: max_genomes, cycle_index]
                                 │
                                 ▼
                        XGBoostTrainer
                 train_per_antibiotic(X_aligned, y)
                                 │
                                 ▼
                XGBoost models + feature_info.json
```

Key points:

- Uses **k-mer frequencies (prob2)** as numeric features.
- One XGBoost classifier **per antibiotic**.
- Chunking (`max_genomes`, `cycle_index`) controls which genomes are used to keep memory manageable.

### 1.3 DNABERT training

```text
SIGNIFICANT_DNA_KMERS_BACTERIA              BVBRC_genome_amr.txt
(genome_id, domain, k, kmer_seq, ...)       (Genome ID, Antibiotic, Phenotype, ...)
                 │                                         │
                 │ DNABERTProcessor                        │ DataPreprocessor + Rosetta
                 ▼                                         ▼
     genome_to_genes: Dict[genome_id → [gene_seq]]   phenotype_df (genome_id, antibiotic, label)
                 │                                         │
                 └──────────────────────┬──────────────────┘
                                        │ create_gene_dataset()
                                        ▼
                          gene_df (gene_sequence, antibiotic, label)
                                        │
                         [chunking: max_genomes, cycle_index]
                                        │
                                        ▼
                         DNABERTTrainer (base_model = DNA_bert_6)
                         - tokenize each gene into 6-mers
                         - train per-antibiotic classifier heads
                                        │
                                        ▼
                            Saved DNABERT models (per antibiotic)
```

Key points:

- K-mer file is used to **reconstruct gene-like sequences**, not directly as features.
- DNABERTTrainer then tokenizes genes into **6-mer tokens** for the DNABERT-6 backbone.
- One Transformer classifier head per antibiotic.

---

## 2. Prediction Data Flow from FASTA

When a user uploads a FASTA genome to `/api/predict`, the backend can run:

- **XGBoost only** (`model_mode = "xgboost"`).
- **Transformer only** (`model_mode = "transformer"`).
- **Both / ensemble** (`model_mode = "both"`).
- **Auto** (choose best available).

### 2.1 XGBoost prediction

```text
Uploaded FASTA
      │
      ▼
KmerProcessor(k = settings.kmer_size_xgboost = 10)
  .extract_kmers_from_fasta()
(sliding window 10-mers → counts)
      │
      ▼
kmer_counts_to_feature_vector(kmer_counts, feature_names from feature_info.json)
(align to training columns, missing k-mers = 0)
      │
      ▼
XGBoostTrainer.predict / predict_proba
      │
      ▼
Genome-level S/I/R per antibiotic (+ probabilities)
```

Notes:

- This path **does not use embeddings or cosine similarity**.
- Predictions come directly from the XGBoost trees.

### 2.2 Transformer prediction (DNABERT classifier)

```text
Uploaded FASTA
      │
      ▼
DNABERTProcessor(k = settings.kmer_size_dnabert, max_length = 512)
  .extract_genes_from_fasta()
      │
      ▼
  gene_sequences: List[str]
      │
      ▼
DNABERTTrainer.load_models(saved_model_path)
  - restores DNABERT-6 backbone
  - restores per-antibiotic classifier heads
  - restores kmer_size used for tokenization (currently 6)
      │
      ▼
For each gene_sequence:
  - convert to k-mer tokens (6-mers for DNABERT-6)
  - run through DNABERT to get per-gene class scores
      │
      ▼
Aggregate gene-level predictions → genome-level S/I/R per antibiotic
```

Notes:

- This is the **Transformer classifier branch**.
- Final S/I/R labels and per-class probabilities come from DNABERT.

### 2.3 DNABERT embeddings + Qdrant similarity

Independently of the classifier, the system can compute an embedding and do similarity search:

```text
Uploaded FASTA
      │
      ▼
EmbeddingService.embed_fasta(fasta_content)
  - DNABERT-6 backbone
  - 6-mer tokenization
  - outputs 768-dim vector
      │
      ▼
QdrantService.search_similar_genomes(query_embedding, top_k = 5)
      │
      ▼
List of similar training genomes with similarity scores
```

Notes:

- This is the **embedding branch**.
- It uses a DNABERT-based encoder and Qdrant to find nearest neighbours.
- It **does not modify** the classifier’s S/I/R probabilities.
- Similar genomes are returned as extra context.

---

## 3. Ensemble Mode: How Results Are Combined

When `model_mode = "both"`, the code in `backend/api/prediction_routes.py` does:

1. **Transformer side**
   - Load DNABERT models.
   - Extract genes from FASTA.
   - Optionally run Qdrant similarity search using DNABERT embeddings.
   - Run `predict_genome_with_proba` to get per-antibiotic:
     - Class index (0=S, 1=I, 2=R).
     - Class probability vector `[p(S), p(I), p(R)]`.

2. **XGBoost side**
   - Load XGBoost models.
   - Extract 10-mers from FASTA.
   - Build feature vector.
   - Run `predict` / `predict_proba` to get per-antibiotic:
     - Class index.
     - Class probability vector.

3. **Markers (explainability)**
   - XGBoost: intersect top k-mers with k-mers present in the query.
   - Transformer: collect genes predicted R/I, optional BLAST annotations.

4. **Final per-antibiotic decision**

   ```text
   if Transformer prediction exists for this antibiotic:
       use Transformer label and probabilities as FINAL
   elif XGBoost prediction exists:
       use XGBoost label and probabilities as FINAL
   else:
       skip antibiotic
   ```

   - Qdrant similarity results and marker data are **attached to the response**,
     but they do **not** change the S/I/R label or probabilities.

---

## 4. Summary

- **XGBoost path**
  - Uses k-mer frequency vectors.
  - Outputs S/I/R per antibiotic and confidences.
  - Does not use embeddings or cosine similarity.

- **Transformer (DNABERT) classifier path**
  - Uses reconstructed gene sequences from k-mers or directly from FASTA.
  - Tokenizes into k-mers (currently 6-mers for DNABERT-6).
  - Outputs S/I/R per antibiotic and confidences.

- **Embedding + Qdrant path**
  - Uses DNABERT-6 as an encoder.
  - Produces genome-level embedding vectors.
  - Finds similar genomes via vector similarity in Qdrant.
  - Provides **context**, not the primary decision.

- **Ensemble (XGBoost + Transformer)**
  - Runs both models when available.
  - **Final S/I/R label and probabilities come from the Transformer** if present,
    otherwise from XGBoost.
  - Embeddings and similarity search are informational; they do not change the
    classifier’s confidence scores.
