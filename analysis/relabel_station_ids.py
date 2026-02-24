"""
Relabel station IDs in all data files from OSM_xx → CSV_xx.

The original pipeline used OSM-derived IDs (OSM_00–OSM_61 with gaps after
removing 14 invalid stations).  This script replaces them with clean sequential
IDs (CSV_00–CSV_48) based on the authoritative tashkent_metro_stations.csv.

No isochrone recomputation — purely an in-place ID rename across:
  data/stations.geojson
  data/isochrones_walk.geojson
  data/isochrones_bike.geojson
  data/metrics.csv
  (web/public/data/ is hardlinked — updated automatically)
"""

import json
import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR      = Path(__file__).resolve().parent.parent
DATA_DIR      = BASE_DIR / "data"
CSV_PATH      = BASE_DIR / "tashkent_metro_stations.csv"

FILES = {
    "stations":       DATA_DIR / "stations.geojson",
    "iso_walk":       DATA_DIR / "isochrones_walk.geojson",
    "iso_bike":       DATA_DIR / "isochrones_bike.geojson",
    "metrics":        DATA_DIR / "metrics.csv",
}


def build_id_map() -> dict[str, str]:
    """
    Match current station_ids in metrics.csv to CSV row order by station name.
    Returns {old_id: new_id} mapping.
    """
    csv_stations = pd.read_csv(CSV_PATH)          # 49 rows, columns: name, latitude, longitude, line
    metrics      = pd.read_csv(FILES["metrics"])  # 49 rows, ordered by current station_id

    # Verify counts
    assert len(csv_stations) == len(metrics), (
        f"Row count mismatch: CSV has {len(csv_stations)}, metrics has {len(metrics)}"
    )

    # Verify names align (strip whitespace for safety)
    csv_names     = csv_stations["name"].str.strip().tolist()
    metrics_names = metrics["name_uz"].str.strip().tolist()

    mismatches = [
        (i, csv_names[i], metrics_names[i])
        for i in range(len(csv_names))
        if csv_names[i] != metrics_names[i]
    ]
    if mismatches:
        logger.warning("Name mismatches (will use positional mapping):")
        for i, csv_name, met_name in mismatches:
            logger.warning("  row %d: CSV=%r  metrics=%r", i, csv_name, met_name)

    id_map = {}
    for i, old_id in enumerate(metrics["station_id"]):
        new_id = f"CSV_{i:02d}"
        id_map[old_id] = new_id
        logger.debug("  %s → %s  (%s)", old_id, new_id, metrics_names[i])

    return id_map


def relabel_geojson(path: Path, id_map: dict[str, str]) -> int:
    """Relabel station_id in every GeoJSON feature. Returns count updated."""
    with open(path) as f:
        data = json.load(f)

    updated = 0
    for feat in data["features"]:
        old = feat["properties"].get("station_id")
        if old in id_map:
            feat["properties"]["station_id"] = id_map[old]
            updated += 1
        elif old is not None:
            logger.warning("%s: unknown station_id %r — not relabelled", path.name, old)

    with open(path, "w") as f:
        json.dump(data, f)

    logger.info("%-35s  %d/%d features relabelled", path.name, updated, len(data["features"]))
    return updated


def relabel_metrics(path: Path, id_map: dict[str, str]) -> int:
    """Relabel station_id column in metrics CSV. Returns count updated."""
    df = pd.read_csv(path)
    original = df["station_id"].copy()
    df["station_id"] = df["station_id"].map(id_map).fillna(df["station_id"])
    changed = (df["station_id"] != original).sum()
    df.to_csv(path, index=False)
    logger.info("%-35s  %d/%d rows relabelled", path.name, changed, len(df))
    return changed


def main():
    logger.info("Building OSM_xx → CSV_xx ID mapping …")
    id_map = build_id_map()

    logger.info("ID map (%d entries):", len(id_map))
    for old, new in id_map.items():
        logger.info("  %s → %s", old, new)

    logger.info("\nRelabelling GeoJSON files …")
    relabel_geojson(FILES["stations"], id_map)
    relabel_geojson(FILES["iso_walk"], id_map)
    relabel_geojson(FILES["iso_bike"], id_map)

    logger.info("\nRelabelling metrics.csv …")
    relabel_metrics(FILES["metrics"], id_map)

    logger.info("\nDone.  Verifying new IDs …")
    df = pd.read_csv(FILES["metrics"])
    ids = df["station_id"].tolist()
    expected = [f"CSV_{i:02d}" for i in range(49)]
    if ids == expected:
        logger.info("All station IDs are now CSV_00 … CSV_48  ✓")
    else:
        unexpected = [x for x in ids if x not in expected]
        logger.warning("Unexpected IDs still present: %s", unexpected)

    print("\nFinal station list:")
    print(df[["station_id", "name_uz", "line"]].to_string(index=False))


if __name__ == "__main__":
    main()
