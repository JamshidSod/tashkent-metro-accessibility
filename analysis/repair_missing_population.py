"""
Targeted repair of missing population values in metrics.csv.

Re-runs only the (station, mode, minutes) isochrones that produced area = 0
or degenerate tiny polygons (area < 0.01 km²), using the fixed _alpha_shape()
which now falls back to convex hull when the alpha-shape is < 5% of the convex hull.

All network and raster data is loaded from cache — no downloads required.

Outputs patched versions of:
  data/isochrones_walk.geojson
  data/isochrones_bike.geojson
  data/metrics.csv
  web/public/data/   (copies of all three)
"""

import json
import logging
import os
import shutil
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape, mapping, Point

# Add the analysis directory to path so local imports work
sys.path.insert(0, os.path.dirname(__file__))

from config import (
    BIKE_SPEED_MS,
    CRS_METRIC,
    CRS_WGS84,
    DATA_DIR,
    WORLDPOP_TIFF,
    WALK_SPEED_MS,
)
from isochrones import compute_isochrone
from network import get_walk_network, get_bike_network
from population import zonal_population

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR_PATH = BASE_DIR / "data"
WEB_DATA_DIR = BASE_DIR / "web" / "public" / "data"

WALK_ISO_PATH = DATA_DIR_PATH / "isochrones_walk.geojson"
BIKE_ISO_PATH = DATA_DIR_PATH / "isochrones_bike.geojson"
METRICS_PATH  = DATA_DIR_PATH / "metrics.csv"

AREA_THRESHOLD_KM2 = 0.01  # treat anything below this as degenerate


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_iso_geojson(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def save_iso_geojson(data: dict, path: Path) -> None:
    with open(path, "w") as f:
        json.dump(data, f)
    logger.info("Saved %s (%d features)", path.name, len(data["features"]))


def area_km2_of_polygon(geojson_geom: dict) -> float:
    """Compute area in km² of a GeoJSON geometry (assumed WGS84)."""
    poly_wgs = shape(geojson_geom)
    gdf = gpd.GeoDataFrame(geometry=[poly_wgs], crs=CRS_WGS84)
    poly_metric = gdf.to_crs(CRS_METRIC).geometry.iloc[0]
    return poly_metric.area / 1e6


def find_bad_entries(iso_data: dict, mode: str) -> list[tuple[str, int]]:
    """
    Return list of (station_id, minutes) where area_km2 < threshold.
    """
    bad = []
    for feat in iso_data["features"]:
        props = feat["properties"]
        area = props.get("area_km2", 0.0) or 0.0
        if area < AREA_THRESHOLD_KM2:
            bad.append((props["station_id"], props["minutes"]))
    return bad


# ── Main repair logic ──────────────────────────────────────────────────────────

def main():
    logger.info("Loading cached networks …")
    G_walk = get_walk_network()
    G_bike = get_bike_network()

    logger.info("Loading stations …")
    stations_gdf = gpd.read_file(DATA_DIR_PATH / "stations.geojson")
    station_points = {
        row["station_id"]: row["geometry"]
        for _, row in stations_gdf.iterrows()
    }

    logger.info("Loading isochrone GeoJSONs …")
    walk_data = load_iso_geojson(WALK_ISO_PATH)
    bike_data = load_iso_geojson(BIKE_ISO_PATH)

    # Identify bad entries
    bad_walk = find_bad_entries(walk_data, "walk")
    bad_bike = find_bad_entries(bike_data, "bike")

    logger.info("Bad walk entries: %d", len(bad_walk))
    logger.info("Bad bike entries: %d", len(bad_bike))

    if not bad_walk and not bad_bike:
        logger.info("No bad entries found — nothing to repair.")
        return

    # ── Re-compute bad isochrones ──────────────────────────────────────────────

    def repair_entries(iso_data, bad_entries, mode, G, speed_ms):
        """Mutate iso_data in-place, returning list of repaired (station_id, minutes, old_area, new_area, new_pop)."""
        # Build index: (station_id, minutes) → feature index
        idx = {
            (f["properties"]["station_id"], f["properties"]["minutes"]): i
            for i, f in enumerate(iso_data["features"])
        }

        results = []
        total = len(bad_entries)
        for n, (sid, minutes) in enumerate(bad_entries, 1):
            logger.info("[%d/%d] Repairing %s | %s | %d min", n, total, sid, mode, minutes)

            point = station_points.get(sid)
            if point is None:
                logger.warning("Station %s not found — skipping.", sid)
                continue

            old_area = iso_data["features"][idx[(sid, minutes)]]["properties"]["area_km2"]

            try:
                new_poly = compute_isochrone(G, point, speed_ms, minutes)
            except Exception as exc:
                logger.error("compute_isochrone failed for %s %s %d: %s", sid, mode, minutes, exc)
                continue

            # Area in km²
            new_area = round(
                gpd.GeoDataFrame(geometry=[new_poly], crs=CRS_WGS84)
                .to_crs(CRS_METRIC)
                .geometry.iloc[0].area / 1e6,
                4,
            )

            # Population via zonal stats
            poly_gdf = gpd.GeoDataFrame(geometry=[new_poly], crs=CRS_WGS84)
            pops = zonal_population(poly_gdf, str(WORLDPOP_TIFF))
            new_pop = pops[0] if pops else 0

            # Patch the feature in-place
            feat = iso_data["features"][idx[(sid, minutes)]]
            feat["geometry"] = mapping(new_poly)
            feat["properties"]["area_km2"] = new_area
            feat["properties"]["population"] = new_pop

            results.append((sid, minutes, old_area, new_area, new_pop))
            logger.info(
                "  %s %s %d min: area %.4f → %.4f km², pop → %d",
                sid, mode, minutes, old_area, new_area, new_pop,
            )

        return results

    logger.info("\n=== Repairing walk isochrones ===")
    walk_results = repair_entries(walk_data, bad_walk, "walk", G_walk, WALK_SPEED_MS)

    logger.info("\n=== Repairing bike isochrones ===")
    bike_results = repair_entries(bike_data, bad_bike, "bike", G_bike, BIKE_SPEED_MS)

    # ── Save patched GeoJSONs ──────────────────────────────────────────────────

    save_iso_geojson(walk_data, WALK_ISO_PATH)
    save_iso_geojson(bike_data, BIKE_ISO_PATH)

    # ── Patch metrics.csv ─────────────────────────────────────────────────────

    logger.info("Patching metrics.csv …")
    metrics = pd.read_csv(METRICS_PATH)
    metrics = metrics.set_index("station_id")

    # Build lookup from repaired isochrones
    # Walk
    for sid, minutes, old_area, new_area, new_pop in walk_results:
        col_area = f"walk_area_{minutes}"
        col_pop  = f"walk_pop_{minutes}"
        if sid in metrics.index:
            metrics.at[sid, col_area] = new_area
            metrics.at[sid, col_pop]  = new_pop

    # Bike
    for sid, minutes, old_area, new_area, new_pop in bike_results:
        col_area = f"bike_area_{minutes}"
        col_pop  = f"bike_pop_{minutes}"
        if sid in metrics.index:
            metrics.at[sid, col_area] = new_area
            metrics.at[sid, col_pop]  = new_pop

    metrics = metrics.reset_index()
    metrics.to_csv(METRICS_PATH, index=False)
    logger.info("Saved metrics.csv")

    # ── Copy to web/public/data/ ───────────────────────────────────────────────

    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for fname in ["isochrones_walk.geojson", "isochrones_bike.geojson", "metrics.csv"]:
        src = DATA_DIR_PATH / fname
        dst = WEB_DATA_DIR / fname
        try:
            shutil.copy2(src, dst)
            logger.info("Copied %s → web/public/data/", fname)
        except shutil.SameFileError:
            logger.info("%s is already in sync (hardlink/symlink)", fname)

    # ── Before/after summary ──────────────────────────────────────────────────

    print("\n" + "=" * 60)
    print("REPAIR SUMMARY")
    print("=" * 60)

    all_results = (
        [("walk", *r) for r in walk_results]
        + [("bike", *r) for r in bike_results]
    )

    print(f"{'Mode':<5} {'Station':<10} {'Min':>4}  {'OldArea':>9}  {'NewArea':>9}  {'NewPop':>8}")
    print("-" * 60)
    for mode, sid, minutes, old_area, new_area, new_pop in sorted(
        all_results, key=lambda x: (x[0], x[1], x[2])
    ):
        print(f"{mode:<5} {sid:<10} {minutes:>4}  {old_area:>9.4f}  {new_area:>9.4f}  {new_pop:>8,}")

    print(f"\nTotal entries repaired: {len(all_results)}")
    print(f"  Walk: {len(walk_results)}")
    print(f"  Bike: {len(bike_results)}")

    # ── Final verification ────────────────────────────────────────────────────

    print("\n" + "=" * 60)
    print("VERIFICATION: Checking remaining zeros in 4 pop columns")
    print("=" * 60)

    metrics_check = pd.read_csv(METRICS_PATH)
    pop_cols = ["walk_pop_10", "walk_pop_15", "bike_pop_10", "bike_pop_15"]
    remaining_zeros = []
    for _, row in metrics_check.iterrows():
        for col in pop_cols:
            val = row[col]
            if pd.isna(val) or val == 0:
                remaining_zeros.append((row["station_id"], row["name_uz"], col))

    if remaining_zeros:
        print(f"WARNING: {len(remaining_zeros)} remaining zeros:")
        for sid, name, col in remaining_zeros:
            print(f"  {sid} ({name}): {col}")
    else:
        print("All population values are non-zero.")

    # Monotonicity check: pop_5 ≤ pop_10 ≤ pop_15
    print("\nMonotonicity check (pop_5 ≤ pop_10 ≤ pop_15):")
    violations = []
    for _, row in metrics_check.iterrows():
        sid = row["station_id"]
        for mode in ["walk", "bike"]:
            p5  = row.get(f"{mode}_pop_5",  0) or 0
            p10 = row.get(f"{mode}_pop_10", 0) or 0
            p15 = row.get(f"{mode}_pop_15", 0) or 0
            if p10 < p5:
                violations.append(f"  {sid} {mode}: pop_10={p10} < pop_5={p5}")
            if p15 < p10:
                violations.append(f"  {sid} {mode}: pop_15={p15} < pop_10={p10}")
    if violations:
        print(f"  {len(violations)} monotonicity violations:")
        for v in violations:
            print(v)
    else:
        print("  All pass.")


if __name__ == "__main__":
    main()
