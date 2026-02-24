"""
Configuration for Tashkent Metro Accessibility Analysis.

All parameters are documented with their sources for reproducibility.
References:
  - Brons et al. (2009). Access to railway stations and its potential in increasing rail use.
    Transportation Research Part A, 43(2), 136-144.
  - Stangl, P. (2012). The pedestrian route directness test: A new level-of-service model.
    Urban Design International, 17(3), 228-238. DOI: 10.1057/udi.2012.14
  - Gutiérrez & García-Palomares (2009). New spatial approaches to the study of
    public transport accessibility. Transport Policy, 16(6), 342-348.
"""

# ── Travel speeds ──────────────────────────────────────────────────────────────
# Walking: 5 km/h is the standard assumption in pedestrian accessibility research.
# Brons et al. (2009) and Iacono et al. (2010) both adopt this value.
WALK_SPEED_KMH = 5.0          # km/h
WALK_SPEED_MS  = WALK_SPEED_KMH * 1000 / 3600  # → 1.389 m/s

# Cycling: 14 km/h is used by Brons et al. (2009) for urban bike access to stations.
BIKE_SPEED_KMH = 14.0         # km/h
BIKE_SPEED_MS  = BIKE_SPEED_KMH * 1000 / 3600  # → 3.889 m/s

# ── Time thresholds ────────────────────────────────────────────────────────────
# 5 / 10 / 15 minutes are the standard catchment thresholds in transit planning
# literature (Gutiérrez & García-Palomares 2009).
TIME_THRESHOLDS_MIN = [5, 10, 15]

# ── Coordinate Reference Systems ───────────────────────────────────────────────
CRS_METRIC = "EPSG:32638"     # UTM Zone 38N — metric CRS for Tashkent (~1 m accuracy)
CRS_WGS84  = "EPSG:4326"      # Geographic WGS84 for GeoJSON output

# ── OpenStreetMap ──────────────────────────────────────────────────────────────
OSM_PLACE  = "Tashkent, Uzbekistan"
# Network types passed to osmnx.graph_from_place()
WALK_NETWORK_TYPE = "walk"
BIKE_NETWORK_TYPE = "bike"

# ── PRD sampling ──────────────────────────────────────────────────────────────
# Number of random OD pairs sampled per station for Pedestrian Route Directness.
# 50 samples gives a stable mean in urban grid networks.
# Method follows Stangl (2012): random destinations within a buffer, mean directness ratio.
PRD_SAMPLE_N = 50
# Euclidean buffer radius for candidate OD point sampling (metres)
PRD_BUFFER_M = 800

# ── File paths ─────────────────────────────────────────────────────────────────
import os
BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR       = os.path.join(BASE_DIR, "data")
CACHE_DIR      = os.path.join(BASE_DIR, ".cache")
WALK_GRAPHML   = os.path.join(CACHE_DIR, "walk_network.graphml")
BIKE_GRAPHML   = os.path.join(CACHE_DIR, "bike_network.graphml")
WORLDPOP_TIFF  = os.path.join(CACHE_DIR, "worldpop_uzb_2020_100m.tif")

# ── WorldPop ───────────────────────────────────────────────────────────────────
# WorldPop UZB 2020, 100m constrained individual countries.
# Citation: WorldPop (www.worldpop.org), University of Southampton, 2020.
# DOI: 10.5258/SOTON/WP00645
WORLDPOP_URL = (
    "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/"
    "2020/BSGM/UZB/uzb_ppp_2020_UNadj_constrained.tif"
)

# ── Alpha-shape ────────────────────────────────────────────────────────────────
# Alpha value for alpha-shape isochrone polygon generation.
# Smaller → tighter polygon; larger → convex hull.
ALPHA_SHAPE_ALPHA = 600  # metres (used as 1/alpha in alphashape library units)
