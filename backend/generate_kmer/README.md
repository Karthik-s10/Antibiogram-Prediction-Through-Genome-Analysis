# Generate K-mer Dataset from BV-BRC Phenotype Data

This pipeline downloads genome sequences from the BV-BRC FTP server using PATRIC Genome IDs
from your phenotype file, then generates k-mers (k=21) with probabilities.

## Output Format

The final output matches the format expected by the training pipeline:

```
taxon_id    Bacteria    21    KMER_SEQUENCE    probability
562         Bacteria    21    AAAAAAAAAAAAAAAAAAAAA    1.23e-05
562         Bacteria    21    AAAAAAAAAAAAAAAAAAAAT    9.87e-06
...
```

## Prerequisites

1. **Python packages**:
   ```bash
   pip install pandas requests tqdm
   ```

2. **KMC3** (K-mer Counter):
   - Linux: `conda install -c bioconda kmc`
   - Or download from: https://github.com/refresh-bio/KMC/releases

3. **Your phenotype file** (`BVBRC_genome_amr.txt`) with columns:
   - `Taxon ID`
   - `Genome ID`
   - `Genome Name`

## Usage

### Step 1: Download Genomes

```bash
cd backend/generate_kmer

python download_genomes.py \
  --phenotype ../DATA/BVBRC_genome_amr.txt \
  --output-dir downloaded_genomes \
  --max-genomes 100  # Optional: limit for testing
```

This downloads `.fna` FASTA files from BV-BRC FTP for each unique Genome ID.

### Step 2: Generate K-mers

```bash
python generate_kmers.py \
  --phenotype ../DATA/BVBRC_genome_amr.txt \
  --genomes-dir downloaded_genomes \
  --output kmer_dataset.txt \
  --k 21
```

This:
- Runs KMC3 on each FASTA file
- Calculates k-mer probabilities
- Outputs in the format: `taxon_id  Bacteria  k  kmer_sequence  probability`

### Step 3 (Optional): Run Full Pipeline

```bash
python run_pipeline.py \
  --phenotype ../DATA/BVBRC_genome_amr.txt \
  --output-dir pipeline_output \
  --k 21 \
  --max-genomes 0  # 0 = all genomes
```

## How It Works

1. **Read Phenotype File**: Extracts unique `(Taxon ID, Genome ID, Genome Name)` tuples.

2. **Download from BV-BRC FTP**:
   - URL pattern: `ftp://ftp.bvbrc.org/genomes/{GENOME_ID}/{GENOME_ID}.fna`
   - Example: `ftp://ftp.bvbrc.org/genomes/562.144628/562.144628.fna`

3. **Count K-mers with KMC3**:
   - `kmc -k21 -ci1 -fm input.fna output_db temp_dir`
   - `kmc_tools transform output_db dump output.txt`

4. **Calculate Probability**:
   - For each k-mer: `probability = count / total_kmers_in_genome`

5. **Output**: Tab-separated file with columns matching your training pipeline.

## Expected Results

- **Number of genomes**: All unique Genome IDs from your phenotype file that have FASTA on BV-BRC.
- **K-mer count per genome**: Depends on genome size; typically millions of 21-mers per genome.
- **Total rows**: (unique genomes) × (k-mers per genome) — can be very large!

## Tips

- Start with `--max-genomes 10` to test the pipeline.
- The download step can be slow; files are cached so re-runs skip existing files.
- For large datasets, consider running on a server with sufficient disk space.
