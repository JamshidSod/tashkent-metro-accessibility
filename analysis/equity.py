"""
Accessibility equity analysis across Tashkent Metro stations.

Computes:
  - Per-station ranking by population reachable within 10 min walk/bike
  - Gini coefficient for population distribution across stations
  - Equity tier labels (High / Medium / Low access)
  - Export: data/equity.csv

Usage:
    python analysis/equity.py
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from config import DATA_DIR

LINE_ORDER = [
    "Chilonzor Line",
    "O'zbekiston Line",
    "Yunusobod Line",
    "Ring Line (Yellow)",
    "Other",
]


def gini(values: np.ndarray) -> float:
    """
    Compute Gini coefficient for an array of non-negative values.
    0 = perfect equality, 1 = maximum inequality.
    """
    v = np.sort(values[~np.isnan(values)])
    n = len(v)
    if n == 0 or v.sum() == 0:
        return float("nan")
    idx = np.arange(1, n + 1)
    return float((2 * (idx * v).sum() / (n * v.sum())) - (n + 1) / n)


def equity_tier(pctile: float) -> str:
    """Classify a station by its percentile into High / Medium / Low access."""
    if pctile >= 80:
        return "High"
    if pctile >= 20:
        return "Medium"
    return "Low"


def build_equity_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add rank, percentile, and equity tier columns for walk and bike pop at 10 min.
    Returns a copy sorted by walk_pop_10 descending.
    """
    out = df[["station_id", "name_uz", "name_ru", "line",
              "walk_pop_10", "bike_pop_10",
              "walk_pop_5", "walk_pop_15"]].copy()

    for col in ("walk_pop_10", "bike_pop_10"):
        short = col.replace("_pop_10", "")
        out[f"{short}_rank"]  = out[col].rank(method="min", ascending=False).astype(int)
        out[f"{short}_pctile"] = out[col].rank(method="average", pct=True).mul(100).round(1)
        out[f"{short}_tier"]   = out[f"{short}_pctile"].apply(equity_tier)

    return out.sort_values("walk_rank").reset_index(drop=True)


def print_report(df: pd.DataFrame, equity: pd.DataFrame) -> None:
    print("=" * 70)
    print("TASHKENT METRO — ACCESSIBILITY EQUITY ANALYSIS")
    print("=" * 70)

    # Gini coefficients
    for col, label in [("walk_pop_10", "Walk pop 10 min"),
                        ("bike_pop_10", "Bike pop 10 min")]:
        g = gini(df[col].dropna().values)
        print(f"\nGini coefficient — {label}: {g:.3f}  "
              f"({'high' if g > 0.4 else 'moderate' if g > 0.25 else 'low'} inequality)")

    # Top / bottom 10
    print("\n── Top 10 stations by walk population (10 min) ─────────────────────")
    top = equity.head(10)
    for _, r in top.iterrows():
        print(f"  {int(r['walk_rank']):>2}. {r['name_uz']:<28} {r['line']:<22} "
              f"{int(r['walk_pop_10']):>7,}  [{r['walk_tier']}]")

    print("\n── Bottom 10 stations by walk population (10 min) ──────────────────")
    bot = equity.tail(10).iloc[::-1]
    for _, r in bot.iterrows():
        print(f"  {int(r['walk_rank']):>2}. {r['name_uz']:<28} {r['line']:<22} "
              f"{int(r['walk_pop_10']):>7,}  [{r['walk_tier']}]")

    # Tier counts by line
    print("\n── Access tier distribution by line (walk 10 min) ──────────────────")
    pivot = (
        equity.groupby(["line", "walk_tier"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=["High", "Medium", "Low"], fill_value=0)
    )
    for line in LINE_ORDER:
        if line in pivot.index:
            r = pivot.loc[line]
            print(f"  {line:<22}  High:{r.get('High',0):>2}  Medium:{r.get('Medium',0):>2}  Low:{r.get('Low',0):>2}")

    print("\n" + "=" * 70)


def export_equity(equity: pd.DataFrame) -> str:
    path = os.path.join(DATA_DIR, "equity.csv")
    equity.to_csv(path, index=False)
    print(f"\nSaved: {path}")
    return path


if __name__ == "__main__":
    metrics_path = os.path.join(DATA_DIR, "metrics.csv")
    if not os.path.exists(metrics_path):
        print(f"ERROR: {metrics_path} not found. Run the pipeline first.")
        sys.exit(1)

    df     = pd.read_csv(metrics_path)
    equity = build_equity_table(df)
    print_report(df, equity)
    export_equity(equity)
