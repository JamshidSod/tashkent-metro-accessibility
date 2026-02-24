"""
Line-level statistical summary of accessibility metrics.

Reads data/metrics.csv and produces:
  - Console report: mean ± SD per line for key metrics, best/worst rankings
  - data/line_summary.csv: wide-format table for publication tables

Usage:
    python analysis/summary.py
"""

import os
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from config import DATA_DIR

# ── Metrics to summarise ───────────────────────────────────────────────────────
# (column, label, unit)
METRICS = [
    ("walk_area_5",   "Walk area 5 min",   "km²"),
    ("walk_area_10",  "Walk area 10 min",  "km²"),
    ("walk_area_15",  "Walk area 15 min",  "km²"),
    ("walk_pop_5",    "Walk pop 5 min",    "persons"),
    ("walk_pop_10",   "Walk pop 10 min",   "persons"),
    ("walk_pop_15",   "Walk pop 15 min",   "persons"),
    ("bike_area_5",   "Bike area 5 min",   "km²"),
    ("bike_area_10",  "Bike area 10 min",  "km²"),
    ("bike_area_15",  "Bike area 15 min",  "km²"),
    ("bike_pop_5",    "Bike pop 5 min",    "persons"),
    ("bike_pop_10",   "Bike pop 10 min",   "persons"),
    ("bike_pop_15",   "Bike pop 15 min",   "persons"),
    ("prd_walk",      "PRD walk",          "0–1"),
    ("prd_bike",      "PRD bike",          "0–1"),
]

LINE_ORDER = [
    "Chilonzor Line",
    "O'zbekiston Line",
    "Yunusobod Line",
    "Ring Line (Yellow)",
    "Other",
]


def build_line_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate per-station metrics to line level.

    Returns a DataFrame with one row per line and columns:
      n_stations, {metric}_mean, {metric}_sd, {metric}_min, {metric}_max
    for each metric in METRICS.
    """
    cols = [m[0] for m in METRICS]
    agg = (
        df.groupby("line")[cols]
        .agg(["mean", "std", "min", "max", "count"])
    )
    # Flatten MultiIndex columns: (metric, stat) → metric_stat
    agg.columns = ["_".join(c) for c in agg.columns]
    agg = agg.rename(columns={f"{cols[0]}_count": "n_stations"})
    # Drop duplicate count columns (keep only first)
    count_cols = [c for c in agg.columns if c.endswith("_count")]
    agg = agg.drop(columns=count_cols)

    # Add n_stations from value_counts
    agg["n_stations"] = df.groupby("line")["station_id"].count()

    # Reorder rows
    present = [l for l in LINE_ORDER if l in agg.index]
    agg = agg.loc[present]

    return agg.reset_index()


def print_report(df: pd.DataFrame, summary: pd.DataFrame) -> None:
    """Print a human-readable summary to stdout."""
    lines = [l for l in LINE_ORDER if l in df["line"].values]

    print("=" * 70)
    print("TASHKENT METRO — ACCESSIBILITY SUMMARY BY LINE")
    print("=" * 70)

    # Station counts
    print("\nStation count per line:")
    for _, row in summary.iterrows():
        print(f"  {row['line']:<22} {int(row['n_stations'])} stations")

    # Per-metric table: mean ± SD
    print("\n── Mean ± SD by line ────────────────────────────────────────────────")
    key_metrics = [
        ("walk_area_10", "Walk area 10 min (km²)"),
        ("walk_pop_10",  "Walk pop 10 min"),
        ("bike_area_10", "Bike area 10 min (km²)"),
        ("bike_pop_10",  "Bike pop 10 min"),
        ("prd_walk",     "PRD walk (0–1)"),
        ("prd_bike",     "PRD bike (0–1)"),
    ]

    for col, label in key_metrics:
        print(f"\n  {label}")
        for _, row in summary.iterrows():
            mean = row[f"{col}_mean"]
            sd   = row.get(f"{col}_std", float("nan"))
            mn   = row[f"{col}_min"]
            mx   = row[f"{col}_max"]
            pop = col.endswith("_pop_10") or col.endswith("_pop_5") or col.endswith("_pop_15")
            if pop:
                sd_str = f"±{sd:,.0f}" if not pd.isna(sd) else ""
                print(f"    {row['line']:<22} {mean:>9,.0f}  {sd_str:<12}  "
                      f"[{mn:,.0f} – {mx:,.0f}]")
            else:
                sd_str = f"±{sd:.3f}" if not pd.isna(sd) else ""
                print(f"    {row['line']:<22} {mean:>8.3f}  {sd_str:<10}  "
                      f"[{mn:.3f} – {mx:.3f}]")

    # Rankings
    print("\n── Rankings (best → worst) ──────────────────────────────────────────")
    ranking_metrics = [
        ("walk_pop_10_mean", "Most population reachable on foot (10 min)", True),
        ("bike_pop_10_mean", "Most population reachable by bike (10 min)", True),
        ("prd_walk_mean",    "Most direct pedestrian network (PRD walk)",  True),
    ]
    for col, label, higher_better in ranking_metrics:
        ranked = summary[summary["line"] != "Other"].sort_values(col, ascending=not higher_better)
        print(f"\n  {label}:")
        for rank, (_, row) in enumerate(ranked.iterrows(), 1):
            print(f"    {rank}. {row['line']:<22} {row[col]:,.3f}")

    print("\n" + "=" * 70)


def export_summary(summary: pd.DataFrame) -> str:
    """Write line_summary.csv to DATA_DIR."""
    path = os.path.join(DATA_DIR, "line_summary.csv")
    # Round floats for cleaner output
    float_cols = [c for c in summary.columns if summary[c].dtype == float]
    out = summary.copy()
    for c in float_cols:
        out[c] = out[c].round(4)
    out.to_csv(path, index=False)
    print(f"\nSaved: {path}")
    return path


if __name__ == "__main__":
    metrics_path = os.path.join(DATA_DIR, "metrics.csv")
    if not os.path.exists(metrics_path):
        print(f"ERROR: {metrics_path} not found. Run the pipeline first.")
        sys.exit(1)

    df = pd.read_csv(metrics_path)
    summary = build_line_summary(df)
    print_report(df, summary)
    export_summary(summary)
