/**
 * LayerControl — Walk/Bike mode toggle, time threshold selector, opacity slider.
 */

import React from 'react';
import { THRESHOLDS, WALK_COLORS, BIKE_COLORS, MARKER_COLOR_OPTIONS, metricScaleColors, LINE_COLORS } from '../constants';

const styles = {
  panel: {
    background: 'white',
    borderRadius: 8,
    boxShadow: '0 2px 8px rgba(0,0,0,0.18)',
    padding: '14px 16px',
    minWidth: 220,
    fontFamily: 'system-ui, sans-serif',
    fontSize: 14,
  },
  title: { fontWeight: 700, marginBottom: 10, fontSize: 13, color: '#444', textTransform: 'uppercase', letterSpacing: '0.05em' },
  section: { marginBottom: 12 },
  label: { display: 'block', fontWeight: 600, marginBottom: 6, color: '#555' },
  modeGroup: { display: 'flex', gap: 6 },
  modeBtn: (active, color) => ({
    flex: 1,
    padding: '5px 0',
    borderRadius: 5,
    border: `2px solid ${color}`,
    background: active ? color : 'white',
    color: active ? 'white' : color,
    fontWeight: 600,
    cursor: 'pointer',
    fontSize: 13,
    transition: 'all 0.15s',
  }),
  thresholdGroup: { display: 'flex', gap: 6 },
  thresholdBtn: (active, color) => ({
    flex: 1,
    padding: '5px 0',
    borderRadius: 5,
    border: `2px solid ${color}`,
    background: active ? color : 'white',
    color: active ? 'white' : '#333',
    fontWeight: 600,
    cursor: 'pointer',
    fontSize: 12,
    transition: 'all 0.15s',
  }),
  sliderWrap: { display: 'flex', alignItems: 'center', gap: 8 },
  slider: { flex: 1, accentColor: '#1565C0' },
  sliderVal: { minWidth: 34, textAlign: 'right', color: '#555', fontWeight: 600 },
  legend: { display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 },
  legendRow: { display: 'flex', alignItems: 'center', gap: 8 },
  swatch: (color) => ({
    width: 18, height: 12, borderRadius: 3,
    background: color, border: '1px solid rgba(0,0,0,0.15)',
    flexShrink: 0,
  }),
  select: {
    width: '100%', padding: '5px 6px', borderRadius: 5,
    border: '1px solid #ddd', fontSize: 13, background: 'white',
    cursor: 'pointer',
  },
  gradientBar: (low, high) => ({
    height: 10, borderRadius: 3,
    background: `linear-gradient(to right, ${low}, ${high})`,
    border: '1px solid rgba(0,0,0,0.1)',
    marginTop: 4,
  }),
  gradientLabels: {
    display: 'flex', justifyContent: 'space-between',
    fontSize: 10, color: '#777', marginTop: 2,
  },
  lineLegend: { display: 'flex', flexDirection: 'column', gap: 3, marginTop: 4 },
  lineLegendRow: { display: 'flex', alignItems: 'center', gap: 6 },
  lineDot: (color) => ({
    width: 10, height: 10, borderRadius: '50%',
    background: color, flexShrink: 0,
  }),
};

const MODE_COLORS_UI = { walk: '#0288D1', bike: '#FB8C00' };

const LINE_LEGEND = [
  { line: "Chilonzor Line",     label: "Chilonzor" },
  { line: "O'zbekiston Line",   label: "O'zbekiston" },
  { line: "Yunusobod Line",     label: "Yunusobod" },
  { line: "Ring Line (Yellow)", label: "Ring (Yellow)" },
];

const METRIC_LABELS = {
  walk_pop_10: { low: 'Low pop', high: 'High pop' },
  prd_walk:    { low: 'Circuitous', high: 'Direct' },
};

export default function LayerControl({
  mode, setMode, threshold, setThreshold, opacity, setOpacity,
  markerColorBy, setMarkerColorBy, metricRange,
}) {
  const colors = mode === 'walk' ? WALK_COLORS : BIKE_COLORS;

  const scaleColors = markerColorBy !== 'line'
    ? metricScaleColors(markerColorBy)
    : null;

  const metricLabels = METRIC_LABELS[markerColorBy];

  return (
    <div style={styles.panel}>
      <div style={styles.title}>Layer Controls</div>

      {/* Mode selector */}
      <div style={styles.section}>
        <span style={styles.label}>Mode</span>
        <div style={styles.modeGroup}>
          {['walk', 'bike'].map(m => (
            <button
              key={m}
              style={styles.modeBtn(mode === m, MODE_COLORS_UI[m])}
              onClick={() => setMode(m)}
            >
              {m === 'walk' ? '🚶 Walk' : '🚲 Bike'}
            </button>
          ))}
        </div>
      </div>

      {/* Time threshold */}
      <div style={styles.section}>
        <span style={styles.label}>Time threshold</span>
        <div style={styles.thresholdGroup}>
          {THRESHOLDS.map(t => (
            <button
              key={t}
              style={styles.thresholdBtn(threshold === t, colors[t])}
              onClick={() => setThreshold(t)}
            >
              {t} min
            </button>
          ))}
        </div>
      </div>

      {/* Opacity slider */}
      <div style={styles.section}>
        <span style={styles.label}>Isochrone opacity</span>
        <div style={styles.sliderWrap}>
          <input
            type="range" min={0.05} max={0.7} step={0.05}
            value={opacity}
            onChange={e => setOpacity(Number(e.target.value))}
            style={styles.slider}
          />
          <span style={styles.sliderVal}>{Math.round(opacity * 100)}%</span>
        </div>
      </div>

      {/* Marker color */}
      <div style={styles.section}>
        <span style={styles.label}>Color markers by</span>
        <select
          style={styles.select}
          value={markerColorBy}
          onChange={e => setMarkerColorBy(e.target.value)}
        >
          {MARKER_COLOR_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>

        {/* Legend for line coloring */}
        {markerColorBy === 'line' && (
          <div style={styles.lineLegend}>
            {LINE_LEGEND.map(({ line, label }) => (
              <div key={line} style={styles.lineLegendRow}>
                <div style={styles.lineDot(LINE_COLORS[line])} />
                <span style={{ fontSize: 11, color: '#555' }}>{label}</span>
              </div>
            ))}
          </div>
        )}

        {/* Gradient legend for metric coloring */}
        {scaleColors && metricLabels && (
          <>
            <div style={styles.gradientBar(scaleColors.low, scaleColors.high)} />
            <div style={styles.gradientLabels}>
              <span>{metricLabels.low}</span>
              <span>{metricLabels.high}</span>
            </div>
          </>
        )}
      </div>

      {/* Isochrone legend */}
      <div style={styles.section}>
        <span style={styles.label}>Isochrone legend</span>
        <div style={styles.legend}>
          {THRESHOLDS.map(t => (
            <div key={t} style={styles.legendRow}>
              <div style={styles.swatch(colors[t])} />
              <span>{t} min {mode} catchment</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
