"""
best_charts.py
--------------
Generates exactly two definitive publication charts:

  1. xgboost_shap_best.png  — SHAP bubble/dot heatmap: top-20 k-mers × 78 antibiotics
       Best for showing WHICH genomic features drive each antibiotic's resistance call.
       Uses the real mean-absolute SHAP values from xgboost_f0849bdd_explainability.json.

  2. dnabert_attention_best.png — Aggregated per-token attention bar chart
       Shows the top-50 6-mer tokens by mean attention weight (averaged across all 50
       genes and all 110 antibiotic models), colored by their per-drug-class breakdown.
       Uses the DNABERT models directly (attention rollup, same method as dnabert_publication.py).

Usage:
    cd backend
    python scripts/best_charts.py [--output-dir ../shap_output] [--n-genes 50]
"""

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent
_PROJECT_DIR = _BACKEND_DIR.parent
sys.path.insert(0, str(_BACKEND_DIR))

try:
    from config import settings   # type: ignore
    MODEL_DIR = Path(settings.model_storage_path)
except Exception:
    MODEL_DIR = _PROJECT_DIR / "trained_models"

try:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Publication style ────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family":     "DejaVu Sans",
    "font.size":       9,
    "axes.titlesize":  11,
    "axes.labelsize":  9,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7.5,
    "savefig.dpi":     300,
    "figure.dpi":      100,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# Drug class colour palette
CLASS_COLORS = {
    "Aminoglycosides":  "#2196F3",
    "Beta-Lactams":     "#F44336",
    "Fluoroquinolones": "#FF9800",
    "Macrolides":       "#9C27B0",
    "Tetracyclines":    "#795548",
    "TB Drugs":         "#607D8B",
    "Glycopeptides":    "#009688",
    "Phenicols":        "#E91E63",
    "Lincosamides":     "#673AB7",
    "Sulfonamides":     "#4CAF50",
    "Polymyxins":       "#FF5722",
    "Miscellaneous":    "#FFC107",
    "Other":            "#9E9E9E",
}

DRUG_CLASS_MAP = {
    "amikacin": "Aminoglycosides", "aminoglycosides": "Aminoglycosides",
    "apramycin": "Aminoglycosides", "gentamicin": "Aminoglycosides",
    "kanamycin": "Aminoglycosides", "neomycin": "Aminoglycosides",
    "netilmicin": "Aminoglycosides", "streptomycin": "Aminoglycosides",
    "tobramycin": "Aminoglycosides",
    "amoxicillin": "Beta-Lactams", "ampicillin": "Beta-Lactams",
    "aztreonam": "Beta-Lactams", "cefazolin": "Beta-Lactams",
    "cefdinir": "Beta-Lactams", "cefepime": "Beta-Lactams",
    "cefixime": "Beta-Lactams", "cefotaxime": "Beta-Lactams",
    "cefoxitin": "Beta-Lactams", "ceftaroline": "Beta-Lactams",
    "ceftazidime": "Beta-Lactams", "ceftriaxone": "Beta-Lactams",
    "cefuroxime": "Beta-Lactams", "cephalexin": "Beta-Lactams",
    "cephalosporin": "Beta-Lactams", "cephalothin": "Beta-Lactams",
    "doripenem": "Beta-Lactams", "ertapenem": "Beta-Lactams",
    "imipenem": "Beta-Lactams", "meropenem": "Beta-Lactams",
    "methicillin": "Beta-Lactams", "oxacillin": "Beta-Lactams",
    "penicillin": "Beta-Lactams", "piperacillin": "Beta-Lactams",
    "ticarcillin": "Beta-Lactams", "beta-lactam": "Beta-Lactams",
    "carbapenem": "Beta-Lactams", "carbenicillin": "Beta-Lactams",
    "ciprofloxacin": "Fluoroquinolones", "enrofloxacin": "Fluoroquinolones",
    "fluoroquinolones": "Fluoroquinolones", "gatifloxacin": "Fluoroquinolones",
    "levofloxacin": "Fluoroquinolones", "moxifloxacin": "Fluoroquinolones",
    "nalidixic acid": "Fluoroquinolones", "norfloxacin": "Fluoroquinolones",
    "ofloxacin": "Fluoroquinolones",
    "azithromycin": "Macrolides", "clarithromycin": "Macrolides",
    "erythromycin": "Macrolides", "macrolides": "Macrolides",
    "spiramycin": "Macrolides", "telithromycin": "Macrolides",
    "tilmicosin": "Macrolides", "tylosin": "Macrolides",
    "chlortetracycline": "Tetracyclines", "doxycycline": "Tetracyclines",
    "minocycline": "Tetracyclines", "oxytetracycline": "Tetracyclines",
    "tetracycline": "Tetracyclines", "tigecycline": "Tetracyclines",
    "bedaquiline": "TB Drugs", "capreomycin": "TB Drugs",
    "cycloserine": "TB Drugs", "delamanid": "TB Drugs",
    "ethambutol": "TB Drugs", "ethionamide": "TB Drugs",
    "isoniazid": "TB Drugs", "pyrazinamide": "TB Drugs",
    "rifabutin": "TB Drugs", "rifampin": "TB Drugs",
    "dalbavancin": "Glycopeptides", "teicoplanin": "Glycopeptides",
    "vancomycin": "Glycopeptides",
    # ── Combination Beta-Lactams (beta-lactam + inhibitor) ────────────────────
    "amoxicillin/clavulanic acid": "Beta-Lactams",
    "ampicillin/sulbactam": "Beta-Lactams",
    "cefotetan": "Beta-Lactams",
    "cefpodoxime": "Beta-Lactams",
    "cefpodoxime_clavulanic_acid": "Beta-Lactams",
    "ceftazidime/avibactam": "Beta-Lactams",
    "ceftiofur": "Beta-Lactams",
    "ceftolozane/tazobactam": "Beta-Lactams",
    "piperacillin/tazobactam": "Beta-Lactams",
    "ticarcillin/clavulanic acid": "Beta-Lactams",
    "timentin": "Beta-Lactams",
    # ── Phenicols ─────────────────────────────────────────────────────────────
    "chloramphenicol": "Phenicols",
    "florfenicol": "Phenicols",
    # ── Lincosamides ──────────────────────────────────────────────────────────
    "clindamycin": "Lincosamides",
    "quinupristin/dalfopristin": "Lincosamides",
    # ── Sulfonamides / folate inhibitors ──────────────────────────────────────
    "sulfamethoxazole": "Sulfonamides",
    "sulfisoxazole": "Sulfonamides",
    "sulfonamides": "Sulfonamides",
    "trimethoprim": "Sulfonamides",
    "trimethoprim/sulfamethoxazole": "Sulfonamides",
    "nicotinamide": "Sulfonamides",
    "para-aminosalicylic acid": "TB Drugs",
    # ── Polymyxins ────────────────────────────────────────────────────────────
    "colistin": "Polymyxins",
    "polymyxin b": "Polymyxins",
    # ── Miscellaneous ─────────────────────────────────────────────────────────
    "clofazimine": "TB Drugs",
    "daptomycin": "Miscellaneous",
    "fosfomycin": "Miscellaneous",
    "linezolid": "Miscellaneous",
    "nitrofurantoin": "Miscellaneous",
    "spectinomycin": "Aminoglycosides",
}


def classify(name: str) -> str:
    return DRUG_CLASS_MAP.get(name.lower().strip(), "Other")


# ═══════════════════════════════════════════════════════════════════════════════
# Chart 1 — XGBoost SHAP: detailed annotated heatmap (top-30 k-mers × antibiotics)
# ═══════════════════════════════════════════════════════════════════════════════

def make_xgboost_chart(out_path: Path, top_n_kmers: int = 30):
    """
    Detailed annotated heatmap:
      Rows  = top_n_kmers globally most-predictive k-mers
      Cols  = all antibiotics, sorted by drug class
      Cells = mean absolute SHAP value (colour + numeric label on non-zero cells)
      Right = horizontal bar: total SHAP per k-mer
      Top   = vertical bar: total SHAP per antibiotic
      Strip = drug-class colour band with embedded class labels
    """
    logger.info("Building detailed XGBoost SHAP heatmap (top %d k-mers)...", top_n_kmers)

    ej = MODEL_DIR / "xgboost_f0849bdd_explainability.json"
    with open(ej) as f:
        data = json.load(f)
    antibiotics_raw = data["antibiotics"]

    # Sort antibiotics: drug class first, then alphabetically
    ab_list = sorted(antibiotics_raw.keys(), key=lambda a: (classify(a), a))
    n_ab = len(ab_list)

    # Per-antibiotic importance dict + global aggregate
    ab_features: dict = {}
    global_kmer_score: dict = defaultdict(float)
    for ab in ab_list:
        feats = sorted(antibiotics_raw[ab].get("top_features", []),
                       key=lambda x: float(x["importance"]), reverse=True)
        ab_features[ab] = {f["feature"]: float(f["importance"]) for f in feats}
        for f in feats:
            global_kmer_score[f["feature"]] += float(f["importance"])

    # Top N k-mers by global sum-of-SHAP
    top_kmers = [k for k, _ in sorted(global_kmer_score.items(),
                                       key=lambda x: x[1], reverse=True)[:top_n_kmers]]
    n_km = len(top_kmers)

    # Importance matrix [n_km × n_ab]
    matrix = np.zeros((n_km, n_ab))
    for j, ab in enumerate(ab_list):
        for i, kmer in enumerate(top_kmers):
            matrix[i, j] = ab_features[ab].get(kmer, 0.0)

    row_sums = matrix.sum(axis=1)   # total SHAP per k-mer
    col_sums = matrix.sum(axis=0)   # total SHAP per antibiotic
    global_max = matrix.max() or 1.0

    # ── Figure layout ─────────────────────────────────────────────────────────
    fig_w = max(28, n_ab  * 0.30)
    fig_h = max(16, n_km  * 0.55)

    fig = plt.figure(figsize=(fig_w, fig_h), constrained_layout=False)

    # Axis coordinates (normalised)
    left, right = 0.09, 0.84
    heat_bottom, top_area = 0.10, 0.94
    strip_h, col_bar_h, gap = 0.028, 0.065, 0.005
    col_bar_top  = top_area - 0.04         # leave room for title
    col_bar_bot  = col_bar_top - col_bar_h
    strip_bot    = col_bar_bot - gap - strip_h
    heat_top     = strip_bot - gap
    heat_h       = heat_top - heat_bottom
    rbar_w       = 0.055
    cbar_w       = 0.012
    rbar_left    = right + 0.005
    cbar_left    = rbar_left + rbar_w + 0.01

    ax_colbar = fig.add_axes([left, col_bar_bot, right - left, col_bar_h])
    ax_strip  = fig.add_axes([left, strip_bot,   right - left, strip_h])
    ax_main   = fig.add_axes([left, heat_bottom, right - left, heat_h])
    ax_rowbar = fig.add_axes([rbar_left, heat_bottom, rbar_w, heat_h])
    ax_cbar   = fig.add_axes([cbar_left, heat_bottom, cbar_w, heat_h])

    # ── Top marginal bar: total SHAP per antibiotic ───────────────────────────
    bar_colors = [CLASS_COLORS.get(classify(ab), "#9E9E9E") for ab in ab_list]
    ax_colbar.bar(np.arange(n_ab), col_sums, color=bar_colors, width=0.75, alpha=0.85)
    ax_colbar.set_xlim(-0.5, n_ab - 0.5)
    ax_colbar.set_xticks([])
    ax_colbar.set_ylabel("Sum\nSHAP", fontsize=7)
    ax_colbar.yaxis.set_tick_params(labelsize=6)
    ax_colbar.set_title(
        "XGBoost SHAP Feature Importance — Detailed Annotated Heatmap\n"
        f"Top {top_n_kmers} k-mer predictors × {n_ab} antibiotics  |  "
        "Model: xgboost_f0849bdd  |  3,204 genomes  ·  155,211 k-mer features",
        fontsize=10, fontweight="bold", pad=8,
    )
    ax_colbar.spines["top"].set_visible(False)
    ax_colbar.spines["right"].set_visible(False)
    ax_colbar.grid(axis="y", linestyle="--", alpha=0.3)

    # ── Drug-class colour strip ───────────────────────────────────────────────
    strip_img = np.zeros((1, n_ab, 3))
    for j, ab in enumerate(ab_list):
        hex_c = CLASS_COLORS.get(classify(ab), "#9E9E9E").lstrip("#")
        strip_img[0, j] = [int(hex_c[k:k+2], 16) / 255 for k in (0, 2, 4)]
    ax_strip.imshow(strip_img, aspect="auto", interpolation="nearest")
    ax_strip.set_xticks([])
    ax_strip.set_yticks([])

    class_spans: dict = {}
    for j, ab in enumerate(ab_list):
        cls = classify(ab)
        if cls not in class_spans:
            class_spans[cls] = [j, j]
        class_spans[cls][1] = j
    for cls, (s, e) in class_spans.items():
        mid = (s + e) / 2
        light = cls in ("Other", "TB Drugs")
        ax_strip.text(mid, 0, cls, ha="center", va="center",
                      fontsize=6, fontweight="bold",
                      color="#111" if light else "white")

    # ── Main heatmap ──────────────────────────────────────────────────────────
    im = ax_main.imshow(matrix, cmap="YlOrRd", aspect="auto",
                        interpolation="nearest", vmin=0, vmax=global_max)

    # Drug-class dividers
    prev_cls = classify(ab_list[0])
    for j in range(1, n_ab):
        cls = classify(ab_list[j])
        if cls != prev_cls:
            ax_main.axvline(j - 0.5, color="white", linewidth=1.8, alpha=0.95)
            prev_cls = cls

    # Thin horizontal lines between k-mers
    for i in range(1, n_km):
        ax_main.axhline(i - 0.5, color="white", linewidth=0.35, alpha=0.45)

    # Annotate every non-zero cell with its SHAP value
    thresh = global_max * 0.48
    for i in range(n_km):
        for j in range(n_ab):
            v = matrix[i, j]
            if v > 0:
                txt_color = "white" if v > thresh else "#2c2c2c"
                ax_main.text(j, i, f"{v:.3f}", ha="center", va="center",
                             fontsize=4.2, color=txt_color, fontweight="bold",
                             family="monospace")

    ax_main.set_xticks(range(n_ab))
    ax_main.set_xticklabels([a.title() for a in ab_list],
                             rotation=50, ha="right", fontsize=5.8)
    ax_main.set_yticks(range(n_km))
    ax_main.set_yticklabels(top_kmers, fontsize=8.5, family="monospace")
    ax_main.set_xlabel("Antibiotic  (sorted by drug class)", fontsize=9, labelpad=8)
    ax_main.set_ylabel(f"Top {top_n_kmers} 10-mer Features  (ranked by global SHAP sum)",
                       fontsize=9)

    # ── Right marginal bar: total SHAP per k-mer ──────────────────────────────
    ax_rowbar.barh(np.arange(n_km), row_sums, color="#c0392b", alpha=0.82, height=0.7)
    ax_rowbar.invert_yaxis()
    ax_rowbar.set_ylim(n_km - 0.5, -0.5)
    ax_rowbar.set_yticks([])
    ax_rowbar.set_xlabel("Sum\nSHAP", fontsize=6.5, labelpad=2)
    ax_rowbar.xaxis.set_tick_params(labelsize=6)
    ax_rowbar.spines["top"].set_visible(False)
    ax_rowbar.spines["right"].set_visible(False)
    ax_rowbar.grid(axis="x", linestyle="--", alpha=0.3)
    # Value labels for top 6 highest-sum k-mers
    for idx in np.argsort(row_sums)[-6:]:
        ax_rowbar.text(row_sums[idx] + row_sums.max() * 0.02, idx,
                       f"{row_sums[idx]:.2f}", va="center", fontsize=5, color="#333")

    # ── Colorbar ──────────────────────────────────────────────────────────────
    cbar = fig.colorbar(im, cax=ax_cbar)
    cbar.set_label("Mean Absolute\nSHAP Value", fontsize=7.5, labelpad=6)
    cbar.ax.tick_params(labelsize=6.5)

    # ── Drug class legend ─────────────────────────────────────────────────────
    present = sorted({classify(a) for a in ab_list})
    patches = [mpatches.Patch(color=CLASS_COLORS.get(c, "#9E9E9E"), alpha=0.85, label=c)
               for c in present]
    ax_main.legend(handles=patches, loc="lower right", fontsize=6.5,
                   title="Drug Class", title_fontsize=7,
                   ncol=2, framealpha=0.93, borderpad=0.8)

    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved detailed XGBoost heatmap: %s", out_path)


# ═══════════════════════════════════════════════════════════════════════════════
# Chart 2 — DNABERT: aggregated per-token attention (mean over genes + models)
# ═══════════════════════════════════════════════════════════════════════════════

def tokenize_sequence(sequence: str, tokenizer):
    clean = re.sub(r"[^ATCG]", "", sequence.upper())
    vocab  = tokenizer.get_vocab()
    if "ATCGAT" in vocab:                    # 6-mer tokenizer
        kmers = [clean[i: i+6] for i in range(len(clean) - 5)]
        sentence = " ".join(kmers) if kmers else clean
    else:
        sentence = clean
    return tokenizer(sentence, return_tensors="pt",
                     padding=True, truncation=True, max_length=512)


def attention_rollup(attentions) -> np.ndarray:
    avg = torch.stack([a.squeeze(0).mean(dim=0) for a in attentions], dim=0)
    importance = avg.sum(dim=0).sum(dim=0).cpu().numpy().astype(float)
    s = importance.sum()
    return importance / s if s > 0 else importance


def make_dnabert_chart(out_path: Path, n_genes: int = 50):
    if not HAS_TORCH:
        logger.error("PyTorch required for DNABERT chart.")
        return

    logger.info("Building DNABERT attention chart (n_genes=%d)...", n_genes)

    job_dir = next(iter(sorted(MODEL_DIR.glob("transformer_*"))), None)
    if job_dir is None:
        logger.error("No transformer_* dir found in %s", MODEL_DIR)
        return

    tokenizer = AutoTokenizer.from_pretrained(str(job_dir / "tokenizer"))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Device: %s", device)

    # Load gene sequences
    fasta_path = _PROJECT_DIR / "DATA" / "AP011121.fasta"
    try:
        from preprocessing.dnabert_processor import DNABERTProcessor  # type: ignore
        genes = DNABERTProcessor(k=6, max_length=512).extract_genes_from_fasta(
            fasta_path.read_text(encoding="utf-8", errors="replace")
        )[:n_genes]
    except Exception:
        raw = re.sub(r"[^ATCG]", "", fasta_path.read_text(errors="replace").upper())
        genes = [raw[i:i+500] for i in range(0, min(len(raw), n_genes*500), 500)][:n_genes]
    logger.info("Using %d genes", len(genes))

    ab_dirs = sorted((job_dir / "antibiotics").iterdir())

    # token_acc[token] → list of attention weights across models+genes
    token_acc: dict = defaultdict(list)
    # Also track per-drug-class
    class_token_acc: dict = defaultdict(lambda: defaultdict(list))

    for ab_dir in ab_dirs:
        if not list(ab_dir.glob("model.safetensors")) and not list(ab_dir.glob("pytorch_model.bin")):
            continue
        ab_name = re.sub(r"^\d+_", "", ab_dir.name).replace("_", " ")
        cls = classify(ab_name)
        try:
            model = AutoModelForSequenceClassification.from_pretrained(
                str(ab_dir), output_attentions=True,
                ignore_mismatched_sizes=True
            ).to(device).eval()
        except Exception as exc:
            logger.warning("Skip %s: %s", ab_name, exc)
            continue

        for seq in genes:
            try:
                inputs = tokenize_sequence(seq, tokenizer)
                inputs = {k: v.to(device) for k, v in inputs.items()}
                tokens_ids = inputs["input_ids"][0]
                tokens = tokenizer.convert_ids_to_tokens(tokens_ids)
                with torch.no_grad():
                    out = model(**inputs)
                if hasattr(out, "attentions") and out.attentions:
                    imp = attention_rollup(out.attentions)
                    n   = min(len(imp), len(tokens))
                    for t, v in zip(tokens[:n], imp[:n]):
                        if t not in ("[CLS]", "[SEP]", "[PAD]", "<cls>", "<sep>", "<pad>"):
                            token_acc[t].append(float(v))
                            class_token_acc[cls][t].append(float(v))
            except Exception:
                continue

        del model
        if device == "cuda":
            torch.cuda.empty_cache()

    if not token_acc:
        logger.error("No attention data collected.")
        return

    # Aggregate: mean per token
    token_mean = {t: np.mean(vs) for t, vs in token_acc.items()}
    top50 = sorted(token_mean.keys(), key=lambda t: token_mean[t], reverse=True)[:50]

    # Per-class breakdown for the top tokens
    classes = [c for c in CLASS_COLORS if any(class_token_acc[c])]

    # ── Figure ──────────────────────────────────────────────────────────────
    fig, (ax_main, ax_heat) = plt.subplots(
        2, 1, figsize=(18, 13),
        gridspec_kw={"height_ratios": [2.5, 1]},
    )

    # ── Top panel: stacked-class bar chart ───────────────────────────────────
    x     = np.arange(len(top50))
    bottoms = np.zeros(len(top50))
    for cls in classes:
        class_means = np.array([
            np.mean(class_token_acc[cls][t]) if class_token_acc[cls][t] else 0.0
            for t in top50
        ])
        ax_main.bar(x, class_means, bottom=bottoms,
                    color=CLASS_COLORS[cls], label=cls, alpha=0.88, width=0.78)
        bottoms += class_means

    # Overlay the global mean as a line
    global_vals = np.array([token_mean[t] for t in top50])
    ax_main.plot(x, global_vals, color="#222", linewidth=1.1,
                 marker="o", markersize=2.5, zorder=5, label="Global mean")

    ax_main.set_xticks(x)
    ax_main.set_xticklabels(top50, rotation=55, ha="right",
                             fontsize=7, family="monospace")
    ax_main.set_ylabel("Mean Attention Weight (normalized)", fontsize=9)
    ax_main.set_xlim(-0.5, len(top50) - 0.5)
    ax_main.set_title(
        "DNABERT Attention Rollup — Top 50 Attended 6-mer Tokens\n"
        "Stacked by drug class contribution  |  Model: transformer_ce13dcc6  |  "
        f"110 antibiotic checkpoints  ·  {len(genes)} genes from AP011121",
        fontsize=10, fontweight="bold", pad=12,
    )
    ax_main.legend(loc="upper right", fontsize=7, ncol=2,
                   title="Drug Class", title_fontsize=7, framealpha=0.9)
    ax_main.grid(axis="y", linestyle="--", alpha=0.25)
    ax_main.set_axisbelow(True)

    # ── Bottom panel: mini-heatmap (class × top-50 tokens) ───────────────────
    heat_matrix = np.array([
        [np.mean(class_token_acc[cls][t]) if class_token_acc[cls][t] else 0.0
         for t in top50]
        for cls in classes
    ])
    # Row-normalize so each class's pattern is visible
    row_max = heat_matrix.max(axis=1, keepdims=True)
    row_max[row_max == 0] = 1.0
    heat_norm = heat_matrix / row_max

    im = ax_heat.imshow(heat_norm, cmap="YlOrRd", aspect="auto",
                        vmin=0, vmax=1, interpolation="nearest")
    ax_heat.set_yticks(range(len(classes)))
    ax_heat.set_yticklabels(classes, fontsize=8)
    ax_heat.set_xticks(range(len(top50)))
    ax_heat.set_xticklabels(top50, rotation=55, ha="right",
                             fontsize=7, family="monospace")
    ax_heat.set_xlabel("6-mer Token", fontsize=9)
    ax_heat.set_ylabel("Drug Class", fontsize=9)
    ax_heat.set_title("Relative Attention Strength per Drug Class (row-normalised)",
                      fontsize=9, pad=6)

    cbar = fig.colorbar(im, ax=ax_heat, fraction=0.015, pad=0.01,
                        label="Relative attention (within class)")

    plt.tight_layout(h_pad=3)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved DNABERT chart: %s", out_path)


# ═══════════════════════════════════════════════════════════════════════════════
# Chart 3 — XGBoost SHAP: DNABERT-style stacked bar + class heatmap
# ═══════════════════════════════════════════════════════════════════════════════

def make_xgboost_stacked_chart(out_path: Path, top_n: int = 50):
    """
    Mirror of make_dnabert_chart layout, but for XGBoost SHAP data:
      Top panel  : stacked bar — top_n k-mers × drug-class SHAP contribution
                   + global mean overlay line
      Bottom panel: row-normalised heatmap (drug class × top_n k-mers)
    """
    logger.info("Building XGBoost SHAP stacked chart (top %d k-mers)...", top_n)

    ej = MODEL_DIR / "xgboost_f0849bdd_explainability.json"
    with open(ej) as f:
        data = json.load(f)
    antibiotics_raw = data["antibiotics"]

    ab_list = sorted(antibiotics_raw.keys(), key=lambda a: (classify(a), a))

    # Build per-class, per-kmer SHAP accumulation
    # class_kmer[class][kmer] = list of importance values (one per antibiotic in that class)
    class_kmer: dict = defaultdict(lambda: defaultdict(list))
    global_kmer: dict = defaultdict(float)

    for ab in ab_list:
        cls = classify(ab)
        feats = antibiotics_raw[ab].get("top_features", [])
        for f in feats:
            v = float(f["importance"])
            class_kmer[cls][f["feature"]].append(v)
            global_kmer[f["feature"]] += v

    # Top N k-mers by global SHAP sum
    top_kmers = [k for k, _ in sorted(global_kmer.items(),
                                       key=lambda x: x[1], reverse=True)[:top_n]]

    # Present classes (those with at least one antibiotic that has SHAP data)
    classes = [c for c in CLASS_COLORS if any(class_kmer[c])]

    # Global mean SHAP per top k-mer (across all antibiotics)
    n_ab_total = len(ab_list)
    global_mean = np.array([global_kmer[km] / max(n_ab_total, 1) for km in top_kmers])

    # Per-class mean SHAP per top k-mer
    def cls_mean(cls: str, km: str) -> float:
        vals = class_kmer[cls][km]
        return float(np.mean(vals)) if vals else 0.0

    # ── Figure ───────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(24, 17))
    gs = fig.add_gridspec(
        2, 2,
        height_ratios=[2.2, 1.6],
        width_ratios=[1, 0.018],
        hspace=0.38, wspace=0.03,
    )
    ax_main  = fig.add_subplot(gs[0, 0])
    ax_heat  = fig.add_subplot(gs[1, 0])
    ax_cbar  = fig.add_subplot(gs[1, 1])
    fig.patch.set_facecolor("#f8f8f8")

    # ── Top panel: stacked-class bar chart ───────────────────────────────────
    x = np.arange(len(top_kmers))
    bottoms = np.zeros(len(top_kmers))
    bar_tops = np.zeros(len(top_kmers))     # track total height per bar
    for cls in classes:
        vals = np.array([cls_mean(cls, km) for km in top_kmers])
        ax_main.bar(x, vals, bottom=bottoms,
                    color=CLASS_COLORS[cls], label=cls, alpha=0.90, width=0.78,
                    edgecolor="white", linewidth=0.3)
        bottoms += vals
        bar_tops += vals

    # Global mean overlay line
    ax_main.plot(x, global_mean, color="#111", linewidth=1.3,
                 marker="o", markersize=3, zorder=5, label="Global mean")

    # Value labels on top-10 tallest bars
    top10_idx = np.argsort(bar_tops)[-10:]
    for i in top10_idx:
        ax_main.text(i, bar_tops[i] + bar_tops.max() * 0.01, f"{bar_tops[i]:.2f}",
                     ha="center", va="bottom", fontsize=5.5, color="#222",
                     fontweight="bold")

    # Symlog scale so the tall top bars don't crush the tail
    ax_main.set_yscale("symlog", linthresh=0.1)
    ax_main.set_xticks(x)
    ax_main.set_xticklabels(top_kmers, rotation=55, ha="right",
                             fontsize=6.5, family="monospace")
    ax_main.set_ylabel("Mean Absolute SHAP Value (symlog)", fontsize=9)
    ax_main.set_xlim(-0.5, len(top_kmers) - 0.5)
    ax_main.set_title(
        f"XGBoost SHAP — Top {top_n} Predictive 10-mer Features\n"
        "Stacked by drug-class SHAP contribution  |  "
        f"Model: xgboost_f0849bdd  |  {len(ab_list)} antibiotics  ·  3,204 genomes  ·  155,211 features",
        fontsize=10, fontweight="bold", pad=12,
    )
    ax_main.legend(loc="upper right", fontsize=7, ncol=3,
                   title="Drug Class", title_fontsize=7, framealpha=0.92)
    ax_main.grid(axis="y", linestyle="--", alpha=0.3, which="both")
    ax_main.set_axisbelow(True)

    # ── Bottom panel: heatmap (drug class × top-N k-mers) ────────────────────
    heat_matrix = np.array([
        [cls_mean(cls, km) for km in top_kmers]
        for cls in classes
    ])
    # Row-normalise so every drug class fills the 0-1 range independently
    row_max = heat_matrix.max(axis=1, keepdims=True)
    row_max[row_max == 0] = 1.0
    heat_norm = heat_matrix / row_max

    # --- Alternating column bands every 5 k-mers for readability ---------------
    for band in range(0, len(top_kmers), 10):
        ax_heat.axvspan(band - 0.5, min(band + 4.5, len(top_kmers) - 0.5),
                        facecolor="#e0e0e0", alpha=0.18, zorder=0)

    # Truncated colormap: 0 -> white/cream, 1 -> deep red
    # By slicing RdYlBu_r from 0.5 (yellow-white) to 1.0 (deep red) we get
    # a diverging effect without the harsh blue at zero.
    import matplotlib.colors as mcolors
    _base_cmap = plt.cm.get_cmap("YlOrRd", 512)
    _cmap_trunc = mcolors.LinearSegmentedColormap.from_list(
        "YlOrRd_trunc", _base_cmap(np.linspace(0.0, 1.0, 512)), N=512)
    im = ax_heat.imshow(heat_norm, cmap=_cmap_trunc, aspect="auto",
                        vmin=0, vmax=1, interpolation="nearest", zorder=1)

    # --- Annotate every cell with a relative value >= 5% of row max -------------
    for i in range(len(classes)):
        for j in range(len(top_kmers)):
            v = heat_norm[i, j]
            if v >= 0.05:
                # Pick text color so it contrasts with background
                txt_col = "white" if v > 0.72 else ("#111" if v < 0.42 else "#333")
                ax_heat.text(j, i, f"{v:.2f}", ha="center", va="center",
                             fontsize=4.2, color=txt_col, fontweight="bold",
                             family="monospace", zorder=2)

    # --- Row separator lines (thicker, dark grey) ------------------------------
    for i in range(1, len(classes)):
        ax_heat.axhline(i - 0.5, color="#555", linewidth=0.8, zorder=3)

    # --- Axes labels & title ---------------------------------------------------
    ax_heat.set_yticks(range(len(classes)))
    ax_heat.set_yticklabels(classes, fontsize=8.5, fontweight="semibold")
    ax_heat.set_xticks(range(len(top_kmers)))
    ax_heat.set_xticklabels(top_kmers, rotation=55, ha="right",
                             fontsize=6.5, family="monospace")
    ax_heat.set_xlabel("k-mer Feature (10-mer)  ·  shaded bands = groups of 5", fontsize=9)
    ax_heat.set_ylabel("Drug Class", fontsize=9)
    ax_heat.set_title(
        "Relative SHAP Importance per Drug Class\n"
        "Row-normalised (each row peaks at 1.0)  ·  annotated where ≥ 5 % of row maximum  ·  "
        "Red = high, Blue = low",
        fontsize=8.5, pad=8,
    )
    ax_heat.set_xlim(-0.5, len(top_kmers) - 0.5)
    ax_heat.set_ylim(len(classes) - 0.5, -0.5)

    # --- Colourbar on dedicated narrow axis ------------------------------------
    cbar = fig.colorbar(im, cax=ax_cbar)
    cbar.set_label("Relative SHAP\n(within class)", fontsize=7.5)
    cbar.ax.tick_params(labelsize=7)
    cbar.set_ticks([0, 0.25, 0.5, 0.75, 1.0])
    cbar.set_ticklabels(["0 %", "25 %", "50 %", "75 %", "100 %"])

    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved XGBoost stacked chart: %s", out_path)



# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="shap_output")
    parser.add_argument("--n-genes",    type=int, default=50)
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    make_xgboost_chart(out_dir / "xgboost_shap_best.png", top_n_kmers=30)
    make_xgboost_stacked_chart(out_dir / "xgboost_shap_stacked.png", top_n=50)
    make_dnabert_chart(out_dir / "dnabert_attention_best.png", n_genes=args.n_genes)

    print(f"\nDone.")
    print(f"  XGBoost heatmap : {out_dir / 'xgboost_shap_best.png'}")
    print(f"  XGBoost stacked : {out_dir / 'xgboost_shap_stacked.png'}")
    print(f"  DNABERT         : {out_dir / 'dnabert_attention_best.png'}")


if __name__ == "__main__":
    main()
