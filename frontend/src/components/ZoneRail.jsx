import { RISK_BAR_CLASS, RISK_LABEL, RISK_TEXT_CLASS } from "../lib/risk";
import DemoControls from "./DemoControls";

// The annunciator rail: one alarm-window tile per zone, modeled on the
// physical annunciator panels in real control rooms. Stays quiet (steel
// gray) while a zone is normal; lights up only as risk rises.

function ZoneTile({ feature, selected, onSelect }) {
  const p = feature.properties;
  const level = p.risk_level ?? "UNKNOWN";
  return (
    <button
      onClick={() => onSelect(p.zone_id)}
      className={`group w-full border-b border-seam border-l-2 px-4 py-3 text-left transition-colors hover:bg-panel focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ink ${
        selected ? "border-l-ink bg-panel" : "border-l-transparent bg-surface"
      }`}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-display text-lg font-medium uppercase tracking-wide text-ink">
          {p.name}
        </span>
        <span
          className={`font-mono text-2xl font-semibold tabular-nums transition-colors duration-500 ${RISK_TEXT_CLASS[level]}`}
        >
          {p.risk_score ?? "--"}
        </span>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <div className="h-1 flex-1 overflow-hidden rounded-full bg-seam">
          <div
            className={`h-full transition-[width] duration-700 ease-out ${RISK_BAR_CLASS[level]}`}
            style={{ width: `${Math.max(4, Math.min(100, p.risk_score ?? 0))}%` }}
          />
        </div>
        <span className={`font-mono text-[11px] uppercase ${RISK_TEXT_CLASS[level]}`}>
          {RISK_LABEL[level]}
        </span>
      </div>
    </button>
  );
}

function ZoneRail({ plantData, selectedZoneId, onSelect }) {
  const features = plantData?.zones?.features ?? [];
  const worst = features.reduce(
    (max, f) => Math.max(max, f.properties.risk_score ?? 0),
    0,
  );

  return (
    <nav className="flex w-64 flex-none flex-col border-r border-seam bg-surface">
      <div className="flex items-baseline justify-between border-b border-seam px-4 py-2">
        <span className="font-mono text-[11px] uppercase tracking-widest text-faint">
          Zones
        </span>
        {/* The rail is the live sensor-only read; the detail panel's headline
            is the full fused assessment. Labeling avoids reading the two
            scores as the system disagreeing with itself. */}
        <span className="font-mono text-[10px] uppercase tracking-widest text-faint">
          live sensor score
        </span>
      </div>
      {features.map((f) => (
        <ZoneTile
          key={f.properties.zone_id}
          feature={f}
          selected={f.properties.zone_id === selectedZoneId}
          onSelect={onSelect}
        />
      ))}
      <div className="mt-auto px-4 py-3">
        <p className="font-mono text-[11px] text-faint">
          {features.length === 0
            ? "Waiting for plant data..."
            : worst < 30
              ? "All zones normal."
              : "Attention required -- open the affected zone."}
        </p>
      </div>
      <DemoControls selectedZoneId={selectedZoneId} />
    </nav>
  );
}

export default ZoneRail;
