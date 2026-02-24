"""
OSMnx network download and caching for Tashkent.

Networks are cached as GraphML files with the OSM download timestamp
embedded in their metadata — a key reproducibility requirement for research
use. See: Boeing, G. (2017). OSMnx: New methods for acquiring, constructing,
analyzing, and visualizing complex street networks. Computers, Environment and
Urban Systems, 65, 126-139.
"""

import logging
import os
from datetime import datetime, timezone

import networkx as nx
import osmnx as ox

from config import (
    BIKE_GRAPHML, BIKE_NETWORK_TYPE, CACHE_DIR,
    CRS_METRIC, OSM_PLACE,
    WALK_GRAPHML, WALK_NETWORK_TYPE,
)

logger = logging.getLogger(__name__)


def _save_with_timestamp(G: nx.MultiDiGraph, path: str) -> None:
    """Persist graph to GraphML, embedding the OSM download timestamp."""
    ts = datetime.now(timezone.utc).isoformat()
    G.graph["osm_download_timestamp"] = ts
    ox.save_graphml(G, path)
    logger.info("Saved %s  (OSM download timestamp: %s)", path, ts)


def download_network(
    place: str, network_type: str, cache_path: str, force: bool = False
) -> nx.MultiDiGraph:
    """
    Download (or load from cache) an OSMnx street network for *place*.

    Parameters
    ----------
    place        : OSM place string (e.g. "Tashkent, Uzbekistan")
    network_type : "walk" or "bike"
    cache_path   : where to persist the GraphML file
    force        : re-download even if cached

    Returns
    -------
    Projected MultiDiGraph in UTM Zone 38N (EPSG:32638)
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    if os.path.exists(cache_path) and not force:
        logger.info("Loading cached %s network from %s …", network_type, cache_path)
        G = ox.load_graphml(cache_path)
        ts = G.graph.get("osm_download_timestamp", "unknown")
        logger.info("Network cached at OSM timestamp: %s", ts)
    else:
        logger.info("Downloading %s network for %s from OSM …", network_type, place)
        G = ox.graph_from_place(place, network_type=network_type, retain_all=False)
        _save_with_timestamp(G, cache_path)

    # Project to metric CRS for distance-based calculations
    G_proj = ox.project_graph(G, to_crs=CRS_METRIC)
    logger.info(
        "%s network: %d nodes, %d edges",
        network_type, G_proj.number_of_nodes(), G_proj.number_of_edges(),
    )
    return G_proj


def get_walk_network(force: bool = False) -> nx.MultiDiGraph:
    return download_network(OSM_PLACE, WALK_NETWORK_TYPE, WALK_GRAPHML, force)


def get_bike_network(force: bool = False) -> nx.MultiDiGraph:
    return download_network(OSM_PLACE, BIKE_NETWORK_TYPE, BIKE_GRAPHML, force)


def get_osm_timestamp(network_type: str) -> str:
    """Return the stored OSM download timestamp for a cached network."""
    path = WALK_GRAPHML if network_type == "walk" else BIKE_GRAPHML
    if not os.path.exists(path):
        return "not cached"
    G = ox.load_graphml(path)
    return G.graph.get("osm_download_timestamp", "unknown")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    Gw = get_walk_network()
    Gb = get_bike_network()
    print("Walk network nodes:", Gw.number_of_nodes())
    print("Bike network nodes:", Gb.number_of_nodes())
