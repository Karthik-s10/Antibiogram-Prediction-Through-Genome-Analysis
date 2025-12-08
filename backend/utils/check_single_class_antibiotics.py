import sys
from pathlib import Path

import pandas as pd  # type: ignore


# Ensure the backend package is on sys.path so we can import preprocessing
CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from preprocessing.phenotype_parser import PhenotypeParser


# Antibiotics reported as "single_class" in the per-antibiotic performance table
SINGLE_CLASS_ANTIBIOTICS = [
    "apramycin",
    "cefalexin",
    "cefdinir",
    "cefoperazone",
    "cefuroximâ",
    "cephalosporin",
    "dicloxacillin",
    "gatifloxacin",
    "macrolides",
    "norfloxacin",
    "prothionamide",
    "sparfloxacin",
    "sulbactam",
    "tgecycline",
    "tilmicosin",
    "trovafloxacin",
]


def main() -> None:
    # Resolve project root as two levels up from this file
    root = Path(__file__).resolve().parents[2]
    pheno_path = root / "DATA" / "BVBRC_genome_amr.txt"

    if not pheno_path.exists():
        print(f"Phenotype file not found at: {pheno_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading phenotype data from: {pheno_path}")

    parser = PhenotypeParser()
    content = pheno_path.read_bytes()

    # Parse and encode phenotypes using the same logic as training
    phenotype_df = parser.parse_phenotype_file(content)
    encoded_df = parser.encode_phenotypes(phenotype_df)

    # encoded_df['antibiotic'] is already lowercased in parse_phenotype_file
    encoded_df['antibiotic'] = encoded_df['antibiotic'].astype(str).str.strip().str.lower()

    all_antibiotics = sorted(encoded_df['antibiotic'].unique())
    print(f"Total distinct antibiotics in file: {len(all_antibiotics)}")

    for ab in SINGLE_CLASS_ANTIBIOTICS:
        ab_key = ab.lower()
        sub = encoded_df[encoded_df['antibiotic'] == ab_key]

        print("\n" + "=" * 80)
        print(f"Antibiotic: {ab} (lookup key: '{ab_key}')")

        if sub.empty:
            print("No encoded phenotype records found for this antibiotic in BVBRC_genome_amr.txt.")
            continue

        # Raw phenotype strings
        pheno_counts = sub['phenotype'].value_counts().sort_index()
        # Encoded classes 0/1/2
        class_counts = sub['encoded'].value_counts().sort_index()

        print("Phenotype value counts:")
        print(pheno_counts.to_string())

        print("\nEncoded class counts (0=S, 1=I, 2=R):")
        print(class_counts.to_string())

        if class_counts.size == 1:
            print("\n=> SINGLE CLASS in raw encoded data.")
        else:
            print("\n=> MULTIPLE CLASSES present in raw encoded data.")


if __name__ == "__main__":
    main()
