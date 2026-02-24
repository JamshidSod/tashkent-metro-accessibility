/**
 * MetricsTable — sortable table of all stations with their accessibility metrics.
 * Highlights the currently selected station row.
 */

import React, { useState, useMemo } from 'react';
import { LINE_COLORS, LINE_NAMES, THRESHOLDS, prdLabel, prdColor } from '../constants';

const styles = {
  wrap: {
    background: 'white',
    borderRadius: 8,
    boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
    overflow: 'hidden',
    fontFamily: 'system-ui, sans-serif',
    fontSize: 12,
  },
  header: {
    padding: '12px 16px',
    borderBottom: '1px solid #e0e0e0',
    fontWeight: 700,
    fontSize: 14,
    color: '#333',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  tableWrap: { overflowX: 'auto', maxHeight: 320 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 11 },
  th: (sorted) => ({
    position: 'sticky', top: 0,
    background: sorted ? '#E3F2FD' : '#F5F5F5',
    padding: '7px 8px',
    textAlign: 'right',
    fontWeight: 700,
    color: '#444',
    cursor: 'pointer',
    borderBottom: '2px solid #ddd',
    userSelect: 'none',
    whiteSpace: 'nowrap',
    fontSize: 10,
  }),
  thLeft: (sorted) => ({
    position: 'sticky', top: 0,
    background: sorted ? '#E3F2FD' : '#F5F5F5',
    padding: '7px 8px',
    textAlign: 'left',
    fontWeight: 700,
    color: '#444',
    cursor: 'pointer',
    borderBottom: '2px solid #ddd',
    userSelect: 'none',
    whiteSpace: 'nowrap',
    fontSize: 10,
  }),
  row: (selected, even) => ({
    background: selected ? '#E3F2FD' : (even ? '#FAFAFA' : 'white'),
    cursor: 'pointer',
    borderBottom: '1px solid #f0f0f0',
  }),
  td: { padding: '5px 8px', textAlign: 'right', color: '#333' },
  tdLeft: { padding: '5px 8px', textAlign: 'left', color: '#333' },
  lineBadge: (line) => ({
    background: LINE_COLORS[line] ?? '#757575',
    color: 'white',
    borderRadius: 3,
    padding: '1px 5px',
    fontSize: 9,
    fontWeight: 700,
  }),
  rdiChip: (color) => ({
    background: color,
    color: 'white',
    borderRadius: 3,
    padding: '1px 5px',
    fontSize: 9,
    fontWeight: 700,
  }),
};

const COLUMNS = [
  { key: 'name_uz',       label: 'Station',         left: true  },
  { key: 'line',          label: 'Line',             left: true  },
  { key: 'walk_area_5',   label: 'Walk 5\u2019 km\u00B2'         },
  { key: 'walk_area_10',  label: 'Walk 10\u2019 km\u00B2'        },
  { key: 'walk_area_15',  label: 'Walk 15\u2019 km\u00B2'        },
  { key: 'bike_area_15',  label: 'Bike 15\u2019 km\u00B2'        },
  { key: 'walk_pop_10',   label: 'Pop @10\u2019 walk'           },
  { key: 'bike_pop_10',   label: 'Pop @10\u2019 bike'           },
  { key: 'prd_walk',      label: 'PRD walk'                      },
  { key: 'prd_bike',      label: 'PRD bike'                      },
];

function SortIcon({ dir }) {
  if (!dir) return <span style={{ color: '#ccc' }}> ⇅</span>;
  return <span>{dir === 'asc' ? ' ↑' : ' ↓'}</span>;
}

export default function MetricsTable({ metrics, selectedId, onSelectStation }) {
  const [sortKey, setSortKey]  = useState('walk_area_10');
  const [sortDir, setSortDir]  = useState('desc');

  const handleSort = (key) => {
    if (key === sortKey) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sorted = useMemo(() => {
    if (!metrics) return [];
    return [...metrics].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      const cmp = typeof av === 'number' ? av - bv : String(av).localeCompare(String(bv));
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [metrics, sortKey, sortDir]);

  if (!metrics || metrics.length === 0) {
    return (
      <div style={styles.wrap}>
        <div style={styles.header}>All Stations</div>
        <div style={{ padding: 20, color: '#aaa', textAlign: 'center' }}>No data</div>
      </div>
    );
  }

  return (
    <div style={styles.wrap}>
      <div style={styles.header}>
        <span>All Stations ({metrics.length})</span>
        <span style={{ fontSize: 11, color: '#888', fontWeight: 400 }}>
          Click a row to select station
        </span>
      </div>
      <div style={styles.tableWrap}>
        <table style={styles.table}>
          <thead>
            <tr>
              {COLUMNS.map(col => (
                <th
                  key={col.key}
                  style={col.left ? styles.thLeft(sortKey === col.key) : styles.th(sortKey === col.key)}
                  onClick={() => handleSort(col.key)}
                >
                  {col.label}
                  <SortIcon dir={sortKey === col.key ? sortDir : null} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => {
              const selected = row.station_id === selectedId;
              return (
                <tr
                  key={row.station_id}
                  style={styles.row(selected, i % 2 === 0)}
                  onClick={() => onSelectStation && onSelectStation(row.station_id)}
                >
                  <td style={styles.tdLeft}>{row.name_uz ?? row.station_id}</td>
                  <td style={styles.tdLeft}>
                    <span style={styles.lineBadge(row.line)}>{row.line}</span>
                  </td>
                  {['walk_area_5','walk_area_10','walk_area_15','bike_area_15'].map(k => (
                    <td key={k} style={styles.td}>
                      {row[k] !== null && row[k] !== undefined ? Number(row[k]).toFixed(2) : '—'}
                    </td>
                  ))}
                  {['walk_pop_10','bike_pop_10'].map(k => (
                    <td key={k} style={styles.td}>
                      {row[k] !== null && row[k] !== undefined
                        ? Number(row[k]).toLocaleString()
                        : '—'}
                    </td>
                  ))}
                  {['prd_walk','prd_bike'].map(k => {
                    const val   = row[k];
                    const label = prdLabel(val);
                    const color = prdColor(val);
                    return (
                      <td key={k} style={styles.td}>
                        {val !== null && val !== undefined
                          ? <span style={styles.rdiChip(color)}>{label} ({Number(val).toFixed(2)})</span>
                          : '—'}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
