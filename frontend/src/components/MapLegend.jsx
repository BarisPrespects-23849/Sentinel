import { RISK_LABEL, RISK_RGB } from "../lib/risk";

// Status legend: every color always appears WITH its text label (status
// colors are never color-alone -- that pairing is also what makes the
// amber/orange adjacency legal for color-vision deficiencies).

const LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

function MapLegend() {
  return (
    <div className="pointer-events-none absolute bottom-10 left-3 flex items-center gap-4 border border-seam bg-surface/90 px-3 py-1.5 backdrop-blur-sm">
      {LEVELS.map((level) => {
        const [r, g, b] = RISK_RGB[level];
        return (
          <span key={level} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2 w-2 rounded-sm"
              style={{ background: `rgb(${r},${g},${b})` }}
            />
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
              {RISK_LABEL[level]}
            </span>
          </span>
        );
      })}
      {/* Divider then permit + compound markers -- not risk levels but the
          two ingredients of the compound condition, so they're set apart. */}
      <span className="h-3 w-px bg-seam" />
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-2 w-2 rounded-sm border border-warn" />
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
          permit
        </span>
      </span>
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-2 w-2 rounded-sm border-2 border-critical" />
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
          compound
        </span>
      </span>
      {/* Sensor points are round (vs square zone swatches). Orange = a
          specific sensor reading elevated -- traces a zone's score to a spot. */}
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-2 w-2 rounded-full bg-high" />
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
          elevated sensor
        </span>
      </span>
    </div>
  );
}

export default MapLegend;
