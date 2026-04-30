"""
shap_publication.py
--------------------
Publication-quality SHAP visualisation for antibiotic resistance predictions.

Reads pre-computed explainability data from:
  trained_models/xgboost_f0849bdd_explainability.json   (78 antibiotics, top-20 k-mers each)
  trained_models/xgboost_f0849bdd_metadata.json         (model metadata)

Generates 5 charts, all saved at 300 DPI for publication:
  1. heatmap_top_kmers.png          — Global importance heatmap (top 30 k-mers × all antibiotics)
  2. barplots_per_antibiotic.pdf    — Top-20 SHAP bar chart per antibiotic (multi-page PDF)
  3. summary_grid_top10.png         — Top-10 k-mers per antibiotic summary grid
  4. kmer_sharing_heatmap.png       — Jaccard similarity of k-mer sets across antibiotics
  5. violin_importance.png          — Importance distribution violin per antibiotic

Usage:
    python scripts/shap_publication.py [--output-dir shap_output] [--dpi 300] [--top-n 20]
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np
import matplotlib
matplotlib.use("Agg")   # non-interactive backend — safe on all platforms
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.ticker as ticker
import seaborn as sns

# ---------------------------------------------------------------------------
# Resolve backend directory so we can import config
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent
sys.path.insert(0, str(_BACKEND_DIR))

try:
    from config import settings  # type: ignore
    MODEL_DIR = Path(settings.model_storage_path)
except Exception:
    MODEL_DIR = _BACKEND_DIR.parent / "trained_models"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Publication style constants
# ---------------------------------------------------------------------------

# Color palette — accessible, publication-standard
CMAP_MAIN   = "YlOrRd"          # warm scale for importance
CMAP_DIV    = "RdBu_r"          # diverging for heatmap
CMAP_SHARE  = "Blues"           # sequential for Jaccard

FONT_FAMILY = "DejaVu Sans"
plt.rcParams.update({
    "font.family":        FONT_FAMILY,
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
    "legend.fontsize":    8,
})

LABEL_COLORS = {
    "Resistant":     "#e05252",
    "Intermediate":  "#f0a500",
    "Susceptible":   "#27ae60",
}

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_explainability(model_dir: Path):
    """Load explainability JSON → {antibiotic: [{feature, importance}]}"""
    path = model_dir / "xgboost_f0849bdd_explainability.json"
    if not path.exists():
        raise FileNotFoundError(f"Explainability file not found: {path}")
    with open(path, "r") as f:
        data = json.load(f)
    return data


def load_metadata(model_dir: Path) -> dict:
    path = model_dir / "xgboost_f0849bdd_metadata.json"
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return json.load(f)


def build_tables(data: dict, top_n: int = 20):
    """
    Returns:
      antibiotics  - sorted list of antibiotic names that have data
      ab_features  - {ab: [(kmer, importance), ...]} sorted desc, length <= top_n
      all_kmers    - ordered list of all unique k-mers appearing in any top-feature list
    """
    antibiotics_raw = data.get("antibiotics", {})
    antibiotics = sorted(antibiotics_raw.keys())

    ab_features = {}
    for ab in antibiotics:
        entry = antibiotics_raw[ab]
        feats = entry.get("top_features", [])
        # Sort by importance descending
        feats_sorted = sorted(feats, key=lambda x: float(x.get("importance", 0)), reverse=True)
        ab_features[ab] = [(f["feature"], float(f["importance"])) for f in feats_sorted[:top_n]]

    # Collect all unique k-mers preserving discovery order (by global rank)
    kmer_global: dict = {}
    for ab in antibiotics:
        for rank, (kmer, imp) in enumerate(ab_features[ab]):
            if kmer not in kmer_global:
                kmer_global[kmer] = 0.0
            kmer_global[kmer] += imp  # aggregate global importance

    all_kmers = sorted(kmer_global.keys(), key=lambda k: kmer_global[k], reverse=True)
    return antibiotics, ab_features, all_kmers


# ---------------------------------------------------------------------------
# Chart 1 — Global importance heatmap
# ---------------------------------------------------------------------------

def plot_global_heatmap(antibiotics, ab_features, all_kmers, out_path: Path, top_kmers: int = 30):
    logger.info("Generating Chart 1: Global k-mer importance heatmap...")

    sel_kmers = all_kmers[:top_kmers]
    n_ab = len(antibiotics)
    n_km = len(sel_kmers)

    # Build matrix
    matrix = np.zeros((n_km, n_ab), dtype=float)
    for j, ab in enumerate(antibiotics):
        imp_map = dict(ab_features[ab])
        for i, kmer in enumerate(sel_kmers):
            matrix[i, j] = imp_map.get(kmer, 0.0)

    # Dynamic figure size
    fig_h = max(10, n_km * 0.35)
    fig_w = max(16, n_ab * 0.22)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    im = ax.imshow(matrix, cmap=CMAP_MAIN, aspect="auto", interpolation="nearest")

    cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01)
    cbar.set_label("Mean SHAP Importance", fontsize=9)

    ax.set_xticks(range(n_ab))
    ax.set_xticklabels(antibiotics, rotation=55, ha="right", fontsize=6.5)
    ax.set_yticks(range(n_km))
    ax.set_yticklabels(sel_kmers, fontsize=7, family="monospace")
    ax.set_title(
        f"XGBoost SHAP Feature Importance: Top {top_kmers} k-mers across {n_ab} Antibiotics\n"
        f"(Model: xgboost_f0849bdd | Genomes: 3,204 | k-mer features: 155,211)",
        fontsize=11, pad=12, fontweight="bold"
    )
    ax.set_xlabel("Antibiotic", fontsize=9)
    ax.set_ylabel("10-mer Sequence", fontsize=9)

    # Grid lines between cells
    ax.set_xticks(np.arange(-0.5, n_ab, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_km, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.5)
    ax.tick_params(which="minor", bottom=False, left=False)

    plt.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# Chart 2 — Per-antibiotic bar charts (PDF, one page per antibiotic)
# ---------------------------------------------------------------------------

def plot_per_antibiotic_bars(antibiotics, ab_features, out_path: Path):
    logger.info("Generating Chart 2: Per-antibiotic SHAP bar charts (PDF)...")

    with PdfPages(out_path) as pdf:
        # First page — cover / metadata summary
        fig_cover, ax_c = plt.subplots(figsize=(8.5, 11))
        ax_c.axis("off")
        cover_text = (
            "SHAP Feature Importance — Antibiotic Resistance Prediction\n\n"
            "Model:        XGBoost (xgboost_f0849bdd)\n"
            "Training set: 3,204 bacterial genomes\n"
            "K-mer size:   10-bp\n"
            "Features:     155,211 unique k-mers\n"
            "Classes:      Susceptible (S) / Intermediate (I) / Resistant (R)\n"
            f"Antibiotics:  {len(antibiotics)} with SHAP data\n\n"
            "Each page shows the Top-20 k-mer features for one antibiotic,\n"
            "ranked by mean absolute SHAP importance score.\n\n"
            "Higher importance → k-mer is more predictive of resistance.\n"
        )
        ax_c.text(
            0.1, 0.88, cover_text, transform=ax_c.transAxes,
            fontsize=12, va="top", ha="left", family="monospace",
            bbox=dict(facecolor="#f5f5f5", edgecolor="#ccc", boxstyle="round,pad=0.8")
        )
        ax_c.set_title("Antibiogram Prediction Through Genome Analysis", fontsize=14, fontweight="bold", pad=20)
        pdf.savefig(fig_cover, bbox_inches="tight")
        plt.close(fig_cover)

        # One page per antibiotic
        for ab in antibiotics:
            feats = ab_features[ab]
            if not feats:
                continue

            kmers = [f[0] for f in feats]
            imps  = [f[1] for f in feats]

            # Color by rank (darker = more important)
            norm_imps = np.array(imps) / (max(imps) + 1e-9)
            colors = plt.cm.get_cmap(CMAP_MAIN)(0.2 + 0.7 * norm_imps)

            fig, ax = plt.subplots(figsize=(8.5, 7))
            bars = ax.barh(range(len(kmers)), imps, color=colors, edgecolor="white", linewidth=0.5)
            ax.set_yticks(range(len(kmers)))
            ax.set_yticklabels(kmers, fontsize=8, family="monospace")
            ax.invert_yaxis()   # rank 1 at top
            ax.set_xlabel("Mean Absolute SHAP Importance", fontsize=9)
            ax.set_title(
                f"SHAP Feature Importance — {ab.title()}\n"
                f"Top {len(feats)} k-mer predictors",
                fontsize=11, fontweight="bold", pad=10
            )

            # Value labels
            for bar, imp in zip(bars, imps):
                ax.text(
                    bar.get_width() + max(imps) * 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{imp:.4f}", va="center", ha="left", fontsize=7, color="#444"
                )

            ax.set_xlim(0, max(imps) * 1.18)
            ax.set_axisbelow(True)

            # Footnote
            fig.text(
                0.5, 0.01,
                f"xgboost_f0849bdd | Antibiogram Prediction Through Genome Analysis",
                ha="center", fontsize=7, color="#888"
            )

            plt.tight_layout(rect=[0, 0.03, 1, 1])
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    logger.info(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# Chart 3 — Summary grid: Top-10 k-mers per antibiotic
# ---------------------------------------------------------------------------

def plot_summary_grid(antibiotics, ab_features, out_path: Path, top_n: int = 10):
    logger.info("Generating Chart 3: Top-10 k-mer summary grid...")

    n_ab = len(antibiotics)
    n_rows = top_n  # one row per rank

    fig_w = max(20, n_ab * 0.55)
    fig_h = max(8, top_n * 0.65)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    # Build matrix for colors
    matrix = np.zeros((n_rows, n_ab))
    labels = [["" for _ in range(n_ab)] for _ in range(n_rows)]

    for j, ab in enumerate(antibiotics):
        feats = ab_features[ab][:top_n]
        for i, (kmer, imp) in enumerate(feats):
            matrix[i, j] = imp
            labels[i][j] = kmer

    # Normalize per row so that color reflects relative rank within each position
    row_max = matrix.max(axis=1, keepdims=True)
    row_max[row_max == 0] = 1.0
    norm_matrix = matrix / row_max

    im = ax.imshow(norm_matrix, cmap="YlGnBu", aspect="auto", vmin=0, vmax=1)

    # Overlay k-mer text
    for i in range(n_rows):
        for j in range(n_ab):
            txt = labels[i][j]
            if txt:
                brightness = norm_matrix[i, j]
                color = "white" if brightness > 0.6 else "#333"
                ax.text(j, i, txt, ha="center", va="center",
                        fontsize=5.5, family="monospace", color=color, weight="bold")

    ax.set_xticks(range(n_ab))
    ax.set_xticklabels(antibiotics, rotation=50, ha="right", fontsize=6)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([f"Rank {i+1}" for i in range(n_rows)], fontsize=7)

    cbar = fig.colorbar(im, ax=ax, fraction=0.01, pad=0.01)
    cbar.set_label("Relative Importance (per rank)", fontsize=8)

    ax.set_title(
        f"Top {top_n} SHAP K-mer Features per Antibiotic\n"
        f"(XGBoost | 3,204 genomes | 155,211 features)",
        fontsize=11, fontweight="bold", pad=12
    )
    ax.set_xlabel("Antibiotic", fontsize=9)
    ax.set_ylabel("Feature Rank", fontsize=9)

    plt.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# Chart 4 — K-mer sharing heatmap (Jaccard similarity)
# ---------------------------------------------------------------------------

def plot_kmer_sharing(antibiotics, ab_features, out_path: Path):
    logger.info("Generating Chart 4: K-mer sharing / Jaccard heatmap...")

    n = len(antibiotics)
    kmer_sets = {ab: set(k for k, _ in ab_features[ab]) for ab in antibiotics}

    # Compute Jaccard matrix
    jaccard = np.zeros((n, n))
    for i, a in enumerate(antibiotics):
        for j, b in enumerate(antibiotics):
            inter = len(kmer_sets[a] & kmer_sets[b])
            union = len(kmer_sets[a] | kmer_sets[b])
            jaccard[i, j] = inter / union if union > 0 else 0.0

    fig_size = max(14, n * 0.22)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size * 0.85))

    im = ax.imshow(jaccard, cmap=CMAP_SHARE, aspect="auto", vmin=0, vmax=1)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Jaccard Similarity (shared k-mers)", fontsize=9)

    ax.set_xticks(range(n))
    ax.set_xticklabels(antibiotics, rotation=55, ha="right", fontsize=6)
    ax.set_yticks(range(n))
    ax.set_yticklabels(antibiotics, fontsize=6)

    ax.set_title(
        "K-mer Signature Sharing Between Antibiotics\n"
        "(Jaccard similarity of Top-20 SHAP k-mer sets — higher = more shared resistance genes)",
        fontsize=11, fontweight="bold", pad=12
    )

    # Annotate high-similarity pairs (> 0.3) with value text
    for i in range(n):
        for j in range(n):
            val = jaccard[i, j]
            if (i != j) and val >= 0.3:
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=5, color="white" if val > 0.5 else "#222")

    plt.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# Chart 5 — Violin / boxplot of importance distribution per antibiotic
# ---------------------------------------------------------------------------

def plot_violin_importance(antibiotics, ab_features, out_path: Path):
    logger.info("Generating Chart 5: Importance distribution violin plot...")

    # Collect importance values per antibiotic
    data_by_ab = {ab: [imp for _, imp in ab_features[ab]] for ab in antibiotics}

    # Sort antibiotics by median importance (most concentrated signal first)
    sorted_abs = sorted(antibiotics, key=lambda ab: np.median(data_by_ab[ab]) if data_by_ab[ab] else 0, reverse=True)

    fig_w = max(22, len(antibiotics) * 0.28)
    fig, ax = plt.subplots(figsize=(fig_w, 7))

    positions = range(1, len(sorted_abs) + 1)
    data_vals = [data_by_ab[ab] for ab in sorted_abs]

    parts = ax.violinplot(data_vals, positions=list(positions), showmedians=True, showextrema=True)

    # Style
    for pc in parts["bodies"]:
        pc.set_facecolor("#3498db")
        pc.set_edgecolor("#1a5276")
        pc.set_alpha(0.7)
    parts["cmedians"].set_color("#e74c3c")
    parts["cmaxes"].set_color("#555")
    parts["cmins"].set_color("#555")
    parts["cbars"].set_color("#555")

    ax.set_xticks(list(positions))
    ax.set_xticklabels(sorted_abs, rotation=55, ha="right", fontsize=6.5)
    ax.set_ylabel("SHAP Importance Score", fontsize=9)
    ax.set_title(
        "Distribution of Top-20 SHAP Feature Importance Scores per Antibiotic\n"
        "(Red line = median, sorted by median importance — concentrated = strong predictor)",
        fontsize=11, fontweight="bold", pad=12
    )

    # Add summary stats as text at the top of each violin
    for pos, ab in zip(positions, sorted_abs):
        vals = data_by_ab[ab]
        if vals:
            med = np.median(vals)
            ax.text(pos, max(vals) * 1.02, f"{med:.3f}",
                    ha="center", va="bottom", fontsize=5.5, color="#555", rotation=90)

    ax.set_xlim(0, len(sorted_abs) + 1)
    plt.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# HTML index for the output directory
# ---------------------------------------------------------------------------

def generate_index(outputs: dict, out_dir: Path, metadata: dict):
    n_ab     = metadata.get("n_antibiotics", "?")
    n_feats  = metadata.get("n_features", "?")
    n_gen    = metadata.get("n_genomes", 3204)
    model_nm = metadata.get("model_name", "xgboost_f0849bdd")
    hp       = metadata.get("hyperparameters", {})

    items = "\n".join(
        f'<li><a href="{Path(p).name}" target="_blank">{name}</a></li>'
        for name, p in outputs.items()
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>SHAP Publication Figures</title>
<style>
  body{{font-family:"Segoe UI",sans-serif;background:#0d1117;color:#e6edf3;padding:40px;max-width:900px;margin:auto}}
  h1{{color:#58a6ff;border-bottom:1px solid #30363d;padding-bottom:12px}}
  h2{{color:#79c0ff;margin-top:28px}}
  table{{border-collapse:collapse;width:100%;margin-bottom:20px}}
  td,th{{padding:8px 14px;text-align:left;border:1px solid #30363d;font-size:14px}}
  th{{background:#161b22;color:#8b949e}}
  a{{color:#58a6ff;text-decoration:none}}
  a:hover{{color:#a5d6ff}}
  ul{{line-height:2.2;font-size:15px}}
  .badge{{background:#1f6feb;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px}}
</style>
</head>
<body>
<h1>SHAP Publication Visualizations</h1>
<p>Antibiogram Prediction Through Genome Analysis — XGBoost Feature Importance</p>

<h2>Model Summary</h2>
<table>
  <tr><th>Field</th><th>Value</th></tr>
  <tr><td>Model</td><td><code>{model_nm}</code></td></tr>
  <tr><td>Training Genomes</td><td>{n_gen:,}</td></tr>
  <tr><td>K-mer Features</td><td>{int(n_feats):,}</td></tr>
  <tr><td>Antibiotics Covered</td><td>{n_ab}</td></tr>
  <tr><td>Max Depth</td><td>{hp.get('max_depth', '?')}</td></tr>
  <tr><td>Learning Rate</td><td>{hp.get('learning_rate', '?')}</td></tr>
  <tr><td>Estimators</td><td>{hp.get('n_estimators', '?')}</td></tr>
</table>

<h2>Generated Figures</h2>
<ul>
{items}
</ul>
</body>
</html>"""

    idx_path = out_dir / "index.html"
    with open(idx_path, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"Index saved: {idx_path}")
    return idx_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate publication-quality SHAP visualizations.")
    parser.add_argument("--output-dir", default="shap_output", help="Output directory (default: shap_output)")
    parser.add_argument("--dpi", type=int, default=300, help="Output DPI (default: 300)")
    parser.add_argument("--top-n", type=int, default=20, help="Top N k-mers per antibiotic (default: 20)")
    parser.add_argument("--top-kmers-heatmap", type=int, default=30, help="Top K-mers for global heatmap (default: 30)")
    args = parser.parse_args()

    plt.rcParams["savefig.dpi"] = args.dpi

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Load data ---
    logger.info(f"Loading explainability data from {MODEL_DIR} ...")
    data     = load_explainability(MODEL_DIR)
    metadata = load_metadata(MODEL_DIR)

    antibiotics, ab_features, all_kmers = build_tables(data, top_n=args.top_n)
    logger.info(f"Loaded {len(antibiotics)} antibiotics, {len(all_kmers)} unique k-mers")

    outputs = {}

    # --- Chart 1 ---
    p1 = out_dir / "heatmap_top_kmers.png"
    plot_global_heatmap(antibiotics, ab_features, all_kmers, p1, top_kmers=args.top_kmers_heatmap)
    outputs["Global K-mer Heatmap (Top 30 x All Antibiotics)"] = str(p1)

    # --- Chart 2 ---
    p2 = out_dir / "barplots_per_antibiotic.pdf"
    plot_per_antibiotic_bars(antibiotics, ab_features, p2)
    outputs["Per-Antibiotic SHAP Bar Charts (PDF, all antibiotics)"] = str(p2)

    # --- Chart 3 ---
    p3 = out_dir / "summary_grid_top10.png"
    plot_summary_grid(antibiotics, ab_features, p3, top_n=10)
    outputs["Top-10 K-mer Summary Grid"] = str(p3)

    # --- Chart 4 ---
    p4 = out_dir / "kmer_sharing_heatmap.png"
    plot_kmer_sharing(antibiotics, ab_features, p4)
    outputs["K-mer Sharing / Jaccard Heatmap"] = str(p4)

    # --- Chart 5 ---
    p5 = out_dir / "violin_importance.png"
    plot_violin_importance(antibiotics, ab_features, p5)
    outputs["Importance Distribution (Violin Plot)"] = str(p5)

    # --- Index ---
    generate_index(outputs, out_dir, {**metadata, "n_genomes": 3204})

    print(f"\nAll SHAP publication figures saved to '{out_dir}/'")
    print(f"   Open: {out_dir / 'index.html'}")
    for name, path in outputs.items():
        print(f"   - {name}: {path}")


if __name__ == "__main__":
    main()
