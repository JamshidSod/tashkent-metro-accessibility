# Tashkent Metro Accessibility

Reproducible research pipeline for evaluating **pedestrian and cyclist accessibility** to all 49 Tashkent Metro stations across four lines. Produces GeoJSON/CSV data outputs, publication-ready static maps, and an interactive web map.

---

## Station Coverage

**49 verified stations** across four metro lines (source: `tashkent_metro_stations.csv`):

| Line | Stations | Colour |
|---|---|---|
| Chilonzor Line | 15 | Blue `#1565C0` |
| O'zbekiston Line | 11 | Red `#C62828` |
| Yunusobod Line | 8 | Green `#2E7D32` |
| Ring Line (Yellow) | 14 | Amber `#F9A825` |
| Other (Paxtakor) | 1 | Gray `#757575` |

Station IDs follow `CSV_00`–`CSV_48`. Fourteen non-metro OSM nodes (freight stations, tram stops, etc.) were identified and excluded during data cleaning.

---

## Methodology

**Core method: Network Isochrone / Pedestrian Catchment Area (PCA)**

Isochrones are computed using the ego-graph method on OpenStreetMap street networks:
1. For each station, find the nearest network node.
2. Build a subgraph reachable within `speed × time` metres via Dijkstra shortest path.
3. Generate a polygon (alpha-shape or convex hull) from the subgraph node coordinates.
4. Intersect with WorldPop population raster to estimate catchment population.

**Key parameters:**

| Parameter | Value | Reference |
|---|---|---|
| Walk speed | 5 km/h (1.39 m/s) | Standard in literature |
| Cycle speed | 14 km/h (3.89 m/s) | Brons et al. 2009 |
| Time thresholds | 5, 10, 15 min | Standard transit planning |
| Isochrone method | Ego-graph on OSM network | OSMnx / NetworkX |
| Population source | WorldPop UZB 2020 100 m constrained | WorldPop.org |
| Metric CRS | EPSG:32638 (UTM 38N) | Appropriate for Tashkent |
| PRD samples | 50 random OD pairs | Stangl 2012 |

### Important note on population reporting

Per-station populations (`walk_pop_*`, `bike_pop_*` in `metrics.csv`) are individually correct and should be used for **station-level analysis**. However, simply summing them across all 49 stations double-counts residents who fall within the catchment of multiple stations.

At the 15-minute cycling threshold, catchments average ~21.6 km² each and overlap heavily, causing a **3.31× overcount** (naïve sum: 5.55 M vs. true unique residents: 1.68 M).

For **network-level city-wide totals**, use `data/network_coverage.csv`, which reports the exact unique population derived from the WorldPop raster masked to the dissolved union of all station catchments for each mode × threshold combination.

**Correct city-wide coverage figures:**

| Mode | Threshold | Unique residents | Share of city (~3 M) |
|---|---|---|---|
| Walk | 5 min | 61,862 | 2 % |
| Walk | 10 min | 281,360 | 9 % |
| Walk | 15 min | 558,512 | 19 % |
| Bike | 5 min | 349,710 | 12 % |
| Bike | 10 min | 1,043,447 | 35 % |
| Bike | 15 min | 1,678,636 | 56 % |

**References:**
- Gutiérrez, J. & García-Palomares, J.C. (2009). New spatial approaches to the study of public transport accessibility. *Transport Policy*, 16(6), 342–348.
- Brons, M., Givoni, M., & Rietveld, P. (2009). Access to railway stations and its potential in increasing rail use. *Transportation Research Part A*, 43(2), 136–144.
- Stangl, P. (2012). The pedestrian route directness test: A new level-of-service model. *Urban Design International*, 17(3), 228–238. DOI: 10.1057/udi.2012.14
- Boeing, G. (2017). OSMnx: New methods for acquiring, constructing, analyzing, and visualizing complex street networks. *Computers, Environment and Urban Systems*, 65, 126–139.

---

## Data Provenance

| Dataset | Source | Version / Date |
|---|---|---|
| Street networks | OpenStreetMap via OSMnx | See `data/run_info.txt` |
| Station list | `tashkent_metro_stations.csv` (manually verified) | 2024–2025 |
| Population | WorldPop UZB 2020 100 m constrained UN-adjusted | [DOI: 10.5258/SOTON/WP00645](https://doi.org/10.5258/SOTON/WP00645) |

The OSM download timestamp is embedded in the `.graphml` cache files and written to `data/run_info.txt` by `run_all.py`.

---

## Project Structure

```
tashkent-metro-accessibility/
├── analysis/                    # Python reproducible analysis pipeline
│   ├── config.py                # All parameters (speeds, CRS, thresholds)
│   ├── stations.py              # Station loader: CSV primary, OSM fallback
│   ├── network.py               # OSMnx network download + cache
│   ├── isochrones.py            # Ego-graph isochrone computation
│   ├── population.py            # WorldPop download + zonal statistics
│   ├── metrics.py               # PRD + aggregate metrics table
│   ├── export.py                # Write GeoJSON + CSV outputs
│   ├── run_all.py               # Single entry point: full pipeline
│   └── make_static_maps.py      # Publication-ready PNG isochrone maps
├── data/                        # Generated outputs (committed to repo)
│   ├── stations.geojson         # 49 stations with line assignments
│   ├── isochrones_walk.geojson  # 147 walking catchment polygons (49 × 3)
│   ├── isochrones_bike.geojson  # 147 cycling catchment polygons (49 × 3)
│   ├── metrics.csv              # Per-station metrics (one row per station)
│   ├── network_coverage.csv     # Network-level unique population (no double-count)
│   ├── line_summary.csv         # Aggregated stats by metro line
│   ├── equity.csv               # Equity/PRD analysis outputs
│   ├── sensitivity.csv          # Sensitivity analysis results
│   └── run_info.txt             # OSM timestamps, run metadata
├── Output/                      # Static PNG maps
│   ├── isochrone_walk_5min.png
│   ├── isochrone_walk_10min.png
│   ├── isochrone_walk_15min.png
│   ├── isochrone_bike_5min.png
│   ├── isochrone_bike_10min.png
│   └── isochrone_bike_15min.png
├── web/                         # React + Leaflet interactive frontend
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   └── hooks/
│   ├── public/data/             # Symlink or copy of ../data/
│   └── package.json
├── tashkent_metro_stations.csv  # Authoritative station list (49 stations)
├── .cache/                      # OSM graphml + WorldPop raster (not committed)
├── requirements.txt
└── README.md
```

---

## Reproduction Instructions

### Prerequisites

- Python 3.10+ with pip
- Node.js 18+ with npm (for the web app only)
- ~200 MB disk space for OSM graphs and WorldPop raster

### Step 1 — Install Python dependencies

```bash
pip install -r requirements.txt
```

On macOS, GDAL bindings may require:
```bash
brew install gdal
```

### Step 2 — Run the analysis pipeline

```bash
python analysis/run_all.py
```

This will:
1. Load station data from `tashkent_metro_stations.csv` (falls back to OSM if missing)
2. Download and cache OSM walk + bike networks
3. Compute isochrone polygons for all 49 stations × 2 modes × 3 thresholds = 294 polygons
4. Download WorldPop raster and compute per-station zonal population statistics
5. Compute Pedestrian Route Directness (PRD) for all stations
6. Write output files to `data/`

To force re-download of cached OSM graphs:
```bash
python analysis/run_all.py --force-download
```

### Step 3 — Generate static PNG maps

```bash
python analysis/make_static_maps.py
```

Produces 6 publication-ready PNG images in `Output/` (one per mode × threshold):

| File | Description |
|---|---|
| `isochrone_walk_5min.png` | 5-minute walking catchment zones |
| `isochrone_walk_10min.png` | 10-minute walking catchment zones |
| `isochrone_walk_15min.png` | 15-minute walking catchment zones |
| `isochrone_bike_5min.png` | 5-minute cycling catchment zones |
| `isochrone_bike_10min.png` | 10-minute cycling catchment zones |
| `isochrone_bike_15min.png` | 15-minute cycling catchment zones |

Each map includes:
- **Basemap:** Esri WorldGrayCanvas (neutral gray, no API key required)
- **Isochrone polygons:** Semi-transparent, color-coded by mode (blue = walk, green = bike)
- **Metro lines:** Correctly ordered continuous paths using nearest-neighbour routing; Ring Line drawn as an open arc matching the actual network geometry
- **Station dots and labels:** Color-coded by line
- **Legend** and source attribution

### Step 4 — Link data to the web app

```bash
# Option A: symlink (recommended on macOS/Linux)
ln -sf ../../data web/public/data

# Option B: copy
cp -r data/ web/public/data/
```

### Step 5 — Run the web app

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

For production deployment (e.g. GitHub Pages):
```bash
cd web
npm run build
# Deploy the dist/ directory
```

### Step 6 — Verify outputs

```bash
# Check data files
ls -lh data/

# Inspect per-station metrics (49 rows)
python -c "import pandas as pd; df=pd.read_csv('data/metrics.csv'); print(df[['station_id','name_uz','line','walk_area_10','bike_pop_15']].to_string())"

# Inspect network-level unique population
python -c "import pandas as pd; print(pd.read_csv('data/network_coverage.csv').to_string())"

# Check OSM timestamps
cat data/run_info.txt
```

---

## Outputs

### `data/stations.geojson`
GeoJSON FeatureCollection of all 49 metro stations.
Properties: `station_id`, `name_uz`, `name_ru`, `line`.

### `data/isochrones_walk.geojson` / `data/isochrones_bike.geojson`
GeoJSON FeatureCollection of catchment polygons (147 features each: 49 stations × 3 thresholds).
Properties: `station_id`, `mode`, `minutes`, `area_km2`, `population`.

### `data/metrics.csv`
Wide-format table, one row per station (49 rows).

| Column | Description |
|---|---|
| `station_id`, `name_uz`, `name_ru`, `line`, `lon`, `lat` | Station identifiers |
| `walk_area_5/10/15` | Walking catchment area (km²) at each threshold |
| `walk_pop_5/10/15` | Population within walking catchment |
| `bike_area_5/10/15` | Cycling catchment area (km²) at each threshold |
| `bike_pop_5/10/15` | Population within cycling catchment |
| `prd_walk`, `prd_bike` | Pedestrian/Cyclist Route Directness score |

> **Note:** `*_pop_*` columns are per-station values and are correct for station-level analysis. Do not sum them across stations for city-wide totals — use `network_coverage.csv` instead.

### `data/network_coverage.csv`
Network-level coverage statistics for each mode × threshold combination (6 rows).
Unique population is computed from the WorldPop raster masked to the dissolved union of all station catchments, eliminating double-counting of residents served by multiple stations.

| Column | Description |
|---|---|
| `mode`, `minutes` | Mode (walk/bike) and time threshold |
| `n_stations` | Number of stations (49) |
| `mean_area_km2`, `sd_area_km2` | Per-station catchment area mean and SD |
| `mean_pop_per_station`, `sd_pop_per_station` | Per-station population mean and SD |
| `sum_pop_stations` | Naïve sum across stations (double-counts overlap — do not use for city totals) |
| `sum_area_km2` | Naïve sum of per-station areas |
| `network_union_area_km2` | Area of dissolved union of all catchments (unique coverage) |
| `network_unique_pop` | **Correct city-wide unique population** (no double-counting) |
| `overcount_factor` | `sum_pop_stations / network_unique_pop` |

---

## Web App

The frontend is a static React + Leaflet application — no backend, no API keys required.

- **Base map:** OpenStreetMap tiles
- **Isochrone layers:** Semi-transparent polygons, toggled by mode (walk/bike) and threshold (5/10/15 min)
- **Station markers:** Colored by metro line
- **Sidebar:** Per-station metrics and PRD score
- **Metrics table:** Sortable table of all 49 stations
- **Export panel:** Download GeoJSON and CSV files

---

## License

Analysis code: MIT.
Data: OSM data © OpenStreetMap contributors (ODbL). WorldPop © University of Southampton (CC BY 4.0).
