/**
 * useAccessibilityData — loads and parses all spatial and tabular data.
 *
 * Returns:
 *   stations    : GeoJSON FeatureCollection
 *   isoWalk     : GeoJSON FeatureCollection (walk isochrones)
 *   isoBike     : GeoJSON FeatureCollection (bike isochrones)
 *   metrics     : array of plain objects (one per station)
 *   loading     : boolean
 *   error       : Error | null
 */

import { useEffect, useState } from 'react';
import { DATA_PATHS } from '../constants';

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch ${url}: ${res.status}`);
  return res.json();
}

async function fetchCsv(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch ${url}: ${res.status}`);
  const text = await res.text();
  return parseCsv(text);
}

function parseCsv(text) {
  const lines = text.trim().split('\n');
  if (lines.length < 2) return [];
  const headers = lines[0].split(',').map(h => h.trim());
  return lines.slice(1).map(line => {
    const values = line.split(',');
    const obj = {};
    headers.forEach((h, i) => {
      const raw = (values[i] ?? '').trim();
      // Coerce numeric columns
      const num = Number(raw);
      obj[h] = raw === '' ? null : (!isNaN(num) ? num : raw);
    });
    return obj;
  });
}

export function useAccessibilityData() {
  const [data, setData] = useState({
    stations: null,
    isoWalk:  null,
    isoBike:  null,
    metrics:  null,
    loading:  true,
    error:    null,
  });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [stations, isoWalk, isoBike, metrics] = await Promise.all([
          fetchJson(DATA_PATHS.stations),
          fetchJson(DATA_PATHS.isochronesWalk),
          fetchJson(DATA_PATHS.isochronesBike),
          fetchCsv(DATA_PATHS.metrics),
        ]);

        if (!cancelled) {
          setData({ stations, isoWalk, isoBike, metrics, loading: false, error: null });
        }
      } catch (err) {
        if (!cancelled) {
          setData(prev => ({ ...prev, loading: false, error: err }));
        }
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  return data;
}

/**
 * Build a lookup map: station_id → metrics row.
 * Useful for O(1) lookup from sidebar.
 */
export function buildMetricsMap(metrics) {
  if (!metrics) return {};
  return Object.fromEntries(metrics.map(row => [row.station_id, row]));
}
