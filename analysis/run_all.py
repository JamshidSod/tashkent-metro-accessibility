"""
Tashkent Metro Accessibility — Full Analysis Pipeline

Single entry point. Runs all steps in order, logs timestamps, and
prints a summary table upon completion.

Usage:
    python analysis/run_all.py [--force-download]

Arguments:
    --force-download   Re-download OSM networks even if cached.
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timezone

# Ensure the analysis/ directory is on PYTHONPATH when running from project root
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATA_DIR, OSM_PLACE, TIME_THRESHOLDS_MIN
from stations   import get_stations
from network    import get_walk_network, get_bike_network, get_osm_timestamp
from isochrones import compute_all_isochrones
from population import download_worldpop, add_population_to_isochrones
from metrics    import build_metrics_table
from export     import export_all

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── CLI ────────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Tashkent Metro Accessibility Pipeline")
parser.add_argument(
    "--force-download",
    action="store_true",
    help="Re-download OSM networks from the internet (ignores cache).",
)


def step(label: str):
    """Context manager that logs step start/end times."""
    class _Step:
        def __enter__(self):
            logger.info("━━━ %s ━━━", label)
            self.t0 = time.time()
        def __exit__(self, *_):
            logger.info("    done in %.1f s", time.time() - self.t0)
    return _Step()


def main():
    args = parser.parse_args()
    run_start = time.time()
    run_ts    = datetime.now(timezone.utc).isoformat()

    logger.info("=" * 60)
    logger.info("  Tashkent Metro Accessibility — Analysis Pipeline")
    logger.info("  Run timestamp (UTC): %s", run_ts)
    logger.info("=" * 60)

    # ── Step 1: Stations ───────────────────────────────────────────────────────
    with step("1/6 — Load station data"):
        stations = get_stations(OSM_PLACE)
        logger.info("    Stations: %d", len(stations))

    # ── Step 2: Networks ───────────────────────────────────────────────────────
    with step("2/6 — Download / load street networks"):
        G_walk = get_walk_network(force=args.force_download)
        G_bike = get_bike_network(force=args.force_download)
        walk_ts = get_osm_timestamp("walk")
        bike_ts = get_osm_timestamp("bike")
        logger.info("    Walk network OSM timestamp: %s", walk_ts)
        logger.info("    Bike network OSM timestamp: %s", bike_ts)

    # ── Step 3: Isochrones ─────────────────────────────────────────────────────
    with step("3/6 — Compute isochrones"):
        isochrones = compute_all_isochrones(
            stations, G_walk, G_bike, thresholds=TIME_THRESHOLDS_MIN
        )
        logger.info("    Isochrone polygons: %d", len(isochrones))

    # ── Step 4: Population ─────────────────────────────────────────────────────
    with step("4/6 — Download WorldPop raster + zonal statistics"):
        raster_path = download_worldpop()
        isochrones  = add_population_to_isochrones(isochrones, raster_path)

    # ── Step 5: Metrics ────────────────────────────────────────────────────────
    with step("5/6 — Build metrics table"):
        metrics_df = build_metrics_table(stations, isochrones, G_walk, G_bike)

    # ── Step 6: Export ─────────────────────────────────────────────────────────
    with step("6/6 — Export outputs"):
        paths = export_all(stations, isochrones, metrics_df)
        for key, path in paths.items():
            logger.info("    %-24s → %s", key, path)

    # ── Summary ────────────────────────────────────────────────────────────────
    elapsed = time.time() - run_start
    logger.info("=" * 60)
    logger.info("  Pipeline complete in %.1f s", elapsed)
    logger.info("  Output directory: %s", DATA_DIR)
    logger.info("=" * 60)

    # Print metrics summary table
    try:
        import pandas as pd
        print("\n── Metrics Summary ──")
        cols = (
            ["station_id", "name_uz", "line"] +
            [f"walk_area_{t}" for t in TIME_THRESHOLDS_MIN] +
            ["prd_walk"]
        )
        available = [c for c in cols if c in metrics_df.columns]
        print(metrics_df[available].to_string(index=False))

        # Write run metadata as a comment in data/run_info.txt
        meta_path = os.path.join(DATA_DIR, "run_info.txt")
        with open(meta_path, "w") as f:
            f.write(f"run_timestamp_utc: {run_ts}\n")
            f.write(f"osm_walk_timestamp: {walk_ts}\n")
            f.write(f"osm_bike_timestamp: {bike_ts}\n")
            f.write(f"osm_place: {OSM_PLACE}\n")
            f.write(f"stations_count: {len(stations)}\n")
            f.write(f"time_thresholds_min: {TIME_THRESHOLDS_MIN}\n")
        logger.info("Run metadata written to %s", meta_path)
    except Exception as exc:
        logger.warning("Summary print failed: %s", exc)


if __name__ == "__main__":
    main()
