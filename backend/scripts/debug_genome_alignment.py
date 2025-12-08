"""Small helper script to inspect how many genomes are available at each step.

It does NOT train anything. It just prints counts so you can see where
Genomes are lost between:

- Phenotype file (BVBRC_genome_amr.txt)
- Rosetta mapping file (BVBRC_genome.txt)
- K-mer file (SIGNIFICANT_DNA_KMERS_BACTERIA)

and how many GCA_ vs GCF_ accessions exist.

Usage (from backend venv, on Linux or Windows PowerShell):

    cd backend
    python -m scripts.debug_genome_alignment \
        --rosetta ../data/BVBRC_genome.txt \
        --phenotype ../data/BVBRC_genome_amr.txt \
        --kmer ../data/SIGNIFICANT_DNA_KMERS_BACTERIA

You can also point it at your uploaded files if needed.
"""

import argparse
from pathlib import Path

import pandas as pd


def load_rosetta(path: Path) -> pd.DataFrame:
    """Load Rosetta mapping with a few useful columns.

    We intentionally load the whole file (not just a subset of columns) so we
    can later experiment with alternate joins using Genome Name and Taxon IDs.
    """
    df = pd.read_csv(
        path,
        sep="\t",
        dtype=str,
        low_memory=False,
    )

    # Normalise a few key columns if they exist
    if "Genome ID" in df.columns:
        df["Genome ID"] = df["Genome ID"].astype(str).str.strip().str.replace("\"", "")
    if "Assembly Accession" in df.columns:
        df["Assembly Accession"] = df["Assembly Accession"].astype(str).str.strip().str.replace("\"", "")
    if "Genome Name" in df.columns:
        df["Genome Name"] = df["Genome Name"].astype(str).str.strip().str.replace("\"", "")
    if "NCBI Taxon ID" in df.columns:
        df["NCBI Taxon ID"] = df["NCBI Taxon ID"].astype(str).str.strip().str.replace("\"", "")

    # Keep only rows that have the core ID columns for the baseline mapping
    core_cols = [c for c in ["Genome ID", "Assembly Accession"] if c in df.columns]
    if core_cols:
        df = df.dropna(subset=core_cols)
    return df


def load_phenotype(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t", dtype=str, low_memory=False)
    df["Genome ID"] = df["Genome ID"].astype(str).str.strip().str.replace("\"", "")
    df["Antibiotic"] = df["Antibiotic"].astype(str).str.strip().str.replace("\"", "")
    df["Resistant Phenotype"] = df["Resistant Phenotype"].astype(str).str.strip()
    return df


def load_kmer(path: Path, max_rows: int | None = None) -> pd.DataFrame:
    # Use pandas to read the k-mer TSV; this may be large, but you can
    # optionally limit rows via --kmer-max-rows if needed.
    df = pd.read_csv(
        path,
        sep="\t",
        header=None,
        names=["Genome ID", "Domain", "k", "kmer_sequence", "prob1", "prob2"],
        nrows=max_rows,
        dtype={"Genome ID": str, "Domain": str, "k": int, "kmer_sequence": str, "prob1": float, "prob2": float},
        low_memory=False,
    )
    df["Genome ID"] = df["Genome ID"].astype(str).str.strip().str.replace("\"", "")
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rosetta", type=Path, required=True, help="Path to BVBRC_genome.txt")
    parser.add_argument("--phenotype", type=Path, required=True, help="Path to BVBRC_genome_amr.txt")
    parser.add_argument("--kmer", type=Path, required=True, help="Path to SIGNIFICANT_DNA_KMERS_BACTERIA")
    parser.add_argument(
        "--kmer-max-rows",
        type=int,
        default=None,
        help="Optional: limit number of k-mer rows to read (for quick testing)",
    )

    args = parser.parse_args()

    print("=== Loading Rosetta mapping ===")
    rosetta = load_rosetta(args.rosetta)
    print(f"Rosetta mappings: {len(rosetta):,}")

    gca_mask = rosetta["Assembly Accession"].str.startswith("GCA_")
    gcf_mask = rosetta["Assembly Accession"].str.startswith("GCF_")
    print(f"  GCA_ accessions: {gca_mask.sum():,}")
    print(f"  GCF_ accessions: {gcf_mask.sum():,}")

    print("\n=== Loading phenotype data ===")
    pheno = load_phenotype(args.phenotype)
    pheno_genomes = set(pheno["Genome ID"].dropna().unique())
    print(f"Phenotype records: {len(pheno):,}")
    print(f"Phenotype genomes (PATRIC IDs): {len(pheno_genomes):,}")

    # Baseline: Map phenotype Genome ID -> Assembly Accession via Rosetta
    id_map = {}
    if {"Genome ID", "Assembly Accession"}.issubset(rosetta.columns):
        id_map = dict(zip(rosetta["Genome ID"], rosetta["Assembly Accession"]))
    mapped_accessions = {id_map[g] for g in pheno_genomes if g in id_map and id_map[g]}
    print(f"\nPhenotype genomes with Rosetta mapping (by Genome ID): {len(mapped_accessions):,} / {len(pheno_genomes):,}")

    n_gca_mapped = sum(1 for acc in mapped_accessions if isinstance(acc, str) and acc.startswith("GCA_"))
    n_gcf_mapped = sum(1 for acc in mapped_accessions if isinstance(acc, str) and acc.startswith("GCF_"))
    print(f"  Mapped GCA_: {n_gca_mapped:,}")
    print(f"  Mapped GCF_: {n_gcf_mapped:,}")

    # Optional diagnostics: try to see if Genome Name or Taxon ID would
    # increase the potential matches beyond the strict Genome ID join.
    unmatched_genomes = pheno_genomes.difference(rosetta["Genome ID"].unique()) if "Genome ID" in rosetta.columns else set()

    # By Genome Name
    extra_accessions_by_name = set()
    extra_genomes_by_name = set()
    if "Genome Name" in pheno.columns and "Genome Name" in rosetta.columns:
        pheno_nm = pheno[["Genome ID", "Genome Name"]].copy()
        pheno_nm["Genome Name"] = pheno_nm["Genome Name"].astype(str).str.strip().str.replace("\"", "")
        rosetta_nm = rosetta[["Genome Name", "Assembly Accession"]].copy()
        rosetta_nm = rosetta_nm.dropna(subset=["Genome Name", "Assembly Accession"])
        rosetta_nm["Genome Name"] = rosetta_nm["Genome Name"].astype(str).str.strip().str.replace("\"", "")

        # Build a map from Genome Name -> set of Assembly Accessions
        name_to_acc = {}
        for _, row in rosetta_nm.iterrows():
            name = row["Genome Name"]
            acc = row["Assembly Accession"]
            if not name or not acc:
                continue
            name_to_acc.setdefault(name, set()).add(acc)

        # Look only at phenotype genomes that were NOT matched by Genome ID
        pheno_unmatched = pheno_nm[pheno_nm["Genome ID"].isin(unmatched_genomes)]
        for _, row in pheno_unmatched.iterrows():
            g_id = row["Genome ID"]
            name = row["Genome Name"]
            if not name:
                continue
            accs = name_to_acc.get(name)
            if accs:
                extra_genomes_by_name.add(g_id)
                extra_accessions_by_name.update(accs)

    # By Taxon ID (coarse, many genomes share a taxon)
    extra_genomes_by_taxon = set()
    extra_accessions_by_taxon = set()
    if "Taxon ID" in pheno.columns and "NCBI Taxon ID" in rosetta.columns and "Assembly Accession" in rosetta.columns:
        pheno_tax = pheno[["Genome ID", "Taxon ID"]].copy()
        pheno_tax["Taxon ID"] = pheno_tax["Taxon ID"].astype(str).str.strip().str.replace("\"", "")
        rosetta_tax = rosetta[["NCBI Taxon ID", "Assembly Accession"]].copy()
        rosetta_tax = rosetta_tax.dropna(subset=["NCBI Taxon ID", "Assembly Accession"])
        rosetta_tax["NCBI Taxon ID"] = rosetta_tax["NCBI Taxon ID"].astype(str).str.strip().str.replace("\"", "")

        # Build Taxon ID -> set(Assembly Accession)
        tax_to_acc = {}
        for _, row in rosetta_tax.iterrows():
            tax = row["NCBI Taxon ID"]
            acc = row["Assembly Accession"]
            if not tax or not acc:
                continue
            tax_to_acc.setdefault(tax, set()).add(acc)

        # Consider only phenotype genomes that were unmatched by Genome ID
        pheno_unmatched_tax = pheno_tax[pheno_tax["Genome ID"].isin(unmatched_genomes)]
        for _, row in pheno_unmatched_tax.iterrows():
            g_id = row["Genome ID"]
            tax = row["Taxon ID"]
            if not tax:
                continue
            accs = tax_to_acc.get(tax)
            if accs:
                extra_genomes_by_taxon.add(g_id)
                extra_accessions_by_taxon.update(accs)

    if extra_genomes_by_name or extra_genomes_by_taxon:
        print("\n=== Extra potential matches (diagnostics only) ===")
        if extra_genomes_by_name:
            print(
                "By Genome Name: potential phenotype genomes with a name match in Rosetta (but no Genome ID match): "
                f"{len(extra_genomes_by_name):,}"
            )
            print(
                "  Unique Assembly Accessions reachable via name-only matches: "
                f"{len(extra_accessions_by_name):,}"
            )
        if extra_genomes_by_taxon:
            print(
                "By Taxon ID (very coarse): phenotype genomes sharing Taxon ID with at least one Rosetta row: "
                f"{len(extra_genomes_by_taxon):,}"
            )

    print("\n=== Loading k-mer data ===")
    kmer = load_kmer(args.kmer, max_rows=args.kmer_max_rows)
    kmer_genomes = set(kmer["Genome ID"].dropna().unique())
    print(f"K-mer records: {len(kmer):,}")
    print(f"K-mer genomes (accessions): {len(kmer_genomes):,}")

    kmer_gca = {g for g in kmer_genomes if g.startswith("GCA_")}
    kmer_gcf = {g for g in kmer_genomes if g.startswith("GCF_")}
    print(f"  K-mer GCA_: {len(kmer_gca):,}")
    print(f"  K-mer GCF_: {len(kmer_gcf):,}")

    # OR-based potential mapping using Genome ID OR Genome Name OR Taxon ID
    potential_accessions_or = set(mapped_accessions)
    potential_accessions_or.update(extra_accessions_by_name)
    potential_accessions_or.update(extra_accessions_by_taxon)

    if potential_accessions_or != mapped_accessions:
        print("\n=== OR-based potential mapping (Genome ID OR Genome Name OR Taxon ID) ===")
        print(f"Unique Assembly Accessions reachable (any key): {len(potential_accessions_or):,}")
        potential_aligned_or = potential_accessions_or.intersection(kmer_genomes)
        print(f"Potential aligned genomes with k-mers (any key): {len(potential_aligned_or):,}")
        pot_gca = {g for g in potential_aligned_or if g.startswith("GCA_")}
        pot_gcf = {g for g in potential_aligned_or if g.startswith("GCF_")}
        print(f"  Potential aligned GCA_: {len(pot_gca):,}")
        print(f"  Potential aligned GCF_: {len(pot_gcf):,}")

    print("\n=== Alignment between mapped phenotypes and k-mers ===")
    aligned = mapped_accessions.intersection(kmer_genomes)
    print(f"Aligned genomes (Assembly Accession in both phenotype+Rosetta and k-mer): {len(aligned):,}")

    aligned_gca = {g for g in aligned if g.startswith("GCA_")}
    aligned_gcf = {g for g in aligned if g.startswith("GCF_")}
    print(f"  Aligned GCA_: {len(aligned_gca):,}")
    print(f"  Aligned GCF_: {len(aligned_gcf):,}")

    # Detailed list of all aligned genomes with basic metadata from Rosetta
    if "Assembly Accession" in rosetta.columns:
        aligned_rows = rosetta[rosetta["Assembly Accession"].isin(aligned)].copy()
        if not aligned_rows.empty:
            cols = ["Assembly Accession"]
            for c in ["Genome ID", "Genome Name", "NCBI Taxon ID"]:
                if c in aligned_rows.columns:
                    cols.append(c)
            aligned_display = aligned_rows[cols].drop_duplicates().fillna("")

            sort_col = "Genome Name" if "Genome Name" in aligned_display.columns else "Assembly Accession"
            aligned_display = aligned_display.sort_values(by=sort_col)

            print("\n=== Aligned genome rows (detailed from Rosetta) ===")
            print(f"Unique rows: {len(aligned_display):,}")
            for _, row in aligned_display.iterrows():
                acc = row.get("Assembly Accession", "")
                gid = row.get("Genome ID", "")
                gname = row.get("Genome Name", "")
                tax = row.get("NCBI Taxon ID", "")
                print(
                    f"  {acc}\tGenome ID={gid}\tGenome Name={gname}\tNCBI Taxon ID={tax}"
                )

            # Now also show every phenotype row for genomes that map to these aligned accessions
            print("\n=== Phenotype rows for aligned genomes ===")
            # Reuse the Genome ID -> Assembly Accession map
            gid_to_acc = {}
            if {"Genome ID", "Assembly Accession"}.issubset(rosetta.columns):
                gid_to_acc = dict(zip(rosetta["Genome ID"], rosetta["Assembly Accession"]))

            aligned_genome_ids = {gid for gid, acc in gid_to_acc.items() if acc in aligned}
            pheno_aligned = pheno[pheno["Genome ID"].isin(aligned_genome_ids)].copy()
            print(f"Total phenotype rows for aligned genomes: {len(pheno_aligned):,}")

            if not pheno_aligned.empty:
                # Print each row so you can inspect all tests used per genome
                # We limit to a focused set of columns for readability.
                cols_pheno = [
                    "Genome ID",
                    "Genome Name" if "Genome Name" in pheno_aligned.columns else None,
                    "Taxon ID" if "Taxon ID" in pheno_aligned.columns else None,
                    "Antibiotic",
                    "Resistant Phenotype",
                    "Measurement",
                    "Measurement Sign",
                    "Measurement Value",
                    "Measurement Unit",
                    "Evidence",
                ]
                cols_pheno = [c for c in cols_pheno if c is not None and c in pheno_aligned.columns]

                pheno_aligned = pheno_aligned[cols_pheno].fillna("")

            # Also write all phenotype rows for aligned genomes to a text file
            output_path = Path("aligned_phenotype_rows.txt")
            with output_path.open("w", encoding="utf-8") as fh:
                fh.write("Phenotype rows for aligned genomes\n")
                fh.write(f"Total phenotype rows: {len(pheno_aligned):,}\n")
                fh.write("Columns: " + ", ".join(cols_pheno) + "\n")

                # Grouped print: by Genome ID, then rows
                for gid in sorted(pheno_aligned["Genome ID"].unique()):
                    subset = pheno_aligned[pheno_aligned["Genome ID"] == gid]
                    header = f"\n-- Genome ID={gid} (phenotype rows: {len(subset):,}) --"
                    print(header)
                    fh.write(header + "\n")
                    for _, row in subset.iterrows():
                        fields = [f"{col}={row[col]}" for col in cols_pheno]
                        line = "  " + "; ".join(fields)
                        print(line)
                        fh.write(line + "\n")

            print(f"\nDetailed phenotype rows written to: {output_path.resolve()}")

    missing_in_kmer = mapped_accessions.difference(kmer_genomes)
    print(f"\nPhenotype genomes (mapped to accessions) missing in k-mer file: {len(missing_in_kmer):,}")

    print("\nDone.")


if __name__ == "__main__":
    main()
