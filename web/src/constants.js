/**
 * Visual constants, layer styles, and label definitions.
 *
 * Color palette chosen for accessibility (WCAG AA contrast on light maps)
 * and colorblind-friendliness (blue/red/green combination tested against
 * Deuteranopia and Protanopia simulators).
 */

// ── Metro line colors ──────────────────────────────────────────────────────────
export const LINE_COLORS = {
  'Chilonzor Line':     '#1565C0', // blue
  "O'zbekiston Line":   '#C62828', // red
  'Yunusobod Line':     '#2E7D32', // green
  'Ring Line (Yellow)': '#F9A825', // amber
  'Other':              '#757575', // gray
  unknown:              '#757575', // fallback
};

export const LINE_NAMES = {
  'Chilonzor Line':     'Chilonzor Line',
  "O'zbekiston Line":   "O'zbekiston Line",
  'Yunusobod Line':     'Yunusobod Line',
  'Ring Line (Yellow)': 'Ring Line (Yellow)',
  'Other':              'Other',
};

// ── Isochrone time-threshold colors ───────────────────────────────────────────
// Light → dark: 5 min → 15 min
export const THRESHOLD_COLORS = {
  5:  '#A5D6A7', // light green
  10: '#43A047', // medium green
  15: '#1B5E20', // dark green
};

// Walk-mode uses blue-green spectrum, bike-mode uses orange spectrum
export const WALK_COLORS = {
  5:  '#B3E5FC',
  10: '#0288D1',
  15: '#01579B',
};

export const BIKE_COLORS = {
  5:  '#FFE0B2',
  10: '#FB8C00',
  15: '#E65100',
};

export const MODE_COLORS = {
  walk: WALK_COLORS,
  bike: BIKE_COLORS,
};

// ── Isochrone polygon style factory ───────────────────────────────────────────
export function isochroneStyle(mode, minutes, opacity = 0.35) {
  const colors = MODE_COLORS[mode] ?? WALK_COLORS;
  const color  = colors[minutes] ?? '#90A4AE';
  return {
    fillColor:   color,
    fillOpacity: opacity,
    color:       color,
    weight:      1.5,
    opacity:     0.7,
  };
}

// ── Station marker style ───────────────────────────────────────────────────────
export function stationStyle(line, selected = false) {
  return {
    radius:      selected ? 10 : 7,
    fillColor:   LINE_COLORS[line] ?? LINE_COLORS.unknown,
    fillOpacity: 0.9,
    color:       selected ? '#FFFFFF' : '#FFFFFF',
    weight:      selected ? 3 : 1.5,
    opacity:     1,
  };
}

// ── PRD label thresholds ──────────────────────────────────────────────────────
// Pedestrian Route Directness: PRD = mean(Euclidean / Network distance) ∈ (0, 1]
// Thresholds derived from Stangl (2012) benchmarks (inverse convention):
//   ≥ 0.80 → High   (Stangl's PRD ≤ 1.25, well-connected grid)
//   ≥ 0.65 → Medium (Stangl's PRD ≤ 1.54)
//   < 0.65 → Low    (circuitous network)
// Source: Stangl, P. (2012). Urban Design International, 17(3), 228–238.
//         DOI: 10.1057/udi.2012.14
export function prdLabel(prd) {
  if (prd === null || prd === undefined) return 'N/A';
  if (prd >= 0.8)  return 'High';
  if (prd >= 0.65) return 'Medium';
  return 'Low';
}

export function prdColor(prd) {
  const label = prdLabel(prd);
  return { High: '#2E7D32', Medium: '#F57F17', Low: '#C62828', 'N/A': '#9E9E9E' }[label];
}

// ── Marker choropleth color scale ─────────────────────────────────────────────
// Available metrics for marker coloring
export const MARKER_COLOR_OPTIONS = [
  { value: 'line',         label: 'Metro line' },
  { value: 'walk_pop_10',  label: 'Walk pop 10 min' },
  { value: 'prd_walk',     label: 'PRD walk' },
];

function hexToRgb(hex) {
  const n = parseInt(hex.replace('#', ''), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function rgbToHex(r, g, b) {
  return '#' + [r, g, b].map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
}

function lerpColor(hexA, hexB, t) {
  const [r1, g1, b1] = hexToRgb(hexA);
  const [r2, g2, b2] = hexToRgb(hexB);
  return rgbToHex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t);
}

// Color scales per metric
const METRIC_SCALES = {
  walk_pop_10: { low: '#E3F2FD', high: '#0D47A1' },  // light → dark blue
  prd_walk:    { low: '#C62828', high: '#2E7D32' },   // red → green
};

export function metricColor(metric, value, min, max) {
  if (value === null || value === undefined || isNaN(value)) return '#9E9E9E';
  const scale = METRIC_SCALES[metric];
  if (!scale) return '#9E9E9E';
  const t = max > min ? Math.max(0, Math.min(1, (value - min) / (max - min))) : 0.5;
  return lerpColor(scale.low, scale.high, t);
}

export function metricScaleColors(metric) {
  return METRIC_SCALES[metric] ?? { low: '#E0E0E0', high: '#212121' };
}

// ── Map defaults ──────────────────────────────────────────────────────────────
export const MAP_CENTER = [41.2995, 69.2401]; // Tashkent city center
export const MAP_ZOOM   = 12;

// ── Time threshold options ────────────────────────────────────────────────────
export const THRESHOLDS = [5, 10, 15];
export const MODES      = ['walk', 'bike'];

// ── Data file paths (relative to /public/data/) ───────────────────────────────
export const DATA_PATHS = {
  stations:        '/data/stations.geojson',
  isochronesWalk:  '/data/isochrones_walk.geojson',
  isochronesBike:  '/data/isochrones_bike.geojson',
  metrics:         '/data/metrics.csv',
};
