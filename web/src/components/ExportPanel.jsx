/**
 * ExportPanel — download buttons for all data outputs.
 */

import React from 'react';
import { DATA_PATHS } from '../constants';

const EXPORTS = [
  { label: 'stations.geojson',        path: DATA_PATHS.stations,       icon: '📍' },
  { label: 'isochrones_walk.geojson', path: DATA_PATHS.isochronesWalk, icon: '🚶' },
  { label: 'isochrones_bike.geojson', path: DATA_PATHS.isochronesBike, icon: '🚲' },
  { label: 'metrics.csv',             path: DATA_PATHS.metrics,         icon: '📊' },
];

const styles = {
  panel: {
    background: 'white',
    borderRadius: 8,
    boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
    padding: '14px 16px',
    fontFamily: 'system-ui, sans-serif',
    fontSize: 13,
    minWidth: 200,
  },
  title: {
    fontWeight: 700, fontSize: 11, textTransform: 'uppercase',
    letterSpacing: '0.06em', color: '#888', marginBottom: 10,
  },
  list: { display: 'flex', flexDirection: 'column', gap: 6 },
  btn: {
    display: 'flex', alignItems: 'center', gap: 8,
    background: '#F5F5F5', border: '1px solid #E0E0E0',
    borderRadius: 6, padding: '7px 10px',
    color: '#1565C0', fontWeight: 600, cursor: 'pointer',
    textDecoration: 'none', fontSize: 12,
    transition: 'background 0.15s',
  },
};

export default function ExportPanel() {
  return (
    <div style={styles.panel}>
      <div style={styles.title}>Download Data</div>
      <div style={styles.list}>
        {EXPORTS.map(({ label, path, icon }) => (
          <a
            key={label}
            href={path}
            download={label}
            style={styles.btn}
            onMouseOver={e => e.currentTarget.style.background = '#E3F2FD'}
            onMouseOut={e  => e.currentTarget.style.background = '#F5F5F5'}
          >
            <span>{icon}</span>
            <span>{label}</span>
          </a>
        ))}
      </div>
    </div>
  );
}
