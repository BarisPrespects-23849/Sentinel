import { useMemo } from "react";
import { Map, useControl } from "react-map-gl/maplibre";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { GeoJsonLayer, TextLayer } from "@deck.gl/layers";
import "maplibre-gl/dist/maplibre-gl.css";
import { RISK_RGB } from "../lib/risk";
import MapLegend from "./MapLegend";

// Compound-condition red (== --color-critical). Reserved for the co-occurrence
// of a permit AND elevated sensors -- the map's expression of the core thesis.
const COMPOUND_RGB = [239, 68, 68];

// Sensor-point state: normal = muted steel (ISA-101: calm is colorless),
// elevated = high-orange so the specific hot sensor locations stand out.
const SENSOR_NORMAL_RGB = [107, 118, 134];
const SENSOR_ELEVATED_RGB = [249, 115, 22];

// Free CARTO dark basemap -- no API key required, and matches the dark UI.
const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

// Permit badge amber (== --color-warn). A permit is a CAUTION state (authorized
// hazardous work in progress), not an alarm -- red stays reserved for the
// compound/critical condition, keeping the ISA-101 hierarchy intact.
const PERMIT_RGB = [250, 204, 21];

// Human label for a zone's active permits (render only what the API provides).
function permitBadgeText(props) {
  const permits = props.active_permits || [];
  if (permits.length === 0) return "";
  if (permits.length === 1) {
    return `${permits[0].replace(/_/g, " ").toUpperCase()} PERMIT`;
  }
  return `${permits.length} ACTIVE PERMITS`;
}

// Middle of a zone polygon's top edge. The label stack anchors here (not the
// centroid) so it floats ABOVE the zone instead of over the clustered sensor
// dots inside it -- keeping the elevated-sensor colors legible at any zoom.
function zoneTopCenter(feature) {
  const ring = feature.geometry.coordinates[0];
  let minLng = Infinity;
  let maxLng = -Infinity;
  let maxLat = -Infinity;
  for (const [lng, lat] of ring) {
    if (lng < minLng) minLng = lng;
    if (lng > maxLng) maxLng = lng;
    if (lat > maxLat) maxLat = lat;
  }
  return [(minLng + maxLng) / 2, maxLat];
}

// Stacked pixel offsets above the zone's top edge (all anchored "bottom", so
// text extends upward). Order top-to-bottom: COMPOUND / NAME / PERMIT.
const LABEL_OFFSET_NAME = [0, -30];
const LABEL_OFFSET_PERMIT = [0, -8];
const LABEL_OFFSET_COMPOUND = [0, -52];

// Centered on the seeded plant zones (they span ~1.4km around this point).
const INITIAL_VIEW_STATE = {
  longitude: 77.5015,
  latitude: 13.003,
  zoom: 15.4,
};

// react-map-gl v8 + deck.gl v9 integration: the Map owns the camera, and
// deck.gl attaches to it as an overlay control (MapboxOverlay implements
// maplibre's IControl -- it works with MapLibre despite the name). The
// older pattern (Map as a child of <DeckGL>) no longer renders reliably.
function DeckGLOverlay(props) {
  const overlay = useControl(() => new MapboxOverlay(props));
  overlay.setProps(props);
  return null;
}

function PlantMap({ plantData, selectedZoneId, onZoneClick }) {
  const layers = useMemo(() => {
    if (!plantData) return [];

    const zoneLayer = new GeoJsonLayer({
      id: "zones",
      data: plantData.zones,
      filled: true,
      stroked: true,
      getFillColor: (f) => {
        const [r, g, b] = RISK_RGB[f.properties.risk_level] || RISK_RGB.UNKNOWN;
        const isSelected = f.properties.zone_id === selectedZoneId;
        return [r, g, b, isSelected ? 150 : 70];
      },
      getLineColor: (f) => {
        const [r, g, b] = RISK_RGB[f.properties.risk_level] || RISK_RGB.UNKNOWN;
        return [r, g, b, 255];
      },
      getLineWidth: 3,
      lineWidthMinPixels: 2,
      pickable: true,
      autoHighlight: true,
      highlightColor: [232, 237, 244, 40],
      onClick: (info) => info.object && onZoneClick(info.object.properties.zone_id),
      updateTriggers: {
        getFillColor: [selectedZoneId],
        getLineColor: [selectedZoneId],
      },
    });

    const sensorLayer = new GeoJsonLayer({
      id: "sensors",
      data: plantData.sensors,
      pointType: "circle",
      // Elevated sensors read slightly larger so the eye lands on them first.
      getPointRadius: (f) => (f.properties.elevated ? 8 : 5),
      pointRadiusMinPixels: 4,
      getFillColor: (f) =>
        f.properties.elevated
          ? [...SENSOR_ELEVATED_RGB, 255]
          : [...SENSOR_NORMAL_RGB, 255],
      getLineColor: (f) =>
        f.properties.elevated ? [...SENSOR_ELEVATED_RGB, 255] : [11, 14, 19, 255],
      getLineWidth: (f) => (f.properties.elevated ? 2 : 1),
      lineWidthMinPixels: 1,
      stroked: true,
      pickable: true,
      updateTriggers: {
        getPointRadius: [plantData],
        getFillColor: [plantData],
        getLineColor: [plantData],
      },
    });

    const labelLayer = new TextLayer({
      id: "zone-labels",
      data: plantData.zones.features,
      getPosition: zoneTopCenter,
      getText: (f) => f.properties.name.toUpperCase(),
      getSize: 12,
      getColor: [232, 237, 244, 190],
      fontFamily: "IBM Plex Mono, monospace",
      characterSet: "auto",
      getTextAnchor: "middle",
      getAlignmentBaseline: "bottom",
      getPixelOffset: LABEL_OFFSET_NAME,
      background: true,
      getBackgroundColor: [11, 14, 19, 150],
      backgroundPadding: [4, 2],
    });

    // Permit badge: a posted work-permit placard on zones with an active
    // permit. Amber, sits just above the zone (below the zone name). Surfaces
    // the permit spatially -- the first half of the compound-risk story.
    const permitLayer = new TextLayer({
      id: "permit-badges",
      data: plantData.zones.features.filter(
        (f) => (f.properties.active_permits || []).length > 0,
      ),
      getPosition: zoneTopCenter,
      getText: (f) => permitBadgeText(f.properties),
      getSize: 10,
      getColor: [...PERMIT_RGB, 255],
      fontFamily: "IBM Plex Mono, monospace",
      fontWeight: 600,
      characterSet: "auto",
      getTextAnchor: "middle",
      getAlignmentBaseline: "bottom",
      getPixelOffset: LABEL_OFFSET_PERMIT,
      background: true,
      getBackgroundColor: [11, 14, 19, 220],
      backgroundPadding: [5, 3],
      getBorderColor: [...PERMIT_RGB, 220],
      getBorderWidth: 1,
    });

    const compoundZones = plantData.zones.features.filter(
      (f) => f.properties.compound,
    );

    // Compound ring: a bold red hazard-outline drawn ON TOP of the risk
    // border, so a zone in the compound condition (permit + elevated sensors)
    // is spatially unmistakable regardless of its fill color.
    const compoundRingLayer = new GeoJsonLayer({
      id: "compound-rings",
      data: { type: "FeatureCollection", features: compoundZones },
      filled: false,
      stroked: true,
      getLineColor: [...COMPOUND_RGB, 255],
      getLineWidth: 6,
      lineWidthMinPixels: 4,
      pickable: false,
    });

    // Compound marker: the top of the stack (COMPOUND RISK / name / PERMIT),
    // floating above the zone so the co-occurrence is narrated in place
    // without covering the sensor dots inside the zone.
    const compoundMarkerLayer = new TextLayer({
      id: "compound-markers",
      data: compoundZones,
      getPosition: zoneTopCenter,
      getText: () => "COMPOUND RISK",
      getSize: 11,
      getColor: [...COMPOUND_RGB, 255],
      fontFamily: "IBM Plex Mono, monospace",
      fontWeight: 700,
      characterSet: "auto",
      getTextAnchor: "middle",
      getAlignmentBaseline: "bottom",
      getPixelOffset: LABEL_OFFSET_COMPOUND,
      background: true,
      getBackgroundColor: [11, 14, 19, 230],
      backgroundPadding: [5, 3],
      getBorderColor: [...COMPOUND_RGB, 230],
      getBorderWidth: 1,
    });

    return [
      zoneLayer,
      compoundRingLayer,
      sensorLayer,
      labelLayer,
      permitLayer,
      compoundMarkerLayer,
    ];
  }, [plantData, selectedZoneId, onZoneClick]);

  return (
    <div className="relative h-full w-full bg-bg">
      <Map initialViewState={INITIAL_VIEW_STATE} mapStyle={MAP_STYLE}>
        <DeckGLOverlay
          layers={layers}
          getTooltip={({ object }) => {
            if (!object?.properties) return null;
            const p = object.properties;
            const permits = p.active_permits || [];
            const permitLine =
              permits.length > 0
                ? `<br/><span style="color:#facc15">permit: ${permits
                    .map((t) => t.replace(/_/g, " "))
                    .join(", ")}</span>`
                : "";
            const compoundLine = p.compound
              ? `<br/><span style="color:#ef4444">COMPOUND RISK — permit + elevated sensors</span>`
              : "";
            const sensorState = p.elevated
              ? `<br/><span style="color:#f97316">elevated${p.z != null ? ` ${p.z}σ` : ""}</span>`
              : `<br/><span style="color:#6b7686">normal</span>`;
            const html = p.sensor_id
              ? `<span style="color:#8b95a5">${p.sensor_type} sensor</span><br/>${p.sensor_id}${sensorState}`
              : `${p.name}<br/><span style="color:#8b95a5">risk ${p.risk_score ?? "--"} · ${p.risk_level}</span>${permitLine}${compoundLine}`;
            return {
              html,
              style: {
                background: "#171c26",
                color: "#e8edf4",
                border: "1px solid #232a36",
                fontFamily: "IBM Plex Mono, monospace",
                fontSize: "11px",
                padding: "6px 8px",
                borderRadius: "0",
              },
            };
          }}
        />
      </Map>
      <MapLegend />
    </div>
  );
}

export default PlantMap;
