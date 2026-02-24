/**
 * Map — main Leaflet map component.
 *
 * Renders:
 *   - OSM base tile layer (no API key required)
 *   - Isochrone polygon layers (walk or bike, filtered by time threshold)
 *   - Station circle markers colored by metro line
 *   - Click interaction → select station → updates sidebar
 */

import React, { useEffect, useRef } from 'react';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  GeoJSON,
  Popup,
  useMap,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

import {
  MAP_CENTER,
  MAP_ZOOM,
  LINE_COLORS,
  isochroneStyle,
  stationStyle,
  metricColor,
  THRESHOLDS,
} from '../constants';

// ── Fly to selected station ───────────────────────────────────────────────────
function FlyToSelected({ station }) {
  const map = useMap();
  useEffect(() => {
    if (!station) return;
    const [lon, lat] = station.geometry.coordinates;
    map.flyTo([lat, lon], Math.max(map.getZoom(), 14), { duration: 0.8 });
  }, [station, map]);
  return null;
}

// ── Isochrone layer (memoized key forces re-render on mode/threshold change) ──
function IsochroneLayer({ geojson, mode, threshold, opacity }) {
  if (!geojson) return null;

  const filtered = {
    ...geojson,
    features: geojson.features.filter(
      f => f.properties.mode === mode && f.properties.minutes === threshold
    ),
  };

  if (!filtered.features.length) return null;

  return (
    <GeoJSON
      key={`${mode}-${threshold}-${opacity}`}
      data={filtered}
      style={feature =>
        isochroneStyle(
          feature.properties.mode,
          feature.properties.minutes,
          opacity,
        )
      }
      onEachFeature={(feature, layer) => {
        const p = feature.properties;
        layer.bindTooltip(
          `${p.station_id} | ${p.mode} | ${p.minutes} min<br/>` +
          `Area: ${p.area_km2?.toFixed(2) ?? '?'} km²<br/>` +
          `Pop: ${p.population !== undefined ? Number(p.population).toLocaleString() : '?'}`,
          { sticky: true }
        );
      }}
    />
  );
}

// ── Main Map component ────────────────────────────────────────────────────────
export default function Map({
  stations,
  isoWalk,
  isoBike,
  mode,
  threshold,
  opacity,
  selectedStation,
  onSelectStation,
  metricsMap   = {},
  markerColorBy = 'line',
  metricRange  = {},
}) {
  const isoData = mode === 'walk' ? isoWalk : isoBike;

  return (
    <MapContainer
      center={MAP_CENTER}
      zoom={MAP_ZOOM}
      style={{ height: '100%', width: '100%' }}
      zoomControl={true}
    >
      {/* OSM base tiles */}
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        maxZoom={19}
      />

      {/* Isochrone polygons */}
      <IsochroneLayer
        geojson={isoData}
        mode={mode}
        threshold={threshold}
        opacity={opacity}
      />

      {/* Station markers */}
      {stations?.features?.map(feature => {
        const [lon, lat] = feature.geometry.coordinates;
        const p          = feature.properties;
        const selected   = selectedStation?.properties?.station_id === p.station_id;

        // Determine fill color: by line or by metric
        let fillColor;
        if (markerColorBy === 'line') {
          fillColor = stationStyle(p.line, selected).fillColor;
        } else {
          const m   = metricsMap[p.station_id] ?? {};
          const val = m[markerColorBy];
          const rng = metricRange[markerColorBy] ?? { min: 0, max: 1 };
          fillColor = metricColor(markerColorBy, val, rng.min, rng.max);
        }

        const styleProps = {
          ...stationStyle(p.line, selected),
          fillColor,
        };

        return (
          <CircleMarker
            key={p.station_id}
            center={[lat, lon]}
            {...styleProps}
            eventHandlers={{
              click: () => onSelectStation(feature),
            }}
          >
            <Popup>
              <strong>{p.name_uz}</strong><br />
              <span style={{ color: '#666' }}>{p.name_ru}</span><br />
              <span style={{
                background: LINE_COLORS[p.line] ?? '#757575',
                color: 'white',
                padding: '1px 6px',
                borderRadius: 3,
                fontSize: 11,
              }}>
                {p.line}
              </span>
            </Popup>
          </CircleMarker>
        );
      })}

      <FlyToSelected station={selectedStation} />
    </MapContainer>
  );
}
