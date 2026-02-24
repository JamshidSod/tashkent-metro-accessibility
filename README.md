# Tashkent Metro Accessibility

Interactive research tool for evaluating **pedestrian and cyclist accessibility** to Tashkent Metro stations. Designed to support reproducible analysis for academic publication.

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
| Population source | WorldPop UZB 100m grid | WorldPop.org |
| Metric CRS | EPSG:32638 (UTM 38N) | Appropriate for Tashkent |
| PRD samples | 50 random OD pairs | Stangl 2012 |

**References:**
- Gutiérrez, J. & García-Palomares, J.C. (2009). New spatial approaches to the study of public transport accessibility. *Transport Policy*, 16(6), 342–348.
- Brons, M., Givoni, M., & Rietveld, P. (2009). Access to railway stations and its potential in increasing rail use. *Transportation Research Part A*, 43(2), 136–144.
- Stangl, P. (2012). The pedestrian route directness test: A new level-of-service model. *Urban Design International*, 17(3), 228–238. DOI: 10.1057/udi.2012.14
- Boeing, G. (2017). OSMnx: New methods for acquiring, constructing, analyzing, and visualizing complex street networks. *Computers, Environment and Urban Systems*, 65, 126–139.

---

## Data Provenance

| Dataset | Source | Version | Date |
|---|---|---|---|
| Street networks | OpenStreetMap via OSMnx | See `data/run_info.txt` | Recorded at runtime |
| Station data | OpenStreetMap (fallback: hardcoded) | See `stations.py` | — |
| Population | WorldPop UZB 2020 100m constrained | 2020 UN-adjusted | [DOI: 10.5258/SOTON/WP00645](https://doi.org/10.5258/SOTON/WP00645) |

The OSM download timestamp is embedded in the `.graphml` cache files and written to `data/run_info.txt` by `run_all.py`.

---

## Project Structure

```
tashkent-metro-accessibility/
├── analysis/           # Python reproducible analysis pipeline
│   ├── config.py       # All parameters (speeds, CRS, thresholds)
│   ├── stations.py     # Station data from OSM / fallback hardcoded
│   ├── network.py      # OSMnx network download + cache
│   ├── isochrones.py   # Ego-graph isochrone computation
│   ├── population.py   # WorldPop download + zonal statistics
│   ├── metrics.py      # PRD + aggregate metrics table
│   ├── export.py       # Write GeoJSON + CSV outputs
│   ├── run_all.py      # Single entry point: full pipeline
│   └── make_static_maps.py  # Generate static PNG isochrone maps
├── data/               # Generated outputs (committed to repo)
│   ├── stations.geojson
│   ├── isochrones_walk.geojson
│   ├── isochrones_bike.geojson
│   ├── metrics.csv
│   └── run_info.txt    # OSM timestamps, run metadata
├── Output/             # Static PNG maps (6 images: walk/bike × 5/10/15 min)
├── web/                # React + Leaflet frontend
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   └── hooks/
│   ├── public/data/    # Symlink or copy of ../data/
│   └── package.json
├── .cache/             # Cached OSM graphml + WorldPop raster (not committed)
├── requirements.txt
└── README.md
```

---

## Reproduction Instructions

### Prerequisites

- Python 3.10+ with pip
- Node.js 18+ with npm (for the web app)
- ~500 MB disk space for OSM graphs and WorldPop raster

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
1. Load station data from OSM (or fall back to hardcoded data)
2. Download and cache OSM walk + bike networks (~100–200 MB)
3. Compute isochrone polygons for all stations × modes × thresholds
4. Download WorldPop raster (~50 MB) and compute zonal population statistics
5. Compute Pedestrian Route Directness (PRD) for all stations
6. Write 4 output files to `data/`

To force re-download of cached OSM graphs:
```bash
python analysis/run_all.py --force-download
```

### Step 3 — Link data to the web app

```bash
# Option A: symlink (recommended on macOS/Linux)
ln -sf ../../data web/public/data

# Option B: copy
cp -r data/ web/public/data/
```

### Step 4 — Run the web app

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### Step 5 — Verify outputs

```bash
# Check all 4 output files exist
ls -lh data/

# Inspect metrics (should have ~29 rows, no empty key columns)
python -c "import pandas as pd; df=pd.read_csv('data/metrics.csv'); print(df[['station_id','name_uz','walk_area_10','prd_walk']].to_string())"

# Check OSM timestamps
cat data/run_info.txt
```

---

## Outputs

### `data/stations.geojson`
GeoJSON FeatureCollection of all metro stations.
Properties: `station_id`, `name_uz`, `name_ru`, `line`, `lon`, `lat`.

### `data/isochrones_walk.geojson` / `data/isochrones_bike.geojson`
GeoJSON FeatureCollection of catchment polygons.
Properties: `station_id`, `mode`, `minutes`, `area_km2`, `population`.

### `data/metrics.csv`
Wide-format table, one row per station.
Columns: `station_id`, `name_uz`, `name_ru`, `line`, `lon`, `lat`,
`walk_area_5`, `walk_area_10`, `walk_area_15`,
`walk_pop_5`, `walk_pop_10`, `walk_pop_15`,
`bike_area_5`, `bike_area_10`, `bike_area_15`,
`bike_pop_5`, `bike_pop_10`, `bike_pop_15`,
`prd_walk`, `prd_bike`.

---

## Web App

The frontend is a static React + Leaflet application with no backend and no API keys required.

- **Base map:** OpenStreetMap tiles
- **Isochrone layers:** Semi-transparent polygons, toggled by mode (walk/bike) and time threshold (5/10/15 min)
- **Station markers:** Colored by metro line (Chilonzor=blue, O'zbekiston=red, Yunusobod=green, Ring=amber)
- **Sidebar:** Per-station metrics, PRD score with qualitative label
- **Metrics table:** Sortable table of all stations
- **Export panel:** Download GeoJSON and CSV files

### Step 6 — Generate static PNG maps (optional)

```bash
python analysis/make_static_maps.py
```

Produces 6 publication-ready PNG images in `Output/`:

| File | Description |
|---|---|
| `isochrone_walk_5min.png` | 5-minute walking catchment |
| `isochrone_walk_10min.png` | 10-minute walking catchment |
| `isochrone_walk_15min.png` | 15-minute walking catchment |
| `isochrone_bike_5min.png` | 5-minute cycling catchment |
| `isochrone_bike_10min.png` | 10-minute cycling catchment |
| `isochrone_bike_15min.png` | 15-minute cycling catchment |

Each map includes a CartoDB Positron basemap, isochrone polygons, metro lines (correctly ordered and color-coded), station labels, and a summary statistics panel.

---

For production deployment (e.g. GitHub Pages):
```bash
cd web
npm run build
# Deploy dist/ directory
```

---

## License

Analysis code: MIT.
Data: OSM data © OpenStreetMap contributors (ODbL). WorldPop © University of Southampton (CC BY 4.0).
