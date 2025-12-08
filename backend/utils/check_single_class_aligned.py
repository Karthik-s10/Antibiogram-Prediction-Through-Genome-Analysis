import sys
from pathlib import Path

import pandas as pd  # type: ignore

# Ensure backend and project roots are importable
CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from preprocessing.phenotype_parser import PhenotypeParser
from preprocessing.kmer_processor import KmerProcessor


# Antibiotics which were "single_class" in the Transformer metrics table
# but show MULTIPLE classes in the raw BVBRC file.
ANTIBIOTICS_TO_CHECK = [
    "apramycin",
    "cefoperazone",
    "norfloxacin",
    "prothionamide",
]


def main() -> None:
    root = PROJECT_ROOT
    pheno_path = root / "DATA" / "BVBRC_genome_amr.txt"
    kmer_path = root / "DATA" / "kmer_dataset_taxon_k10_p1e-5_all.txt"

    if not pheno_path.exists():
        print(f"Phenotype file not found at: {pheno_path}", file=sys.stderr)
        sys.exit(1)
    if not kmer_path.exists():
        print(f"K-mer file not found at: {kmer_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading phenotype data from: {pheno_path}")
    print(f"Reading k-mer data from:     {kmer_path}")

    parser = PhenotypeParser()
    pheno_content = pheno_path.read_bytes()
    phenotype_df = parser.parse_phenotype_file(pheno_content)

    # Build the set/order of genomes that actually have k-mers
    kmer_processor = KmerProcessor(k=10)
    kmer_content = kmer_path.read_bytes()
    kmer_df = kmer_processor.parse_kmer_file(kmer_content)
    feature_genome_ids = (
        kmer_df["genome_id"].astype(str).str.strip().unique().tolist()
    )

    print(f"Total genomes with k-mers: {len(feature_genome_ids)}")
    print(f"Total phenotype genomes:    {phenotype_df['genome_id'].nunique()}")

    # Align using the same logic as XGBoost training (but without building X)
    aligned_genome_ids, label_matrix, antibiotic_names = parser.align_data(
        feature_genome_ids, phenotype_df
    )

    print(f"Aligned genomes (features ∩ phenotypes): {len(aligned_genome_ids)}")
    print(f"Number of antibiotics in aligned label matrix: {len(antibiotic_names)}")

    name_to_index = {name: idx for idx, name in enumerate(antibiotic_names)}

    for ab in ANTIBIOTICS_TO_CHECK:
        key = ab.lower()
        print("\n" + "=" * 80)
        print(f"Antibiotic: {ab} (lookup key in label matrix: '{key}')")

        if key not in name_to_index:
            print("Not present in aligned antibiotic list (no overlapping data with k-mer genomes).")
            continue

        idx = name_to_index[key]
        y_col = label_matrix[:, idx]
        mask = y_col != -1
        used = y_col[mask]

        print(f"Total aligned genomes with ANY label for this antibiotic: {used.size}")

        if used.size == 0:
            print("=> No genomes were used for this antibiotic after alignment.")
            continue

        # Count encoded classes 0/1/2
        counts = pd.Series(used).value_counts().sort_index()
        print("Encoded class counts among aligned genomes (0=S, 1=I, 2=R):")
        print(counts.to_string())

        if counts.size == 1:
            print("=> SINGLE CLASS after alignment to k-mer genomes.")
        else:
            print("=> MULTIPLE CLASSES after alignment to k-mer genomes.")


if __name__ == "__main__":
    main()
