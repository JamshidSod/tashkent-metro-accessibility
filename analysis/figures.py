"""
Publication-ready figures for Tashkent Metro accessibility analysis.

Outputs (PNG 300 dpi + SVG) saved to Output/figures/:
  fig1_walk_pop_by_line.png/svg   — mean walk pop 10 min by line (bar + error bars)
  fig2_walk_pop_boxplot.png/svg   — walk pop 10 min distribution by line (box plot)
  fig3_prd_by_line.png/svg        — mean PRD walk by line (bar + error bars)
  fig4_prd_vs_area_scatter.png/svg — PRD walk vs walk area 10 min (scatter by line)
  fig5_overview.png/svg           — 2×2 subplot overview

Usage:
    python analysis/figures.py
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from config import DATA_DIR

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGURES_DIR = os.path.join(BASE_DIR, "Output", "figures")

LINE_ORDER = [
    "Chilonzor Line",
    "O'zbekiston Line",
    "Yunusobod Line",
    "Ring Line (Yellow)",
]
LINE_SHORT = {
    "Chilonzor Line":     "Chilonzor",
    "O'zbekiston Line":   "O'zbekiston",
    "Yunusobod Line":     "Yunusobod",
    "Ring Line (Yellow)": "Ring (Yellow)",
}
LINE_COLORS = {
    "Chilonzor Line":     "#1565C0",
    "O'zbekiston Line":   "#C62828",
    "Yunusobod Line":     "#2E7D32",
    "Ring Line (Yellow)": "#F9A825",
}

FONT = {"family": "sans-serif", "size": 10}
matplotlib.rc("font", **FONT)


def save(fig, name: str) -> None:
    os.makedirs(FIGURES_DIR, exist_ok=True)
    for ext in ("png", "svg"):
        path = os.path.join(FIGURES_DIR, f"{name}.{ext}")
        fig.savefig(path, dpi=300, bbox_inches="tight")
        print(f"  Saved: {path}")
    plt.close(fig)


def fig1_walk_pop_by_line(df: pd.DataFrame) -> None:
    """Horizontal bar chart: mean walk pop 10 min by line, sorted."""
    sub = df[df["line"].isin(LINE_ORDER)]
    stats = sub.groupby("line")["walk_pop_10"].agg(["mean", "std"]).reindex(LINE_ORDER)
    stats["short"] = [LINE_SHORT[l] for l in stats.index]
    stats = stats.sort_values("mean")

    fig, ax = plt.subplots(figsize=(7, 3.5))
    colors = [LINE_COLORS[l] for l in stats.index]
    bars = ax.barh(stats["short"], stats["mean"], xerr=stats["std"],
                   color=colors, edgecolor="white", capsize=4, error_kw={"linewidth": 1.2})
    ax.set_xlabel("Mean population reachable (persons)", labelpad=8)
    ax.set_title("Population reachable within 10 min walk by metro line\n(mean ± SD)", pad=10)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(left=0)
    fig.tight_layout()
    save(fig, "fig1_walk_pop_by_line")


def fig2_walk_pop_boxplot(df: pd.DataFrame) -> None:
    """Box plot: walk pop 10 min distribution by line."""
    sub = df[df["line"].isin(LINE_ORDER)].copy()
    ordered = [l for l in LINE_ORDER if l in sub["line"].values]
    data    = [sub[sub["line"] == l]["walk_pop_10"].dropna().values for l in ordered]
    labels  = [LINE_SHORT[l] for l in ordered]
    colors  = [LINE_COLORS[l] for l in ordered]

    fig, ax = plt.subplots(figsize=(7, 4))
    bp = ax.boxplot(data, patch_artist=True, medianprops={"color": "white", "linewidth": 2},
                    whiskerprops={"linewidth": 1.2}, capprops={"linewidth": 1.2},
                    flierprops={"marker": "o", "markersize": 4, "alpha": 0.6})
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.85)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Population reachable (persons)")
    ax.set_title("Walk population catchment (10 min) distribution by metro line", pad=10)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save(fig, "fig2_walk_pop_boxplot")


def fig3_prd_by_line(df: pd.DataFrame) -> None:
    """Bar chart: mean PRD walk by line with error bars."""
    sub   = df[df["line"].isin(LINE_ORDER)]
    stats = sub.groupby("line")["prd_walk"].agg(["mean", "std"]).reindex(LINE_ORDER)
    stats["short"] = [LINE_SHORT[l] for l in stats.index]
    stats = stats.sort_values("mean", ascending=False)

    fig, ax = plt.subplots(figsize=(7, 3.5))
    colors = [LINE_COLORS[l] for l in stats.index]
    ax.bar(stats["short"], stats["mean"], yerr=stats["std"],
           color=colors, edgecolor="white", capsize=5, error_kw={"linewidth": 1.2})
    ax.set_ylabel("Mean PRD walk (0–1)")
    ax.set_title("Pedestrian Route Directness (PRD) by metro line\n(mean ± SD, higher = more direct)",
                 pad=10)
    ax.set_ylim(0, 1.0)
    ax.axhline(0.80, color="#2E7D32", linewidth=1, linestyle="--", alpha=0.7, label="High threshold (0.80)")
    ax.axhline(0.65, color="#F57F17", linewidth=1, linestyle="--", alpha=0.7, label="Medium threshold (0.65)")
    ax.legend(fontsize=9, framealpha=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save(fig, "fig3_prd_by_line")


def fig4_prd_vs_area_scatter(df: pd.DataFrame) -> None:
    """Scatter: PRD walk vs walk area 10 min, colored by line."""
    sub = df[df["line"].isin(LINE_ORDER)].copy()

    fig, ax = plt.subplots(figsize=(7, 5))
    for line in LINE_ORDER:
        mask = sub["line"] == line
        ax.scatter(sub.loc[mask, "walk_area_10"], sub.loc[mask, "prd_walk"],
                   color=LINE_COLORS[line], label=LINE_SHORT[line],
                   s=55, alpha=0.85, edgecolors="white", linewidths=0.5)

    # Reference lines
    ax.axhline(0.80, color="#2E7D32", linewidth=0.8, linestyle="--", alpha=0.6)
    ax.axhline(0.65, color="#F57F17", linewidth=0.8, linestyle="--", alpha=0.6)

    ax.set_xlabel("Walk catchment area — 10 min (km²)")
    ax.set_ylabel("PRD walk (0–1, higher = more direct)")
    ax.set_title("Catchment area vs. network directness per station", pad=10)
    ax.legend(framealpha=0.85, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save(fig, "fig4_prd_vs_area_scatter")


def fig5_overview(df: pd.DataFrame) -> None:
    """2×2 subplot overview for publication."""
    sub    = df[df["line"].isin(LINE_ORDER)].copy()
    stats  = sub.groupby("line").agg(
        walk_pop_mean=("walk_pop_10", "mean"), walk_pop_std=("walk_pop_10", "std"),
        prd_mean=("prd_walk", "mean"),         prd_std=("prd_walk", "std"),
    ).reindex(LINE_ORDER)
    labels = [LINE_SHORT[l] for l in LINE_ORDER]
    colors = [LINE_COLORS[l] for l in LINE_ORDER]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Tashkent Metro — Accessibility Overview", fontsize=13, fontweight="bold", y=1.01)

    # A: Walk pop by line (bar)
    ax = axes[0, 0]
    ax.bar(labels, stats["walk_pop_mean"], yerr=stats["walk_pop_std"],
           color=colors, edgecolor="white", capsize=4)
    ax.set_title("(A) Walk pop 10 min by line (mean ± SD)")
    ax.set_ylabel("Persons")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", rotation=15)

    # B: Bike pop by line (bar)
    ax = axes[0, 1]
    stats_b = sub.groupby("line").agg(
        bike_pop_mean=("bike_pop_10", "mean"), bike_pop_std=("bike_pop_10", "std"),
    ).reindex(LINE_ORDER)
    ax.bar(labels, stats_b["bike_pop_mean"], yerr=stats_b["bike_pop_std"],
           color=colors, edgecolor="white", capsize=4, alpha=0.85)
    ax.set_title("(B) Bike pop 10 min by line (mean ± SD)")
    ax.set_ylabel("Persons")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", rotation=15)

    # C: PRD walk by line (bar)
    ax = axes[1, 0]
    ax.bar(labels, stats["prd_mean"], yerr=stats["prd_std"],
           color=colors, edgecolor="white", capsize=4)
    ax.set_title("(C) PRD walk by line (mean ± SD)")
    ax.set_ylabel("PRD (0–1)")
    ax.set_ylim(0, 1.0)
    ax.axhline(0.80, color="#2E7D32", linewidth=0.8, linestyle="--", alpha=0.7)
    ax.axhline(0.65, color="#F57F17", linewidth=0.8, linestyle="--", alpha=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", rotation=15)

    # D: scatter PRD vs walk area
    ax = axes[1, 1]
    for line in LINE_ORDER:
        mask = sub["line"] == line
        ax.scatter(sub.loc[mask, "walk_area_10"], sub.loc[mask, "prd_walk"],
                   color=LINE_COLORS[line], label=LINE_SHORT[line],
                   s=40, alpha=0.8, edgecolors="white", linewidths=0.4)
    ax.set_title("(D) Walk area vs PRD walk")
    ax.set_xlabel("Walk area 10 min (km²)")
    ax.set_ylabel("PRD walk (0–1)")
    ax.legend(fontsize=8, framealpha=0.8)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    save(fig, "fig5_overview")


if __name__ == "__main__":
    import matplotlib.ticker

    metrics_path = os.path.join(DATA_DIR, "metrics.csv")
    if not os.path.exists(metrics_path):
        print(f"ERROR: {metrics_path} not found.")
        sys.exit(1)

    df = pd.read_csv(metrics_path)
    print(f"Generating figures → {FIGURES_DIR}")
    fig1_walk_pop_by_line(df)
    fig2_walk_pop_boxplot(df)
    fig3_prd_by_line(df)
    fig4_prd_vs_area_scatter(df)
    fig5_overview(df)
    print("Done.")
