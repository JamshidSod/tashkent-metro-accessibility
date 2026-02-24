"""
Isochrone / Pedestrian Catchment Area computation using ego-graph method.

Method reference:
  Gutiérrez, J. & García-Palomares, J.C. (2009). New spatial approaches to the
  study of public transport accessibility. Transport Policy, 16(6), 342-348.

Implementation:
  1. Project station point to network CRS.
  2. Find nearest network node.
  3. Compute ego-graph with Dijkstra up to max_distance = speed × time (metres).
  4. Extract node coordinates and generate polygon via alpha-shape or convex hull.
  5. Reproject polygon to WGS84 for GeoJSON output.

Edge-weight attribute used: 'length' (metres), set by OSMnx from OSM geometry.
"""

import logging
from typing import List

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.ops import unary_union

from config import (
    ALPHA_SHAPE_ALPHA,
    BIKE_SPEED_MS,
    CRS_METRIC,
    CRS_WGS84,
    TIME_THRESHOLDS_MIN,
    WALK_SPEED_MS,
)

logger = logging.getLogger(__name__)


def _alpha_shape(points: np.ndarray, alpha: float) -> Polygon:
    """
    Compute alpha shape (concave hull) of a point cloud.

    Falls back to convex hull if alphashape is not available or if
    fewer than 4 unique points are present.

    Parameters
    ----------
    points : (N, 2) array of (x, y) coordinates in a metric CRS
    alpha  : inverse of radius (larger → more concave; 0 → convex hull)
    """
    if len(points) < 4:
        return MultiPoint([Point(p) for p in points]).convex_hull

    convex = MultiPoint([Point(p) for p in points]).convex_hull
    try:
        import alphashape
        shape = alphashape.alphashape(points, alpha)
        if shape.is_empty or not shape.is_valid:
            raise ValueError("degenerate alpha shape")
        # Reject if result is < 5% of convex hull area (degenerate tiny polygon)
        if convex.area > 0 and shape.area / convex.area < 0.05:
            raise ValueError(
                f"alpha shape too small ({shape.area / convex.area:.3f} of convex hull)"
            )
        return shape
    except Exception as exc:
        logger.debug("Alpha-shape failed (%s); using convex hull.", exc)
        return convex


def compute_isochrone(
    G: nx.MultiDiGraph,
    station_point: Point,
    speed_ms: float,
    time_min: int,
    crs_metric: str = CRS_METRIC,
    alpha: float = ALPHA_SHAPE_ALPHA,
) -> Polygon:
    """
    Compute a single isochrone polygon for one station / speed / time combination.

    Parameters
    ----------
    G            : projected OSMnx graph (metric CRS)
    station_point: station geometry in WGS84
    speed_ms     : travel speed in m/s
    time_min     : time threshold in minutes
    crs_metric   : metric CRS EPSG string for reprojection
    alpha        : alpha-shape concavity parameter (metres)

    Returns
    -------
    Polygon in WGS84 (EPSG:4326)
    """
    # Project station point from WGS84 to metric CRS
    station_gdf = gpd.GeoDataFrame(geometry=[station_point], crs=CRS_WGS84)
    station_proj = station_gdf.to_crs(crs_metric).geometry.iloc[0]

    # Find nearest network node
    nearest_node = ox.distance.nearest_nodes(
        G, X=station_proj.x, Y=station_proj.y
    )

    # Maximum travel distance in metres
    max_dist_m = speed_ms * time_min * 60

    # Subgraph reachable within max_dist_m via Dijkstra on 'length'
    subgraph = nx.ego_graph(
        G, nearest_node, radius=max_dist_m, distance="length"
    )

    if subgraph.number_of_nodes() < 3:
        logger.warning("Subgraph too small; returning station buffer.")
        buf_proj = station_proj.buffer(max_dist_m * 0.5)
        buf_gdf  = gpd.GeoDataFrame(geometry=[buf_proj], crs=crs_metric)
        return buf_gdf.to_crs(CRS_WGS84).geometry.iloc[0]

    # Collect node coordinates (already in metric CRS)
    node_data = subgraph.nodes(data=True)
    coords = np.array([[d["x"], d["y"]] for _, d in node_data])

    # Generate polygon
    poly_metric = _alpha_shape(coords, alpha / max_dist_m)

    # Reproject to WGS84
    poly_gdf = gpd.GeoDataFrame(geometry=[poly_metric], crs=crs_metric)
    return poly_gdf.to_crs(CRS_WGS84).geometry.iloc[0]


def compute_all_isochrones(
    stations: gpd.GeoDataFrame,
    G_walk: nx.MultiDiGraph,
    G_bike: nx.MultiDiGraph,
    thresholds: List[int] = TIME_THRESHOLDS_MIN,
) -> gpd.GeoDataFrame:
    """
    Compute isochrones for all stations × modes × time thresholds.

    Returns a GeoDataFrame with one row per (station × mode × threshold),
    columns: station_id, mode, minutes, geometry (WGS84), area_km2.
    """
    rows = []
    total = len(stations) * 2 * len(thresholds)
    done  = 0

    for _, station in stations.iterrows():
        sid   = station["station_id"]
        point = station["geometry"]

        for mode, G, speed in [
            ("walk", G_walk, WALK_SPEED_MS),
            ("bike", G_bike, BIKE_SPEED_MS),
        ]:
            for t in thresholds:
                logger.info("[%d/%d] %s | %s | %d min", done + 1, total, sid, mode, t)
                try:
                    poly = compute_isochrone(G, point, speed, t)
                    # Area in km² (reproject to metric CRS for accurate area)
                    poly_proj = (
                        gpd.GeoDataFrame(geometry=[poly], crs=CRS_WGS84)
                        .to_crs(CRS_METRIC)
                        .geometry.iloc[0]
                    )
                    area_km2 = poly_proj.area / 1e6
                except Exception as exc:
                    logger.error("Failed %s %s %d min: %s", sid, mode, t, exc)
                    poly     = Point(point).buffer(0)  # empty fallback
                    area_km2 = 0.0

                rows.append({
                    "station_id": sid,
                    "mode":       mode,
                    "minutes":    t,
                    "geometry":   poly,
                    "area_km2":   round(area_km2, 4),
                })
                done += 1

    gdf = gpd.GeoDataFrame(rows, crs=CRS_WGS84)
    return gdf


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from stations import get_stations
    from network  import get_walk_network, get_bike_network
    from config   import OSM_PLACE

    stations = get_stations(OSM_PLACE)
    Gw = get_walk_network()
    Gb = get_bike_network()

    iso = compute_all_isochrones(stations.head(2), Gw, Gb, thresholds=[10])
    print(iso[["station_id", "mode", "minutes", "area_km2"]])
