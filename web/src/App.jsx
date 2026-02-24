/**
 * Tashkent Metro Accessibility — Main App
 *
 * Layout:
 *   ┌──────────────────────────────────────────────────────────────────┐
 *   │  Header                                                          │
 *   ├─────────────────────────────────────┬────────────────────────────┤
 *   │  Map (flex: 1)                      │  Right panel               │
 *   │                                     │  ├ LayerControl            │
 *   │                                     │  ├ StationSidebar          │
 *   │                                     │  └ ExportPanel             │
 *   ├──────────────────────────────────────────────────────────────────┤
 *   │  MetricsTable (bottom)                                           │
 *   └──────────────────────────────────────────────────────────────────┘
 */

import React, { useState, useMemo, useCallback } from 'react';
import Map          from './components/Map';
import LayerControl from './components/LayerControl';
import StationSidebar from './components/StationSidebar';
import MetricsTable from './components/MetricsTable';
import ExportPanel  from './components/ExportPanel';
import { useAccessibilityData, buildMetricsMap } from './hooks/useAccessibilityData';

const styles = {
  root: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    background: '#F5F5F5',
  },
  header: {
    background: '#1565C0',
    color: 'white',
    padding: '10px 20px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
    flexShrink: 0,
  },
  headerTitle: { fontWeight: 700, fontSize: 17, letterSpacing: '0.01em' },
  headerSub:   { fontSize: 12, opacity: 0.8, marginTop: 2 },
  body: { display: 'flex', flex: 1, overflow: 'hidden' },
  mapWrap: { flex: 1, position: 'relative' },
  rightPanel: {
    width: 300,
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    padding: 12,
    overflowY: 'auto',
    background: '#EEEEEE',
    flexShrink: 0,
  },
  bottom: {
    maxHeight: 380,
    flexShrink: 0,
    padding: '0 12px 12px',
    background: '#EEEEEE',
  },
  error: {
    position: 'absolute', top: 20, left: '50%', transform: 'translateX(-50%)',
    background: '#FFEBEE', border: '1px solid #EF9A9A', borderRadius: 6,
    padding: '10px 18px', color: '#C62828', fontWeight: 600, zIndex: 1000,
    maxWidth: 400, textAlign: 'center',
  },
  loading: {
    position: 'absolute', inset: 0, display: 'flex',
    alignItems: 'center', justifyContent: 'center',
    background: 'rgba(255,255,255,0.8)', zIndex: 1000,
    fontSize: 16, color: '#1565C0', fontWeight: 600,
  },
};

export default function App() {
  const { stations, isoWalk, isoBike, metrics, loading, error } = useAccessibilityData();

  const [mode,              setMode]             = useState('walk');
  const [threshold,         setThreshold]        = useState(10);
  const [opacity,           setOpacity]          = useState(0.35);
  const [selectedStation,   setSelectedStation]  = useState(null);
  const [markerColorBy,     setMarkerColorBy]    = useState('line');

  const metricsMap = useMemo(() => buildMetricsMap(metrics), [metrics]);

  // Precompute min/max for choropleth scaling
  const metricRange = useMemo(() => {
    if (!metrics || !metrics.length) return {};
    const range = {};
    for (const key of ['walk_pop_10', 'prd_walk']) {
      const vals = metrics.map(m => m[key]).filter(v => v !== null && v !== undefined && !isNaN(v));
      range[key] = { min: Math.min(...vals), max: Math.max(...vals) };
    }
    return range;
  }, [metrics]);

  // Find selected station feature from GeoJSON
  const selectedFeature = useMemo(() => {
    if (!selectedStation || !stations) return null;
    return stations.features?.find(
      f => f.properties.station_id === selectedStation
    ) ?? null;
  }, [selectedStation, stations]);

  const selectedMetrics = selectedStation ? metricsMap[selectedStation] : null;

  function handleSelectStation(feature) {
    if (typeof feature === 'string') {
      // Called from MetricsTable with station_id string
      setSelectedStation(feature);
    } else {
      // Called from Map with GeoJSON feature
      setSelectedStation(feature?.properties?.station_id ?? null);
    }
  }

  return (
    <div style={styles.root}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <div style={styles.headerTitle}>Tashkent Metro Accessibility</div>
          <div style={styles.headerSub}>
            Pedestrian &amp; Cyclist Catchment Analysis · OSMnx + WorldPop · Research Tool
          </div>
        </div>
        <div style={{ fontSize: 12, opacity: 0.75, textAlign: 'right' }}>
          {stations ? `${stations.features?.length ?? 0} stations loaded` : 'Loading…'}
        </div>
      </div>

      {/* Main body */}
      <div style={styles.body}>
        {/* Map */}
        <div style={styles.mapWrap}>
          {loading && (
            <div style={styles.loading}>Loading data…</div>
          )}
          {error && (
            <div style={styles.error}>
              ⚠ Data load error: {error.message}
              <br />
              <small>Run the Python pipeline first to generate data files.</small>
            </div>
          )}
          <Map
            stations={stations}
            isoWalk={isoWalk}
            isoBike={isoBike}
            mode={mode}
            threshold={threshold}
            opacity={opacity}
            selectedStation={selectedFeature}
            onSelectStation={handleSelectStation}
            metricsMap={metricsMap}
            markerColorBy={markerColorBy}
            metricRange={metricRange}
          />
        </div>

        {/* Right panel */}
        <div style={styles.rightPanel}>
          <LayerControl
            mode={mode}               setMode={setMode}
            threshold={threshold}     setThreshold={setThreshold}
            opacity={opacity}         setOpacity={setOpacity}
            markerColorBy={markerColorBy} setMarkerColorBy={setMarkerColorBy}
            metricRange={metricRange}
          />
          <StationSidebar
            station={selectedFeature}
            metrics={selectedMetrics}
          />
          <ExportPanel />
        </div>
      </div>

      {/* Bottom metrics table */}
      <div style={styles.bottom}>
        <MetricsTable
          metrics={metrics}
          selectedId={selectedStation}
          onSelectStation={handleSelectStation}
        />
      </div>
    </div>
  );
}
