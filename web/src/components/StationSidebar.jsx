/**
 * StationSidebar — per-station accessibility metrics panel.
 *
 * Shows: name, metro line badge, catchment area table, population reached,
 * and Pedestrian Route Directness with qualitative label.
 */

import React from 'react';
import { LINE_COLORS, LINE_NAMES, THRESHOLDS, prdLabel, prdColor } from '../constants';

const styles = {
  sidebar: {
    background: 'white',
    borderRadius: 8,
    boxShadow: '0 2px 8px rgba(0,0,0,0.18)',
    padding: '16px',
    fontFamily: 'system-ui, sans-serif',
    fontSize: 13,
    maxWidth: 300,
    minWidth: 260,
  },
  header: { marginBottom: 12 },
  nameUz: { fontWeight: 700, fontSize: 16, color: '#1a1a1a', lineHeight: 1.2 },
  nameRu: { color: '#666', fontSize: 13, marginTop: 2 },
  badge: (line) => ({
    display: 'inline-block',
    background: LINE_COLORS[line] ?? '#757575',
    color: 'white',
    borderRadius: 4,
    padding: '2px 8px',
    fontSize: 11,
    fontWeight: 700,
    marginTop: 6,
    letterSpacing: '0.03em',
  }),
  section: { marginTop: 14 },
  sectionTitle: {
    fontWeight: 700, fontSize: 11, textTransform: 'uppercase',
    letterSpacing: '0.06em', color: '#888', marginBottom: 6,
  },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 12 },
  th: {
    textAlign: 'right', fontWeight: 600, color: '#555',
    padding: '3px 6px', borderBottom: '1px solid #eee',
  },
  thLeft: {
    textAlign: 'left', fontWeight: 600, color: '#555',
    padding: '3px 6px', borderBottom: '1px solid #eee',
  },
  td: { textAlign: 'right', padding: '4px 6px', color: '#222' },
  tdLeft: { textAlign: 'left', padding: '4px 6px', color: '#222' },
  rdiWrap: { display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 },
  rdiVal: { fontWeight: 700, fontSize: 18, color: '#222' },
  rdiLabel: (color) => ({
    display: 'inline-block', background: color, color: 'white',
    borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 700,
  }),
  rdiNote: { color: '#888', fontSize: 11, marginTop: 4 },
  placeholder: { color: '#aaa', fontStyle: 'italic', textAlign: 'center', paddingTop: 30 },
};

function fmt(val, decimals = 2) {
  if (val === null || val === undefined) return '—';
  return typeof val === 'number' ? val.toFixed(decimals) : val;
}

function fmtPop(val) {
  if (val === null || val === undefined) return '—';
  return Number(val).toLocaleString();
}

export default function StationSidebar({ station, metrics }) {
  if (!station) {
    return (
      <div style={styles.sidebar}>
        <div style={styles.placeholder}>
          Click a station<br />to view metrics
        </div>
      </div>
    );
  }

  const p  = station.properties ?? {};
  const m  = metrics ?? {};
  const line = p.line ?? 'unknown';

  return (
    <div style={styles.sidebar}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.nameUz}>{p.name_uz ?? 'Unknown Station'}</div>
        <div style={styles.nameRu}>{p.name_ru}</div>
        <span style={styles.badge(line)}>
          {LINE_NAMES[line] ?? line}
        </span>
      </div>

      {/* Catchment Area */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Catchment Area (km²)</div>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.thLeft}>Mode</th>
              {THRESHOLDS.map(t => (
                <th key={t} style={styles.th}>{t} min</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {['walk', 'bike'].map(mode => (
              <tr key={mode}>
                <td style={styles.tdLeft}>{mode === 'walk' ? '🚶 Walk' : '🚲 Bike'}</td>
                {THRESHOLDS.map(t => (
                  <td key={t} style={styles.td}>
                    {fmt(m[`${mode}_area_${t}`])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Population */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Population Reached</div>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.thLeft}>Mode</th>
              {THRESHOLDS.map(t => (
                <th key={t} style={styles.th}>{t} min</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {['walk', 'bike'].map(mode => (
              <tr key={mode}>
                <td style={styles.tdLeft}>{mode === 'walk' ? '🚶 Walk' : '🚲 Bike'}</td>
                {THRESHOLDS.map(t => (
                  <td key={t} style={styles.td}>
                    {fmtPop(m[`${mode}_pop_${t}`])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* PRD */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Route Directness (PRD)</div>
        {['walk', 'bike'].map(mode => {
          const prd   = m[`prd_${mode}`];
          const label = prdLabel(prd);
          const color = prdColor(prd);
          return (
            <div key={mode} style={{ marginBottom: 8 }}>
              <span style={{ color: '#555', fontWeight: 600 }}>
                {mode === 'walk' ? '🚶 Walk' : '🚲 Bike'}:&nbsp;
              </span>
              <div style={styles.rdiWrap}>
                <span style={styles.rdiVal}>{prd !== null && prd !== undefined ? prd.toFixed(3) : '—'}</span>
                <span style={styles.rdiLabel(color)}>{label}</span>
              </div>
            </div>
          );
        })}
        <div style={styles.rdiNote}>
          PRD = mean(Euclidean / Network distance) ∈ (0,1]. Higher → straighter paths.
          <br />Stangl (2012). Urban Design International, 17(3). DOI: 10.1057/udi.2012.14
        </div>
      </div>
    </div>
  );
}
