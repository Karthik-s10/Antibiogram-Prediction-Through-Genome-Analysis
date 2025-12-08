import random
from pathlib import Path

# Source FASTA to randomize
SRC = Path(r"e:\Antibiogram-Prediction-Through-Genome-Analysis\DATA\AP011121.fasta")
# Output FASTA path (same name with _random suffix)
DST = SRC.with_name(SRC.stem + "_random.fasta")

ALPHABET = "ACGT"


def make_random_fasta(src: Path, dst: Path) -> None:
    """Create a random-gibberish FASTA by preserving headers and randomizing bases."""
    if not src.exists():
        raise FileNotFoundError(f"Source FASTA not found: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    with src.open("r") as fin, dst.open("w") as fout:
        for line in fin:
            if line.startswith(">"):
                header = line[1:].strip()
                fout.write(f">{header}_random\n")
            else:
                seq = line.strip().upper()
                if not seq:
                    fout.write("\n")
                    continue
                rand_seq = "".join(random.choice(ALPHABET) for _ in seq)
                fout.write(rand_seq + "\n")


if __name__ == "__main__":
    make_random_fasta(SRC, DST)
    print(f"Wrote random FASTA to {DST}")
