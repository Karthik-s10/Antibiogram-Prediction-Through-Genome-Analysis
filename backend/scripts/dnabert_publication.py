"""
dnabert_publication.py
-----------------------
Publication-quality DNABERT attention-rollup visualizations for antibiotic
resistance prediction.

Uses *real* per-antibiotic DNABERT checkpoints from:
    trained_models/transformer_<job_id>/antibiotics/<idx>_<name>/

and gene sequences extracted from the project genome:
    DATA/AP011121.fasta  (Acetobacter pasteurianus, ~50 genes)

Generated charts (all 300 DPI, publication-ready):
  1. dnabert_attention_per_antibiotic.pdf
       – Heatmap (genes × tokens) per antibiotic, one page per antibiotic
  2. dnabert_top_tokens.png
       – Top-20 most-attended k-mer tokens per antibiotic (grid of bar charts)
  3. dnabert_token_sharing.png
       – Cross-antibiotic attention heatmap (antibiotics × top-50 global tokens)
  4. dnabert_gene_spotlight.png
       – Attention weight sequence plot for the most informative gene per antibiotic

Usage:
    cd backend
    python scripts/dnabert_publication.py [--output-dir ../shap_output] [--n-genes 10] [--dpi 300]
"""

import argparse
import logging
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.gridspec import GridSpec

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent
_PROJECT_DIR = _BACKEND_DIR.parent
sys.path.insert(0, str(_BACKEND_DIR))

try:
    from config import settings  # type: ignore
    MODEL_DIR = Path(settings.model_storage_path)
except Exception:
    MODEL_DIR = _PROJECT_DIR / "trained_models"

# Try to import PyTorch / Transformers (optional — graceful fallback)
try:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Publication style
# ---------------------------------------------------------------------------
plt.rcParams.update({
    "font.family":        "DejaVu Sans",
    "font.size":          9,
    "axes.titlesize":     10,
    "axes.labelsize":     9,
    "xtick.labelsize":    7,
    "ytick.labelsize":    7,
    "figure.dpi":         100,
    "savefig.dpi":        300,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.alpha":         0.3,
})

CMAP_ATTN     = "YlOrRd"
CMAP_SHARE    = "Blues"
CMAP_SPOT     = "viridis"

# Drug class groupings for coherent ordering
DRUG_CLASSES = {
    "Aminoglycosides":   ["amikacin", "aminoglycosides", "apramycin", "gentamicin",
                          "kanamycin", "neomycin", "netilmicin", "streptomycin", "tobramycin"],
    "Beta-Lactams":      ["amoxicillin", "amoxicillin/clavulanic acid", "ampicillin",
                          "ampicillin/sulbactam", "aztreonam", "beta-lactam", "carbenicillin",
                          "cefazolin", "cefdinir", "cefepime", "cefixime", "cefotaxime",
                          "cefotaxime/clavulanic acid", "cefoxitin", "ceftaroline",
                          "ceftazidime", "ceftazidime/avibactam", "ceftriaxone", "cefuroxime",
                          "cephalexin", "cephalosporin", "cephalothin", "doripenem",
                          "ertapenem", "imipenem", "meropenem", "methicillin", "oxacillin",
                          "penicillin", "piperacillin", "piperacillin/tazobactam",
                          "ticarcillin", "ticarcillin/clavulanic acid"],
    "Fluoroquinolones":  ["ciprofloxacin", "enrofloxacin", "fluoroquinolones", "gatifloxacin",
                          "levofloxacin", "moxifloxacin", "nalidixic acid", "norfloxacin",
                          "ofloxacin"],
    "Macrolides":        ["azithromycin", "clarithromycin", "erythromycin", "macrolides",
                          "spiramycin", "telithromycin", "tilmicosin", "tylosin"],
    "Tetracyclines":     ["chlortetracycline", "doxycycline", "minocycline", "oxytetracycline",
                          "tetracycline", "tigecycline"],
    "TB Drugs":          ["bedaquiline", "capreomycin", "cycloserine", "delamanid",
                          "ethambutol", "ethionamide", "isoniazid", "pyrazinamide",
                          "rifabutin", "rifampin"],
    "Glycopeptides":     ["dalbavancin", "teicoplanin", "vancomycin"],
    "Other":             [],   # catch-all
}


def classify_antibiotic(name: str) -> str:
    n = name.lower()
    for cls, members in DRUG_CLASSES.items():
        if any(n == m or n.startswith(m) for m in members):
            return cls
    return "Other"


# ---------------------------------------------------------------------------
# DNABERT checkpoint discovery
# ---------------------------------------------------------------------------

def find_job_dir() -> Path | None:
    candidates = sorted(MODEL_DIR.glob("transformer_*"))
    return candidates[0] if candidates else None


def list_antibiotic_dirs(job_dir: Path):
    ab_dir = job_dir / "antibiotics"
    if not ab_dir.is_dir():
        return []
    return sorted(ab_dir.iterdir())


def dir_to_name(d: Path) -> str:
    """Strip leading index from directory name (e.g. '003_amoxicillin' → 'amoxicillin')."""
    return re.sub(r"^\d+_", "", d.name).replace("_", " ")


# ---------------------------------------------------------------------------
# Genome / gene sequence loading
# ---------------------------------------------------------------------------

def load_gene_sequences(n_genes: int = 10) -> list[str]:
    """Extract gene sequences from the project FASTA file."""
    fasta_path = _PROJECT_DIR / "DATA" / "AP011121.fasta"
    if not fasta_path.exists():
        logger.warning("FASTA not found at %s; using synthetic sequences.", fasta_path)
        return ["ATCGATCGATCG" * 50] * n_genes

    fasta_content = fasta_path.read_text(encoding="utf-8", errors="replace")

    try:
        from preprocessing.dnabert_processor import DNABERTProcessor  # type: ignore
        genes = DNABERTProcessor(k=6, max_length=512).extract_genes_from_fasta(fasta_content)
        logger.info("Extracted %d genes from FASTA (using first %d)", len(genes), n_genes)
        return genes[:n_genes]
    except Exception as exc:
        logger.warning("DNABERTProcessor failed (%s); splitting raw sequence every 500 bp", exc)
        raw = re.sub(r"[^ATCG]", "", fasta_content.upper())
        chunks = [raw[i: i + 500] for i in range(0, len(raw), 500) if len(raw[i: i + 500]) >= 50]
        return chunks[:n_genes]


# ---------------------------------------------------------------------------
# Tokenisation + attention rollup
# ---------------------------------------------------------------------------

def tokenize_sequence(sequence: str, tokenizer) -> dict:
    clean = re.sub(r"[^ATCG]", "", sequence.upper())
    if "ATCGAT" in tokenizer.get_vocab():
        k = 6
        kmers = [clean[i: i + k] for i in range(len(clean) - k + 1)]
        sentence = " ".join(kmers) if kmers else clean
    else:
        sentence = clean
    return tokenizer(sentence, return_tensors="pt", padding=True, truncation=True, max_length=512)


def attention_rollup(attentions) -> np.ndarray:
    avg = torch.stack([a.squeeze(0).mean(dim=0) for a in attentions], dim=0)
    rollup = avg.sum(dim=0)
    importance = rollup.sum(dim=0).cpu().numpy().astype(float)
    total = importance.sum()
    if total > 0:
        importance /= total
    return importance


def run_inference(model, inputs, tokenizer):
    """Returns (pred_label, importance_array, tokens)."""
    tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
    with torch.no_grad():
        outputs = model(**inputs)
    logits = outputs.logits
    probs = torch.softmax(logits, dim=-1)
    pred_idx = int(torch.argmax(probs, dim=-1)[0])
    pred_label = {0: "S", 1: "I", 2: "R"}.get(pred_idx, "?")
    pred_conf = float(probs[0, pred_idx])

    if hasattr(outputs, "attentions") and outputs.attentions:
        importance = attention_rollup(outputs.attentions)
    else:
        importance = np.ones(len(tokens)) / len(tokens)

    if len(importance) > len(tokens):
        importance = importance[:len(tokens)]
    elif len(importance) < len(tokens):
        importance = np.pad(importance, (0, len(tokens) - len(importance)))
    return pred_label, pred_conf, importance, tokens


# ---------------------------------------------------------------------------
# Data collection: run all DNABERT models over all genes
# ---------------------------------------------------------------------------

def collect_attention_data(ab_dirs, gene_sequences, job_dir):
    """
    Returns a list of dicts, one per processed antibiotic:
      {
        'name':        str,
        'dir':         Path,
        'drug_class':  str,
        'gene_matrix': np.ndarray(n_genes, n_tokens),  # attention weights
        'tokens':      List[str],
        'pred_labels': List[str],   # per-gene prediction
        'pred_confs':  List[float],
        'top_tokens':  Dict[str, float],  # aggregate token → mean attention
      }
    """
    if not HAS_TORCH:
        raise RuntimeError("PyTorch and Transformers are required for DNABERT visualizations.")

    tok_path = job_dir / "tokenizer"
    if not tok_path.is_dir():
        raise FileNotFoundError(f"Tokenizer not found at {tok_path}")
    tokenizer = AutoTokenizer.from_pretrained(str(tok_path))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Using device: %s", device)

    results = []

    for ab_dir in ab_dirs:
        ab_name = dir_to_name(ab_dir)
        ckpt_files = list(ab_dir.glob("model.safetensors")) + list(ab_dir.glob("pytorch_model.bin"))
        if not ckpt_files:
            logger.debug("Skipping %s — no checkpoint found", ab_name)
            continue

        logger.info("Processing: %s", ab_name)
        try:
            model = AutoModelForSequenceClassification.from_pretrained(
                str(ab_dir),
                output_attentions=True,
                ignore_mismatched_sizes=True,
            ).to(device).eval()
        except Exception as exc:
            logger.warning("Could not load model for %s: %s", ab_name, exc)
            continue

        gene_matrix_rows = []
        shared_tokens = None
        pred_labels = []
        pred_confs = []

        for seq in gene_sequences:
            try:
                inputs = tokenize_sequence(seq, tokenizer)
                inputs = {k: v.to(device) for k, v in inputs.items()}
                pred_label, pred_conf, importance, tokens = run_inference(model, inputs, tokenizer)
                pred_labels.append(pred_label)
                pred_confs.append(pred_conf)
                if shared_tokens is None:
                    shared_tokens = tokens
                gene_matrix_rows.append(importance[:len(shared_tokens)])
            except Exception as exc:
                logger.debug("Inference failed for gene: %s", exc)
                continue

        # Free GPU memory
        del model
        if device == "cuda":
            torch.cuda.empty_cache()

        if not gene_matrix_rows:
            continue

        gene_matrix = np.array(gene_matrix_rows)  # (n_genes, n_tokens)

        # Aggregate top tokens
        mean_per_token = gene_matrix.mean(axis=0)
        top_tokens = {
            t: float(v)
            for t, v in sorted(zip(shared_tokens, mean_per_token), key=lambda x: x[1], reverse=True)[:20]
        }

        results.append({
            "name":        ab_name,
            "dir":         ab_dir,
            "drug_class":  classify_antibiotic(ab_name),
            "gene_matrix": gene_matrix,
            "tokens":      shared_tokens,
            "pred_labels": pred_labels,
            "pred_confs":  pred_confs,
            "top_tokens":  top_tokens,
        })

    return results


# ---------------------------------------------------------------------------
# Chart 1 — Per-antibiotic attention heatmap PDF
# ---------------------------------------------------------------------------

def plot_attention_heatmap_pdf(results, out_path: Path, gene_sequences):
    logger.info("Generating Chart 1: Per-antibiotic attention heatmap PDF...")

    with PdfPages(out_path) as pdf:
        # Cover page
        fig_c, ax_c = plt.subplots(figsize=(8.5, 11))
        ax_c.axis("off")
        cover_text = (
            "DNABERT Attention-Rollup Visualizations\n"
            "Antibiotic Resistance Prediction\n\n"
            "Model:        transformer_ce13dcc6\n"
            f"Checkpoints:  {len(results)} per-antibiotic DNABERT models\n"
            "Method:       Attention Rollup (averaged heads, all layers)\n"
            f"Genome:       AP011121 — Acetobacter pasteurianus\n"
            f"Genes used:   {len(gene_sequences)}\n\n"
            "Each page:\n"
            "  • Heatmap: rows = genes, cols = 6-mer tokens\n"
            "  • Color intensity ∝ attention weight\n"
            "  • Title shows most common prediction (S/I/R)\n"
        )
        ax_c.text(0.08, 0.88, cover_text, transform=ax_c.transAxes,
                  fontsize=11, va="top", ha="left", family="monospace",
                  bbox=dict(facecolor="#f0f0f0", edgecolor="#aaa", boxstyle="round,pad=0.8"))
        ax_c.set_title("Antibiogram Prediction Through Genome Analysis", fontsize=14, fontweight="bold", pad=20)
        pdf.savefig(fig_c, bbox_inches="tight")
        plt.close(fig_c)

        for entry in results:
            ab_name   = entry["name"]
            mat       = entry["gene_matrix"]
            tokens    = entry["tokens"]
            labels    = entry["pred_labels"]
            confs     = entry["pred_confs"]

            n_genes, n_tok = mat.shape
            dominant = max(set(labels), key=labels.count) if labels else "?"
            mean_conf = np.mean(confs) if confs else 0.0
            drug_cls  = entry["drug_class"]

            # Limit tokens shown for readability (max 80)
            max_tok = min(n_tok, 80)
            mat_show = mat[:, :max_tok]
            tok_show = tokens[:max_tok]

            fig_w = max(12, max_tok * 0.14)
            fig_h = max(4, n_genes * 0.45)
            fig, ax = plt.subplots(figsize=(fig_w, fig_h))

            im = ax.imshow(mat_show, cmap=CMAP_ATTN, aspect="auto",
                           interpolation="nearest", vmin=0)
            fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01,
                         label="Attention Weight (normalized)")

            ax.set_yticks(range(n_genes))
            ax.set_yticklabels([f"Gene {i+1}  [{labels[i] if i < len(labels) else '?'}]"
                                for i in range(n_genes)], fontsize=7)
            ax.set_xticks(range(0, max_tok, max(1, max_tok // 20)))
            ax.set_xticklabels(tok_show[::max(1, max_tok // 20)],
                               rotation=45, ha="right", fontsize=6, family="monospace")
            ax.set_xlabel("6-mer Token (position)", fontsize=9)
            ax.set_ylabel("Gene", fontsize=9)
            ax.set_title(
                f"DNABERT Attention — {ab_name.title()}  [{drug_cls}]\n"
                f"Dominant prediction: {dominant}  |  Mean confidence: {mean_conf:.3f}",
                fontsize=11, fontweight="bold", pad=10
            )

            fig.text(0.5, 0.01,
                     "transformer_ce13dcc6 | AP011121 genome | attention rollup",
                     ha="center", fontsize=7, color="#888")

            plt.tight_layout(rect=[0, 0.03, 1, 1])
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    logger.info("Saved: %s", out_path)


# ---------------------------------------------------------------------------
# Chart 2 — Top-20 attended tokens grid
# ---------------------------------------------------------------------------

def plot_top_tokens_grid(results, out_path: Path):
    logger.info("Generating Chart 2: Top-20 attended tokens grid...")

    n_ab = len(results)
    ncols = 5
    nrows = (n_ab + ncols - 1) // ncols

    fig_w = ncols * 4.5
    fig_h = nrows * 3.2
    fig, axes = plt.subplots(nrows, ncols, figsize=(fig_w, fig_h))
    axes_flat = axes.flatten() if n_ab > 1 else [axes]

    # Sort by drug class then name
    sorted_results = sorted(results, key=lambda e: (e["drug_class"], e["name"]))

    for ax, entry in zip(axes_flat, sorted_results):
        top_tokens = entry["top_tokens"]
        tokens = list(top_tokens.keys())[:20]
        vals   = list(top_tokens.values())[:20]
        norm   = np.array(vals) / (max(vals) + 1e-9)
        colors = plt.cm.get_cmap(CMAP_ATTN)(0.15 + 0.75 * norm)

        bars = ax.barh(range(len(tokens)), vals, color=colors, edgecolor="white", linewidth=0.4)
        ax.set_yticks(range(len(tokens)))
        ax.set_yticklabels(tokens, fontsize=5.5, family="monospace")
        ax.invert_yaxis()

        # Dominant prediction badge
        labels_list = entry.get("pred_labels", [])
        dominant = max(set(labels_list), key=labels_list.count) if labels_list else "?"
        badge_color = {"R": "#e05252", "I": "#f0a500", "S": "#27ae60"}.get(dominant, "#888")
        ax.set_title(f"{entry['name'].title()}", fontsize=7.5, fontweight="bold", pad=4)
        ax.text(1.0, 1.0, dominant, transform=ax.transAxes, fontsize=9, fontweight="bold",
                color=badge_color, ha="right", va="top")
        ax.set_xlabel("Attention", fontsize=6)
        ax.tick_params(axis="x", labelsize=6)
        ax.set_axisbelow(True)

    # Hide unused subplots
    for extra_ax in axes_flat[len(sorted_results):]:
        extra_ax.axis("off")

    fig.suptitle(
        "Top-20 DNABERT Attended 6-mer Tokens per Antibiotic\n"
        "(Sorted by drug class | Badge = dominant prediction)",
        fontsize=12, fontweight="bold", y=1.01
    )
    plt.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved: %s", out_path)


# ---------------------------------------------------------------------------
# Chart 3 — Cross-antibiotic token sharing heatmap
# ---------------------------------------------------------------------------

def plot_token_sharing_heatmap(results, out_path: Path, top_global: int = 50):
    logger.info("Generating Chart 3: Cross-antibiotic token sharing heatmap...")

    # Aggregate global token importance
    global_tok: dict = defaultdict(float)
    for entry in results:
        for tok, val in entry["top_tokens"].items():
            global_tok[tok] += val

    top_global_tokens = [t for t, _ in sorted(global_tok.items(), key=lambda x: x[1], reverse=True)[:top_global]]

    n_ab  = len(results)
    n_tok = len(top_global_tokens)
    matrix = np.zeros((n_ab, n_tok))

    sorted_results = sorted(results, key=lambda e: (e["drug_class"], e["name"]))
    for i, entry in enumerate(sorted_results):
        for j, tok in enumerate(top_global_tokens):
            matrix[i, j] = entry["top_tokens"].get(tok, 0.0)

    fig_w = max(16, n_tok * 0.28)
    fig_h = max(10, n_ab * 0.30)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    im = ax.imshow(matrix, cmap=CMAP_SHARE, aspect="auto", vmin=0)
    cbar = fig.colorbar(im, ax=ax, fraction=0.015, pad=0.01)
    cbar.set_label("Mean Attention Weight", fontsize=9)

    ax.set_xticks(range(n_tok))
    ax.set_xticklabels(top_global_tokens, rotation=55, ha="right", fontsize=6, family="monospace")
    ax.set_yticks(range(n_ab))
    ab_labels = [f"{e['name'].title()}  [{e['drug_class'][:3]}]" for e in sorted_results]
    ax.set_yticklabels(ab_labels, fontsize=6.5)

    ax.set_title(
        f"Cross-Antibiotic DNABERT Attention: Top-{top_global} Global Tokens\n"
        f"(Row = antibiotic, Col = 6-mer token | sorted by drug class)",
        fontsize=11, fontweight="bold", pad=12
    )
    ax.set_xlabel("6-mer Token", fontsize=9)
    ax.set_ylabel("Antibiotic [Class]", fontsize=9)

    # Add drug class separators
    class_boundaries = []
    prev_cls = sorted_results[0]["drug_class"] if sorted_results else None
    for i, e in enumerate(sorted_results):
        if e["drug_class"] != prev_cls:
            class_boundaries.append(i - 0.5)
            prev_cls = e["drug_class"]
    for b in class_boundaries:
        ax.axhline(b, color="white", linewidth=1.5, linestyle="--")

    plt.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved: %s", out_path)


# ---------------------------------------------------------------------------
# Chart 4 — Gene spotlight: per-position attention for select antibiotics
# ---------------------------------------------------------------------------

def plot_gene_spotlight(results, gene_sequences, out_path: Path):
    logger.info("Generating Chart 4: Gene spotlight...")

    if not results or not gene_sequences:
        logger.warning("No data for gene spotlight; skipping.")
        return

    # Select representative gene — use gene 0 (first gene = most stable signal)
    gene_idx = 0
    n_display = min(15, len(results))
    # Sort by dominant label diversity for an informative selection
    sorted_results = sorted(results, key=lambda e: e["name"])[:n_display]

    fig_h = n_display * 1.8
    fig, axes = plt.subplots(n_display, 1, figsize=(16, fig_h), sharex=False)
    if n_display == 1:
        axes = [axes]

    for ax, entry in zip(axes, sorted_results):
        mat = entry["gene_matrix"]
        if gene_idx >= len(mat):
            gene_idx = 0
        attention = mat[gene_idx]
        tokens    = entry["tokens"]

        n_tok = min(len(attention), len(tokens), 80)
        x     = np.arange(n_tok)
        y     = attention[:n_tok]
        tok   = tokens[:n_tok]

        norm = plt.Normalize(vmin=y.min(), vmax=y.max())
        colors = plt.cm.get_cmap(CMAP_SPOT)(norm(y))

        ax.bar(x, y, color=colors, width=0.85, linewidth=0)
        ax.set_xlim(-0.5, n_tok - 0.5)
        ax.set_xticks(x[::max(1, n_tok // 15)])
        ax.set_xticklabels(tok[::max(1, n_tok // 15)],
                           rotation=55, ha="right", fontsize=5.5, family="monospace")

        label_list = entry.get("pred_labels", [])
        dominant = max(set(label_list), key=label_list.count) if label_list else "?"
        conf = np.mean(entry.get("pred_confs", [0.0]))
        badge_color = {"R": "#e05252", "I": "#f0a500", "S": "#27ae60"}.get(dominant, "#888")

        ax.set_ylabel("Attention", fontsize=7)
        ax.set_title(
            f"{entry['name'].title()}  [{entry['drug_class']}]  →  {dominant}  (conf {conf:.2f})",
            fontsize=8, fontweight="bold", color=badge_color, pad=3
        )
        ax.tick_params(axis="y", labelsize=6)
        ax.set_axisbelow(True)

    fig.suptitle(
        f"DNABERT Attention Spotlight — Gene {gene_idx+1} of AP011121\n"
        f"(Per-position attention weight, top {n_display} antibiotics alphabetically)",
        fontsize=12, fontweight="bold"
    )
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved: %s", out_path)


# ---------------------------------------------------------------------------
# HTML index
# ---------------------------------------------------------------------------

def generate_index_dnabert(outputs: dict, out_dir: Path, n_ab: int, n_genes: int):
    items = "\n".join(
        f'<li><a href="{Path(p).name}" target="_blank">{name}</a></li>'
        for name, p in outputs.items()
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>DNABERT Publication Figures</title>
<style>
  body{{font-family:"Segoe UI",sans-serif;background:#0d1117;color:#e6edf3;padding:40px;max-width:900px;margin:auto}}
  h1{{color:#58a6ff;border-bottom:1px solid #30363d;padding-bottom:12px}}
  h2{{color:#79c0ff;margin-top:28px}}
  table{{border-collapse:collapse;width:100%;margin-bottom:20px}}
  td,th{{padding:8px 14px;text-align:left;border:1px solid #30363d;font-size:14px}}
  th{{background:#161b22;color:#8b949e}}
  a{{color:#58a6ff;text-decoration:none}}
  ul{{line-height:2.2;font-size:15px}}
</style>
</head>
<body>
<h1>DNABERT Attention Visualizations</h1>
<p>Antibiogram Prediction Through Genome Analysis — Transformer Attention Rollup</p>
<h2>Model Summary</h2>
<table>
  <tr><th>Field</th><th>Value</th></tr>
  <tr><td>Model</td><td><code>transformer_ce13dcc6</code></td></tr>
  <tr><td>Antibiotics</td><td>{n_ab}</td></tr>
  <tr><td>Method</td><td>Attention rollup (avg heads, all layers)</td></tr>
  <tr><td>Genome</td><td>AP011121 — Acetobacter pasteurianus</td></tr>
  <tr><td>Genes Used</td><td>{n_genes}</td></tr>
</table>
<h2>Generated Figures</h2>
<ul>
{items}
</ul>
</body>
</html>"""
    idx = out_dir / "dnabert_index.html"
    idx.write_text(html, encoding="utf-8")
    logger.info("Index saved: %s", idx)
    return idx


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate DNABERT attention publication figures.")
    parser.add_argument("--output-dir",  default="shap_output", help="Output directory")
    parser.add_argument("--dpi",         type=int, default=300,  help="Output DPI")
    parser.add_argument("--n-genes",     type=int, default=10,   help="Number of genes to analyze per antibiotic")
    parser.add_argument("--top-global",  type=int, default=50,   help="Top global tokens for sharing heatmap")
    args = parser.parse_args()

    if not HAS_TORCH:
        print("ERROR: PyTorch and Transformers are required for DNABERT visualizations.")
        print("  pip install torch transformers")
        sys.exit(1)

    plt.rcParams["savefig.dpi"] = args.dpi

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    job_dir = find_job_dir()
    if job_dir is None:
        print("ERROR: No transformer_* directory found in:", MODEL_DIR)
        sys.exit(1)
    logger.info("Using DNABERT job dir: %s", job_dir)

    ab_dirs = list_antibiotic_dirs(job_dir)
    logger.info("Found %d antibiotic checkpoints", len(ab_dirs))

    # Load gene sequences
    gene_sequences = load_gene_sequences(n_genes=args.n_genes)
    logger.info("Using %d gene sequences", len(gene_sequences))

    # ---- Run inference to collect all attention data ----
    logger.info("Running attention rollup inference... (this may take several minutes)")
    results = collect_attention_data(ab_dirs, gene_sequences, job_dir)
    logger.info("Collected attention data for %d antibiotics", len(results))

    if not results:
        print("ERROR: No attention data collected — check DNABERT checkpoints.")
        sys.exit(1)

    outputs = {}

    # Chart 1
    p1 = out_dir / "dnabert_attention_per_antibiotic.pdf"
    plot_attention_heatmap_pdf(results, p1, gene_sequences)
    outputs["Per-Antibiotic Attention Heatmap (PDF)"] = str(p1)

    # Chart 2
    p2 = out_dir / "dnabert_top_tokens.png"
    plot_top_tokens_grid(results, p2)
    outputs["Top-20 Attended Token Grid"] = str(p2)

    # Chart 3
    p3 = out_dir / "dnabert_token_sharing.png"
    plot_token_sharing_heatmap(results, p3, top_global=args.top_global)
    outputs["Cross-Antibiotic Token Sharing Heatmap"] = str(p3)

    # Chart 4
    p4 = out_dir / "dnabert_gene_spotlight.png"
    plot_gene_spotlight(results, gene_sequences, p4)
    outputs["Gene Spotlight (per-position attention)"] = str(p4)

    # Index
    generate_index_dnabert(outputs, out_dir, len(results), len(gene_sequences))

    print(f"\nAll DNABERT figures saved to '{out_dir}/'")
    print(f"   Open: {out_dir / 'dnabert_index.html'}")
    for name, path in outputs.items():
        print(f"   - {name}: {path}")


if __name__ == "__main__":
    main()
