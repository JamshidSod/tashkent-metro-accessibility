"""
Sensitivity analysis: how does PRD vary with buffer radius?

Tests PRD_BUFFER_M in [400, 600, 800, 1000, 1200] metres for all stations
on the walk network (20 OD samples per station for speed).

Outputs:
  - Console: Pearson correlations between buffer settings, mean PRD per buffer
  - data/sensitivity.csv: station × buffer PRD matrix

Usage:
    python analysis/sensitivity.py
    (Requires cached walk network in .cache/walk_network.graphml)
"""

import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from config import DATA_DIR, WALK_GRAPHML

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BUFFERS   = [400, 600, 800, 1000, 1200]
N_SAMPLES = 20   # fewer samples for speed (vs 50 in full pipeline)


def run_sensitivity() -> pd.DataFrame:
    from metrics  import compute_prd
    from stations import get_stations
    from network  import get_walk_network

    stations = get_stations("Tashkent, Uzbekistan")
    logger.info("Loaded %d stations", len(stations))

    logger.info("Loading walk network from cache …")
    G_walk = get_walk_network()
    logger.info("Walk network ready: %d nodes", G_walk.number_of_nodes())

    records = []
    n = len(stations)
    for i, (_, st) in enumerate(stations.iterrows()):
        row = {"station_id": st["station_id"], "name_uz": st["name_uz"]}
        for buf in BUFFERS:
            val = compute_prd(G_walk, st.geometry, buffer_m=buf, n_samples=N_SAMPLES, seed=42)
            row[f"prd_{buf}m"] = val
            logger.info("[%d/%d] %s  buffer=%dm  prd=%.4f",
                        i + 1, n, st["station_id"], buf, val if val else float("nan"))
        records.append(row)

    return pd.DataFrame(records)


def print_report(df: pd.DataFrame) -> None:
    print("=" * 65)
    print("PRD SENSITIVITY TO BUFFER RADIUS (walk network, n_samples=20)")
    print("=" * 65)

    cols = [f"prd_{b}m" for b in BUFFERS]

    print("\nMean PRD by buffer radius:")
    for col, buf in zip(cols, BUFFERS):
        vals = df[col].dropna()
        print(f"  {buf:>5} m : mean={vals.mean():.4f}  sd={vals.std():.4f}  "
              f"min={vals.min():.4f}  max={vals.max():.4f}")

    print("\nPearson correlation with reference (800 m):")
    for col, buf in zip(cols, BUFFERS):
        if buf == 800:
            continue
        common = df[["prd_800m", col]].dropna()
        r = np.corrcoef(common["prd_800m"], common[col])[0, 1]
        print(f"  {buf:>5} m vs 800 m : r = {r:.4f}")

    print("\nPearson correlation matrix:")
    corr = df[cols].corr()
    header = "        " + "".join(f"{b:>8}m" for b in BUFFERS)
    print(header)
    for col, buf in zip(cols, BUFFERS):
        row_str = f"  {buf:>5}m  " + "".join(f"  {corr.loc[col, c]:>6.4f}" for c in cols)
        print(row_str)

    print("\n" + "=" * 65)


if __name__ == "__main__":
    if not os.path.exists(os.path.join(DATA_DIR, "metrics.csv")):
        print("ERROR: data/metrics.csv not found. Run the pipeline first.")
        sys.exit(1)

    if not os.path.exists(WALK_GRAPHML):
        print(f"ERROR: Walk network cache not found at {WALK_GRAPHML}.")
        sys.exit(1)

    df = run_sensitivity()
    print_report(df)

    out_path = os.path.join(DATA_DIR, "sensitivity.csv")
    df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")
