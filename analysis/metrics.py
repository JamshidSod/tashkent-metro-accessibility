"""
Compute aggregate accessibility metrics per station.

Metrics produced (wide-format CSV, one row per station):
  - walk_area_{5,10,15}  : walking catchment area (km²)
  - walk_pop_{5,10,15}   : population within walking catchment
  - bike_area_{5,10,15}  : cycling catchment area (km²)
  - bike_pop_{5,10,15}   : population within cycling catchment
  - prd_walk             : Pedestrian Route Directness for walking network
  - prd_bike             : Route Directness for cycling network

Pedestrian Route Directness (PRD):
  PRD here = mean(Euclidean distance / Network distance) for sampled OD pairs.
  PRD ∈ (0, 1]; higher → straighter paths (more direct street network).

  Note on convention: Stangl (2012) defines PRD as Network/Euclidean ≥ 1
  (lower = more direct). This implementation uses the inverse (Euclidean/Network ≤ 1),
  so higher values mean more direct — equivalent information, opposite direction.
  Stangl's benchmark: ~1.3 (direct grid) → 0.77 in our convention; ~1.6 (circuitous) → 0.63.

  Reference: Stangl, P. (2012). The pedestrian route directness test: A new
             level-of-service model. Urban Design International, 17(3), 228–238.
             DOI: 10.1057/udi.2012.14
"""

import logging
import random
from typing import Optional

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
from shapely.geometry import Point

from config import (
    CRS_METRIC,
    CRS_WGS84,
    PRD_BUFFER_M,
    PRD_SAMPLE_N,
    TIME_THRESHOLDS_MIN,
)

logger = logging.getLogger(__name__)


def compute_prd(
    G: nx.MultiDiGraph,
    station_point: Point,
    buffer_m: float = PRD_BUFFER_M,
    n_samples: int = PRD_SAMPLE_N,
    seed: int = 42,
) -> Optional[float]:
    """
    Compute the Route Directness for a station on a given network.

    Samples `n_samples` random points within a Euclidean buffer of the station,
    then computes Euclidean / network distance for each, returning the mean ratio.
    Higher values indicate more direct (straighter) paths.

    Formula: mean(Euclidean_dist / Network_dist) ∈ (0, 1]
    This is the inverse of Stangl's (2012) PRD convention (Network/Euclidean ≥ 1).

    Parameters
    ----------
    G             : projected OSMnx graph (metric CRS)
    station_point : station geometry in WGS84
    buffer_m      : buffer radius for sampling OD destinations (metres)
    n_samples     : number of OD pairs to sample
    seed          : random seed for reproducibility

    Returns
    -------
    Mean directness ratio (float in (0, 1]) or None if computation fails.
    """
    random.seed(seed)
    np.random.seed(seed)

    # Project station to metric CRS
    station_gdf  = gpd.GeoDataFrame(geometry=[station_point], crs=CRS_WGS84)
    station_proj = station_gdf.to_crs(CRS_METRIC).geometry.iloc[0]
    sx, sy       = station_proj.x, station_proj.y

    # Find nearest node to station
    origin_node = ox.distance.nearest_nodes(G, X=sx, Y=sy)

    # Sample random destination points within buffer
    buffer_poly = station_proj.buffer(buffer_m)
    min_x, min_y, max_x, max_y = buffer_poly.bounds

    ratios = []
    attempts = 0
    max_attempts = n_samples * 10

    while len(ratios) < n_samples and attempts < max_attempts:
        attempts += 1
        rx = random.uniform(min_x, max_x)
        ry = random.uniform(min_y, max_y)
        dest_point = Point(rx, ry)
        if not buffer_poly.contains(dest_point):
            continue

        euclid = station_proj.distance(dest_point)
        if euclid < 10:  # skip points too close to station
            continue

        dest_node = ox.distance.nearest_nodes(G, X=rx, Y=ry)
        if dest_node == origin_node:
            continue

        try:
            net_dist = nx.shortest_path_length(
                G, origin_node, dest_node, weight="length"
            )
            if net_dist > 0:
                ratios.append(euclid / net_dist)
        except nx.NetworkXNoPath:
            continue

    if not ratios:
        logger.warning("Could not compute PRD (no valid paths sampled).")
        return None

    return round(float(np.mean(ratios)), 4)


def build_metrics_table(
    stations: gpd.GeoDataFrame,
    isochrones: gpd.GeoDataFrame,
    G_walk: nx.MultiDiGraph,
    G_bike: nx.MultiDiGraph,
    thresholds: list = TIME_THRESHOLDS_MIN,
) -> pd.DataFrame:
    """
    Assemble the wide-format metrics table.

    Parameters
    ----------
    stations   : station GeoDataFrame (WGS84)
    isochrones : isochrones GeoDataFrame with 'population' column
    G_walk     : projected walk network
    G_bike     : projected bike network
    thresholds : list of time thresholds in minutes

    Returns
    -------
    DataFrame with one row per station, all area/population/PRD metrics.
    """
    records = []
    n = len(stations)

    for i, (_, station) in enumerate(stations.iterrows()):
        sid = station["station_id"]
        logger.info("[%d/%d] Building metrics for %s …", i + 1, n, sid)

        row = {
            "station_id": sid,
            "name_uz":    station["name_uz"],
            "name_ru":    station["name_ru"],
            "line":       station["line"],
            "lon":        station.geometry.x,
            "lat":        station.geometry.y,
        }

        # Area and population per mode × threshold
        for mode in ("walk", "bike"):
            for t in thresholds:
                mask = (
                    (isochrones["station_id"] == sid) &
                    (isochrones["mode"]       == mode) &
                    (isochrones["minutes"]    == t)
                )
                subset = isochrones[mask]
                if subset.empty:
                    row[f"{mode}_area_{t}"] = None
                    row[f"{mode}_pop_{t}"]  = None
                else:
                    row[f"{mode}_area_{t}"] = float(subset["area_km2"].iloc[0])
                    row[f"{mode}_pop_{t}"]  = int(subset["population"].iloc[0])

        # Pedestrian Route Directness
        logger.info("  Computing PRD (walk) …")
        row["prd_walk"] = compute_prd(G_walk, station.geometry)
        logger.info("  Computing PRD (bike) …")
        row["prd_bike"] = compute_prd(G_bike, station.geometry)

        records.append(row)

    df = pd.DataFrame(records)
    return df


def prd_label(prd: Optional[float]) -> str:
    """
    Convert numeric PRD directness ratio to a human-readable label.

    Thresholds derived from Stangl (2012) benchmarks, converted to our
    Euclidean/Network convention (inverse of Stangl's Network/Euclidean):
      Stangl "direct grid" PRD ≈ 1.3  → our ratio ≈ 0.77
      Stangl "circuitous"  PRD ≈ 1.6  → our ratio ≈ 0.63

      ≥ 0.80 : High directness  (near-Euclidean paths, well-connected grid)
      ≥ 0.65 : Medium directness
      <  0.65 : Low directness   (circuitous network, barriers, dead ends)

    Reference: Stangl, P. (2012). Urban Design International, 17(3), 228–238.
    """
    if prd is None:
        return "N/A"
    if prd >= 0.80:
        return "High"
    if prd >= 0.65:
        return "Medium"
    return "Low"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from stations   import get_stations
    from network    import get_walk_network, get_bike_network
    from isochrones import compute_all_isochrones
    from population import download_worldpop, add_population_to_isochrones
    from config     import OSM_PLACE

    sts  = get_stations(OSM_PLACE).head(3)
    Gw   = get_walk_network()
    Gb   = get_bike_network()
    iso  = compute_all_isochrones(sts, Gw, Gb)
    rast = download_worldpop()
    iso  = add_population_to_isochrones(iso, rast)
    tbl  = build_metrics_table(sts, iso, Gw, Gb)
    print(tbl.to_string())
