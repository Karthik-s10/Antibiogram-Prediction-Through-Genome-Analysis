"""
visualize_qdrant.py
-------------------
Pull genome embeddings + resistance profiles from Qdrant
and produce detailed, interactive HTML plots using Plotly.

Generates:
  1. 2-D UMAP projection coloured by most-resistant antibiotic
  2. 2-D UMAP coloured by number of Resistant labels
  3. Per-antibiotic resistance rate bar chart (top 30)
  4. Resistance label distribution pie chart
  5. n_genes distribution histogram

Usage:
    python visualize_qdrant.py [--max-points 3204] [--output-dir viz_output]
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from collections import defaultdict, Counter

import numpy as np  # type: ignore
import pandas as pd  # type: ignore

# ---------------------------------------------------------------------------
# Optional heavy imports — warn nicely if missing
# ---------------------------------------------------------------------------
try:
    from umap import UMAP  # type: ignore
    HAS_UMAP = True
except ImportError:
    HAS_UMAP = False

try:
    import plotly.graph_objects as go  # type: ignore
    import plotly.express as px  # type: ignore
    from plotly.subplots import make_subplots  # type: ignore
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# Set up path so we can import backend modules regardless of cwd
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))
# Also support running from inside the backend dir
sys.path.insert(0, str(_BACKEND_DIR / "backend"))

from services.qdrant_service import QdrantService  # type: ignore
from config import settings  # type: ignore

try:
    import kaleido  # type: ignore
    HAS_KALEIDO = True
except ImportError:
    HAS_KALEIDO = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LABEL_ORDER = {"Resistant": 2, "Intermediate": 1, "Susceptible": 0}
LABEL_COLORS = {
    "Resistant": "#e74c3c",
    "Intermediate": "#f39c12",
    "Susceptible": "#27ae60",
    "Unknown": "#95a5a6",
}


def _dominant_label(resistance_profile: dict) -> str:
    """Return the 'worst' resistance label across all antibiotics."""
    if not resistance_profile:
        return "Unknown"
    labels = list(resistance_profile.values())
    for lbl in ("Resistant", "Intermediate", "Susceptible"):
        if lbl in labels:
            return lbl
    return "Unknown"


def _resistant_count(resistance_profile: dict) -> int:
    return sum(1 for v in resistance_profile.values() if v == "Resistant")


def save_plot(fig: go.Figure, base_path: str, title: str):
    """Save both HTML and PNG versions of a figure."""
    html_path = base_path + ".html"
    png_path = base_path + ".png"
    
    # Save HTML
    fig.write_html(html_path)
    logger.info(f"Saved HTML: {html_path}")
    
    # Save PNG
    if HAS_KALEIDO:
        try:
            fig.write_image(png_path, width=1200, height=800, scale=2)
            logger.info(f"Saved PNG: {png_path}")
        except Exception as e:
            logger.warning(f"Failed to save PNG for {title}: {e}")
    else:
        logger.warning(f"Skipping PNG save for {title} (kaleido not installed)")


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_data(max_points: int = 3204) -> pd.DataFrame:
    """
    Scroll through Qdrant and build a DataFrame with:
        genome_id, vector (768-d), resistance_profile, n_genes, dominant_label, n_resistant
    """
    qs = QdrantService()
    records = []
    offset = None
    fetched = 0
    batch_size = 100

    logger.info(f"Fetching up to {max_points} genomes from Qdrant...")

    while fetched < max_points:
        limit = min(batch_size, max_points - fetched)
        results, next_offset = qs.client.scroll(
            collection_name="bacterial_genomes",
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        if not results:
            break

        for hit in results:
            payload = hit.payload or {}
            rp = payload.get("resistance_profile", {}) or {}
            if isinstance(rp, str):
                try:
                    rp = json.loads(rp.replace("'", '"'))
                except Exception:
                    rp = {}
            records.append({
                "genome_id": payload.get("genome_id", str(hit.id)),
                "n_genes": int(payload.get("n_genes", 0) or 0),
                "resistance_profile": rp,
                "dominant_label": _dominant_label(rp),
                "n_resistant": _resistant_count(rp),
                "vector": np.array(hit.vector, dtype=np.float32),
            })

        fetched += len(results)
        logger.info(f"  Fetched {fetched} genomes...")

        if next_offset is None:
            break
        offset = next_offset

    logger.info(f"Done. Total records: {len(records)}")
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# UMAP projection
# ---------------------------------------------------------------------------

def compute_umap(vectors: np.ndarray, n_neighbors: int = 15, min_dist: float = 0.1) -> np.ndarray:
    if not HAS_UMAP:
        logger.warning("UMAP not installed; using random 2-D projection. Install via: pip install umap-learn")
        rng = np.random.default_rng(42)
        return rng.normal(size=(len(vectors), 2))

    logger.info("Running UMAP (this may take a few minutes for large datasets)...")
    reducer = UMAP(n_neighbors=n_neighbors, min_dist=min_dist, n_components=2, random_state=42, verbose=True)
    return reducer.fit_transform(vectors)


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_umap_by_label(df: pd.DataFrame, umap_xy: np.ndarray, output_path: str) -> None:
    """Scatter plot coloured by dominant resistance label."""
    fig = go.Figure()

    for label, color in LABEL_COLORS.items():
        mask = df["dominant_label"] == label
        if not mask.any():
            continue
        sub = df[mask]
        xy = umap_xy[mask.to_numpy()]
        hover = (
            "Genome: " + sub["genome_id"].astype(str) + "<br>" +
            "Label: " + sub["dominant_label"] + "<br>" +
            "n_resistant: " + sub["n_resistant"].astype(str) + "<br>" +
            "n_genes: " + sub["n_genes"].astype(str)
        )
        fig.add_trace(go.Scattergl(
            x=xy[:, 0], y=xy[:, 1],
            mode="markers",
            marker=dict(color=color, size=5, opacity=0.6),
            name=label,
            text=hover,
            hoverinfo="text",
        ))

    fig.update_layout(
        title="UMAP of Bacterial Genomes — Coloured by Dominant Resistance Label",
        xaxis_title="UMAP 1", yaxis_title="UMAP 2",
        template="plotly_dark",
        legend_title="Resistance",
        width=1100, height=750,
    )
    save_plot(fig, output_path.replace(".html", ""), "UMAP by Label")


def plot_umap_by_n_resistant(df: pd.DataFrame, umap_xy: np.ndarray, output_path: str) -> None:
    """Scatter plot coloured by number of Resistant antibiotics."""
    fig = go.Figure()
    fig.add_trace(go.Scattergl(
        x=umap_xy[:, 0], y=umap_xy[:, 1],
        mode="markers",
        marker=dict(
            color=df["n_resistant"],
            colorscale="YlOrRd",
            size=5, opacity=0.8,
            colorbar=dict(title="# Resistant"),
            showscale=True,
        ),
        text=(
            "Genome: " + df["genome_id"].astype(str) + "<br>" +
            "n_resistant: " + df["n_resistant"].astype(str)
        ),
        hoverinfo="text",
    ))
    fig.update_layout(
        title="UMAP of Bacterial Genomes — Coloured by # Resistant Antibiotics",
        xaxis_title="UMAP 1", yaxis_title="UMAP 2",
        template="plotly_dark",
        width=1100, height=750,
    )
    save_plot(fig, output_path.replace(".html", ""), "UMAP by n_resistant")


def plot_resistance_rates(df: pd.DataFrame, output_path: str, top_n: int = 30) -> None:
    """Stacked bar chart: Resistant / Intermediate / Susceptible rate per antibiotic."""
    ab_counts: dict = defaultdict(lambda: Counter())

    for _, row in df.iterrows():
        rp = row["resistance_profile"]
        if isinstance(rp, dict):
            for ab, label in rp.items():
                ab_counts[ab][label] += 1

    rows = []
    for ab, cnts in ab_counts.items():
        total = sum(cnts.values())
        if total == 0:
            continue
        rows.append({
            "antibiotic": ab,
            "total": total,
            "Resistant_pct": cnts.get("Resistant", 0) / total * 100,
            "Intermediate_pct": cnts.get("Intermediate", 0) / total * 100,
            "Susceptible_pct": cnts.get("Susceptible", 0) / total * 100,
        })

    if not rows:
        logger.warning("No resistance rate data to plot.")
        return

    ab_df = pd.DataFrame(rows).sort_values("total", ascending=False).head(top_n)

    fig = go.Figure()
    for label, col in [("Resistant", "Resistant_pct"), ("Intermediate", "Intermediate_pct"), ("Susceptible", "Susceptible_pct")]:
        fig.add_trace(go.Bar(
            x=ab_df["antibiotic"],
            y=ab_df[col],
            name=label,
            marker_color=LABEL_COLORS[label],
        ))

    fig.update_layout(
        barmode="stack",
        title=f"Top {top_n} Antibiotics — Resistance Rate (% of genomes tested)",
        xaxis_title="Antibiotic", yaxis_title="% of Genomes",
        xaxis_tickangle=-45,
        template="plotly_dark",
        legend_title="Label",
        width=1300, height=650,
    )
    save_plot(fig, output_path.replace(".html", ""), "Resistance Rates")


def plot_label_distribution(df: pd.DataFrame, output_path: str) -> None:
    """Pie chart of dominant resistance labels across all genomes."""
    counts = df["dominant_label"].value_counts()
    fig = go.Figure(go.Pie(
        labels=counts.index.tolist(),
        values=counts.values.tolist(),
        marker=dict(colors=[LABEL_COLORS.get(l, "#aaa") for l in counts.index]),
        textinfo="label+percent",
        hole=0.35,
    ))
    fig.update_layout(
        title="Genome-level Dominant Resistance Label Distribution",
        template="plotly_dark",
        width=700, height=600,
    )
    save_plot(fig, output_path.replace(".html", ""), "Label Distribution")


def plot_n_genes_histogram(df: pd.DataFrame, output_path: str) -> None:
    """Histogram of gene counts per genome."""
    fig = go.Figure()
    for label, color in LABEL_COLORS.items():
        subset = df[df["dominant_label"] == label]["n_genes"]
        if subset.empty:
            continue
        fig.add_trace(go.Histogram(
            x=subset,
            name=label,
            marker_color=color,
            opacity=0.8,
            nbinsx=100,
        ))
    fig.update_layout(
        barmode="stack",
        title="Distribution of Gene Count per Genome",
        xaxis_title="# Pseudo-genes per Genome",
        yaxis_title="Count",
        template="plotly_dark",
        legend_title="Label",
        width=1000, height=550,
    )
    save_plot(fig, output_path.replace(".html", ""), "Gene Count Histogram")


def plot_top_resistant_genomes(df: pd.DataFrame, output_path: str, top_n: int = 50) -> None:
    """Horizontal bar chart of the genomes with the most resistant antibiotics."""
    top = df.nlargest(top_n, "n_resistant")[["genome_id", "n_resistant", "dominant_label"]].copy()
    top = top.sort_values("n_resistant")
    fig = go.Figure(go.Bar(
        x=top["n_resistant"],
        y=top["genome_id"].astype(str),
        orientation="h",
        marker=dict(
            color=top["n_resistant"],
            colorscale="YlOrRd",
            showscale=True,
            colorbar=dict(title="# Resistant"),
        ),
        text=top["n_resistant"],
        textposition="outside",
    ))
    fig.update_layout(
        title=f"Top {top_n} Multi-Drug Resistant Genomes",
        xaxis_title="# Resistant Antibiotics",
        yaxis_title="Genome ID",
        template="plotly_dark",
        height=max(500, top_n * 18),
        width=950,
    )
    save_plot(fig, output_path.replace(".html", ""), "Top MDR Genomes")


def generate_summary_dashboard(paths: dict, output_path: str) -> None:
    """Generate a simple HTML index linking to all plots."""
    links = "\n".join(
        f'<li><a href="{Path(p).name}" target="_blank">{name}</a> (<a href="{Path(p).name.replace(".html", ".png")}" download>Download PNG</a>)</li>'
        for name, p in paths.items()
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Bacterial Genome Qdrant Visualizations</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #111; color: #eee; padding: 40px; }}
  h1 {{ color: #27ae60; }}
  ul {{ line-height: 2.5; }}
  a {{ color: #3498db; text-decoration: none; font-size: 1.1em; }}
  a:hover {{ color: #5dade2; }}
</style>
</head>
<body>
<h1>🦠 Bacterial Genome Visualization Dashboard</h1>
<p>Qdrant collection: <code>bacterial_genomes</code></p>
<ul>
{links}
</ul>
</body>
</html>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"Dashboard saved: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Visualize Qdrant bacterial genome embeddings.")
    parser.add_argument("--max-points", type=int, default=3204, help="Max genomes to load (default: all 3204)")
    parser.add_argument("--output-dir", default="viz_output", help="Directory for HTML output files")
    parser.add_argument("--skip-umap", action="store_true", help="Skip UMAP (fast — only bar/pie plots)")
    args = parser.parse_args()

    if not HAS_PLOTLY:
        logger.error("Plotly is required. Install with:  pip install plotly")
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- fetch ---
    df = fetch_data(max_points=args.max_points)

    # --- static plots (no UMAP needed) ---
    paths = {}

    p1 = str(out_dir / "resistance_rates.html")
    plot_resistance_rates(df, p1)
    paths["Per-Antibiotic Resistance Rates (Top 30)"] = p1

    p2 = str(out_dir / "label_distribution.html")
    plot_label_distribution(df, p2)
    paths["Genome Label Distribution (Pie)"] = p2

    # Handle outliers for n_genes histogram
    df_histo = df.copy()
    max_genes_threshold = 5000
    n_outliers = (df_histo["n_genes"] > max_genes_threshold).sum()
    if n_outliers > 0:
        logger.info(f"Clipping {n_outliers} n_genes outliers to {max_genes_threshold} for histogram.")
        df_histo["n_genes"] = df_histo["n_genes"].clip(upper=max_genes_threshold)

    p3 = str(out_dir / "n_genes_histogram.html")
    plot_n_genes_histogram(df_histo, p3)
    paths["Gene Count Histogram"] = p3

    p4 = str(out_dir / "top_resistant_genomes.html")
    plot_top_resistant_genomes(df, p4)
    paths["Top 50 Most Resistant Genomes"] = p4

    # --- UMAP projections ---
    if not args.skip_umap:
        vectors = np.stack(df["vector"].to_numpy())

        # Subsample if very large for speed
        if len(vectors) > 3204:
            idx = np.random.default_rng(42).choice(len(vectors), 3204, replace=False)
            df_sub = df.iloc[idx].reset_index(drop=True)
            vectors = vectors[idx]
        else:
            df_sub = df

        umap_xy = compute_umap(vectors)

        p5 = str(out_dir / "umap_by_label.html")
        plot_umap_by_label(df_sub, umap_xy, p5)
        paths["UMAP — by Resistance Label"] = p5

        p6 = str(out_dir / "umap_by_n_resistant.html")
        plot_umap_by_n_resistant(df_sub, umap_xy, p6)
        paths["UMAP — by # Resistant Antibiotics"] = p6
    else:
        logger.info("Skipping UMAP plots (--skip-umap flag set).")

    # --- dashboard index ---
    dash = str(out_dir / "index.html")
    generate_summary_dashboard(paths, dash)

    print(f"\nAll plots saved to '{out_dir}/'")
    print(f"   Open:  {dash}")


if __name__ == "__main__":
    main()
