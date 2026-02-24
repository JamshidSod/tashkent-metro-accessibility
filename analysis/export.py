"""
Export pipeline outputs to data/ directory.

Outputs:
  data/stations.geojson          — all metro stations
  data/isochrones_walk.geojson   — walking catchment polygons
  data/isochrones_bike.geojson   — cycling catchment polygons
  data/metrics.csv               — wide-format per-station metrics table
"""

import logging
import os

import geopandas as gpd
import pandas as pd

from config import CRS_WGS84, DATA_DIR

logger = logging.getLogger(__name__)


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def export_stations(stations: gpd.GeoDataFrame) -> str:
    """Write stations GeoDataFrame to GeoJSON (WGS84)."""
    ensure_data_dir()
    path = os.path.join(DATA_DIR, "stations.geojson")

    out = stations.copy()
    if out.crs is None or out.crs.to_epsg() != 4326:
        out = out.to_crs(CRS_WGS84)

    out.to_file(path, driver="GeoJSON")
    logger.info("Wrote %s  (%d features)", path, len(out))
    return path


def export_isochrones(isochrones: gpd.GeoDataFrame, mode: str) -> str:
    """
    Write isochrones for a single mode (walk | bike) to GeoJSON.

    Properties included: station_id, mode, minutes, area_km2, population.
    """
    ensure_data_dir()
    assert mode in ("walk", "bike"), f"mode must be 'walk' or 'bike', got {mode!r}"
    path = os.path.join(DATA_DIR, f"isochrones_{mode}.geojson")

    subset = isochrones[isochrones["mode"] == mode].copy()
    if subset.crs is None or subset.crs.to_epsg() != 4326:
        subset = subset.to_crs(CRS_WGS84)

    # Drop rows with empty geometries (failed isochrones)
    valid = subset[~subset.geometry.is_empty & subset.geometry.notna()]
    if len(valid) < len(subset):
        logger.warning("Dropped %d empty geometries from %s isochrones.", len(subset) - len(valid), mode)

    valid.to_file(path, driver="GeoJSON")
    logger.info("Wrote %s  (%d features)", path, len(valid))
    return path


def export_metrics(metrics: pd.DataFrame) -> str:
    """Write metrics DataFrame to CSV."""
    ensure_data_dir()
    path = os.path.join(DATA_DIR, "metrics.csv")
    metrics.to_csv(path, index=False)
    logger.info("Wrote %s  (%d rows × %d cols)", path, len(metrics), len(metrics.columns))
    return path


def export_all(
    stations: gpd.GeoDataFrame,
    isochrones: gpd.GeoDataFrame,
    metrics: pd.DataFrame,
) -> dict:
    """
    Run all exports and return a dict of output paths.

    Parameters
    ----------
    stations   : station GeoDataFrame
    isochrones : combined walk + bike isochrone GeoDataFrame
    metrics    : wide-format metrics DataFrame

    Returns
    -------
    dict with keys: stations, isochrones_walk, isochrones_bike, metrics
    """
    return {
        "stations":         export_stations(stations),
        "isochrones_walk":  export_isochrones(isochrones, "walk"),
        "isochrones_bike":  export_isochrones(isochrones, "bike"),
        "metrics":          export_metrics(metrics),
    }
