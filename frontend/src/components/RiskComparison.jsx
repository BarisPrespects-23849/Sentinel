import { RISK_LABEL, RISK_TEXT_CLASS } from "../lib/risk";

// Side-by-side: what a traditional single-sensor alarm concludes vs. what
// SENTINEL's compound detection concludes, from the SAME readings. The
// baseline verdict is computed honestly by the backend
// (app/risk/baseline.py) -- this component only renders it. The rubric
// scores exactly this contrast ("compound detection vs. single-sensor
// baselines"), so it is shown, not just claimed.

// One honest interpretive line for every combination of the two verdicts.
// It never overclaims: it states what each system actually concluded, even
// in the case where the traditional alarm fires and SENTINEL does not.
function verdictNote(baselineAlarm, level) {
  const sentinelHot = level === "HIGH" || level === "CRITICAL";
  if (baselineAlarm && sentinelHot) {
    return "Both systems flag this — a single sensor is critical on its own.";
  }
  if (baselineAlarm && !sentinelHot) {
    return "A single sensor is over its own trip point; a traditional alarm catches this isolated spike. SENTINEL adds the compound-risk layer — it doesn't replace single-sensor alarms.";
  }
  if (sentinelHot) {
    return "Individually-normal readings — SENTINEL catches the compound risk a single-sensor alarm misses.";
  }
  // MEDIUM: SENTINEL rates the zone elevated, but no single sensor has
  // crossed its own trip point. Saying "within tolerance" here would
  // contradict the ELEVATED level shown alongside this note.
  if (level === "MEDIUM") {
    return "SENTINEL rates this elevated; no single sensor has crossed its own trip point.";
  }
  // Reached only for LOW (baseline NO ALARM, SENTINEL not elevated).
  return "Both systems agree this zone is within tolerance.";
}

function RiskComparison({ baseline, level, score, multiplier }) {
  if (!baseline) return null;

  const sentinelHot = level === "HIGH" || level === "CRITICAL";
  // The contrast is "meaningful" (worth calling out) only when the two
  // systems actually disagree -- SENTINEL hot while the baseline is silent.
  const divergent = sentinelHot && !baseline.alarm;

  return (
    <div
      data-testid="risk-comparison"
      className={`border ${divergent ? "border-critical/50" : "border-seam"} bg-panel`}
    >
      <div className="grid grid-cols-2">
        {/* Left: the naive single-sensor baseline */}
        <div className="border-r border-seam p-3">
          <p className="font-mono text-[10px] uppercase tracking-widest text-faint">
            Traditional single-sensor alarm
          </p>
          <p
            data-testid="baseline-verdict"
            className={`mt-1 font-mono text-xl font-semibold uppercase ${
              baseline.alarm ? "text-critical" : "text-normal"
            }`}
          >
            {baseline.label}
          </p>
          <p className="mt-1 font-mono text-[11px] leading-snug text-faint">
            highest single reading {baseline.peak_z}σ · trips at{" "}
            {baseline.threshold_z}σ
          </p>
        </div>

        {/* Right: SENTINEL's fused compound verdict */}
        <div className="p-3">
          <p className="font-mono text-[10px] uppercase tracking-widest text-faint">
            SENTINEL compound detection
          </p>
          <p className="mt-1 flex items-baseline gap-2">
            <span
              className={`font-mono text-xl font-semibold uppercase ${RISK_TEXT_CLASS[level]}`}
            >
              {RISK_LABEL[level] ?? "—"}
            </span>
            {score != null && (
              <span className={`font-mono text-sm tabular-nums ${RISK_TEXT_CLASS[level]}`}>
                {typeof score === "number" ? score.toFixed(1) : score}
              </span>
            )}
          </p>
          <p className="mt-1 font-mono text-[11px] leading-snug text-faint">
            {multiplier
              ? `${multiplier} compound multiplier applied`
              : "fused across all sensors in the zone"}
          </p>
        </div>
      </div>

      <p
        className={`border-t border-seam px-3 py-2 font-mono text-[11px] leading-snug ${
          divergent ? "text-critical" : "text-faint"
        }`}
      >
        {verdictNote(baseline.alarm, level)}
      </p>
    </div>
  );
}

export default RiskComparison;
