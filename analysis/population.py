"""
Population estimation within catchment areas using WorldPop raster data.

Data source: WorldPop (www.worldpop.org) — UZB 2020 100m constrained raster.
Citation:
  WorldPop (www.worldpop.org - School of Geography and Environmental Science,
  University of Southampton), (2020). Uzbekistan 100m Population.
  DOI: 10.5258/SOTON/WP00645

Method: Zonal statistics (sum) of population pixels within each isochrone polygon.
  rasterstats.zonal_stats() reprojects the vector to the raster CRS internally.
"""

import logging
import os
import urllib.request

import geopandas as gpd
from shapely.geometry import mapping

from config import CACHE_DIR, WORLDPOP_TIFF, WORLDPOP_URL

logger = logging.getLogger(__name__)


def download_worldpop(url: str = WORLDPOP_URL, dest: str = WORLDPOP_TIFF) -> str:
    """
    Download the WorldPop raster if not already cached.

    Returns the local path to the TIFF file.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    if os.path.exists(dest):
        logger.info("WorldPop raster already cached at %s", dest)
        return dest

    logger.info("Downloading WorldPop raster from %s …", url)
    logger.info("This may take several minutes (~50 MB file).")

    def _reporthook(block_num, block_size, total_size):
        if total_size > 0:
            pct = block_num * block_size * 100 / total_size
            if int(pct) % 10 == 0:
                logger.info("  Downloaded %.0f%%", min(pct, 100))

    urllib.request.urlretrieve(url, dest, reporthook=_reporthook)
    logger.info("WorldPop raster saved to %s", dest)
    return dest


def zonal_population(
    polygons: gpd.GeoDataFrame,
    raster_path: str,
    nodata_value: float = -99999.0,
) -> list:
    """
    Compute population sum for each polygon using zonal statistics.

    Parameters
    ----------
    polygons      : GeoDataFrame of catchment polygons (any CRS; reprojected internally)
    raster_path   : path to WorldPop GeoTIFF
    nodata_value  : raster nodata value to exclude

    Returns
    -------
    List of population counts (int), one per polygon row.
    """
    try:
        from rasterstats import zonal_stats
    except ImportError as e:
        raise ImportError(
            "rasterstats is required: pip install rasterstats"
        ) from e

    # rasterstats works best with WGS84 geometries; reproject if needed
    if polygons.crs and polygons.crs.to_epsg() != 4326:
        polys_wgs = polygons.to_crs("EPSG:4326")
    else:
        polys_wgs = polygons

    geoms = [mapping(g) for g in polys_wgs.geometry]

    stats = zonal_stats(
        geoms,
        raster_path,
        stats=["sum"],
        nodata=nodata_value,
        all_touched=False,
    )

    populations = []
    for s in stats:
        val = s.get("sum")
        populations.append(int(round(val)) if val is not None and val >= 0 else 0)

    return populations


def add_population_to_isochrones(
    isochrones: gpd.GeoDataFrame,
    raster_path: str,
) -> gpd.GeoDataFrame:
    """
    Add a 'population' column to the isochrones GeoDataFrame.

    Computes zonal population sum for each catchment polygon.
    """
    logger.info("Computing zonal population statistics for %d polygons …", len(isochrones))
    populations = zonal_population(isochrones, raster_path)
    isochrones = isochrones.copy()
    isochrones["population"] = populations
    return isochrones


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raster = download_worldpop()
    print("Raster cached at:", raster)
