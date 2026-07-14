import { useEffect, useState } from "react";
import { API_BASE_URL } from "../api";
import { RISK_LABEL, RISK_TEXT_CLASS } from "../lib/risk";
import WhatIfPanel from "./WhatIfPanel";
import RiskComparison from "./RiskComparison";

// Full multi-agent assessment for one zone, fetched on demand (this path
// can invoke the LLM-backed Compliance Agent, so it never runs on a poll).

// Causal-chain card typing. "compound" is not a backend source -- it's the
// rule signal with no sensor_id (the cross-sensor insight), promoted to its
// own visual type because it's the finding the whole system exists for.
const SIGNAL_KINDS = {
  compound: { label: "compound risk", order: 0, accent: true },
  rule: { label: "sensor", order: 1 },
  permit: { label: "work permit", order: 2 },
  maintenance: { label: "maintenance", order: 3 },
  compliance: { label: "regulation", order: 4 },
  ml: { label: "ml model", order: 5 },
};

function classifySignal(sig) {
  if (sig.source === "rule" && !sig.sensor_id) return "compound";
  return sig.source in SIGNAL_KINDS ? sig.source : "rule";
}

// Right-aligned weight readout: only shown where the number genuinely
// means "points added" (or the compound multiplier); the ML probability
// and zero-weight context signals explain themselves in prose.
function weightText(sig, kind) {
  if (kind === "compound" && typeof sig.weight_contribution === "string") {
    return sig.weight_contribution.replace("x multiplier", "×");
  }
  if ((kind === "rule" || kind === "permit") && sig.weight_contribution > 0) {
    return `+${sig.weight_contribution}`;
  }
  return null;
}

function CausalChain({ signals }) {
  const ordered = [...signals].sort((a, b) => {
    const ka = SIGNAL_KINDS[classifySignal(a)].order;
    const kb = SIGNAL_KINDS[classifySignal(b)].order;
    if (ka !== kb) return ka - kb;
    // Within a kind, heaviest contribution first.
    return (Number(b.weight_contribution) || 0) - (Number(a.weight_contribution) || 0);
  });

  return (
    <ul className="flex flex-col gap-2" data-testid="causal-chain">
      {ordered.map((sig, i) => {
        const kind = classifySignal(sig);
        const meta = SIGNAL_KINDS[kind];
        const weight = weightText(sig, kind);
        return (
          <li
            key={i}
            className={`border p-3 text-sm ${
              meta.accent ? "border-critical/50 bg-critical/5" : "border-seam bg-panel"
            }`}
          >
            <div className="flex items-baseline justify-between gap-2">
              <span
                className={`border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-widest ${
                  sig.degraded
                    ? "border-warn/50 text-warn"
                    : meta.accent
                      ? "border-critical/50 text-critical"
                      : "border-seam text-faint"
                }`}
              >
                {/* Degraded compliance still shows its citations -- label it
                    so the missing narrative reads as graceful degradation,
                    not a normal citation card. */}
                {sig.degraded ? `${meta.label} · narrative offline` : meta.label}
              </span>
              {weight && (
                <span className="font-mono text-xs tabular-nums text-muted">{weight}</span>
              )}
            </div>
            {/* The LLM occasionally emits markdown emphasis; we render
                plain text, so strip the asterisks. */}
            <p className="mt-1.5 leading-snug text-ink">
              {(sig.description ?? "").replace(/\*+/g, "")}
            </p>
            {sig.citations?.length > 0 && (
              <p className="mt-1.5 font-mono text-[10px] leading-relaxed text-faint">
                {sig.citations.join(" · ")}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

// Ticks a countdown down from the fetched value, once per second.
function useCountdown(seconds) {
  const [remaining, setRemaining] = useState(seconds);
  useEffect(() => {
    setRemaining(seconds);
    if (seconds == null) return;
    const interval = setInterval(
      () => setRemaining((r) => (r != null && r > 0 ? r - 1 : r)),
      1000,
    );
    return () => clearInterval(interval);
  }, [seconds]);
  return remaining;
}

// Urgency bands for the countdown, most-urgent first. Same alarm colors as
// everywhere else (lib/risk.js semantics); the pulse is reserved for the
// final 30 seconds, mirroring how CRITICAL zones pulse on the map.
const COUNTDOWN_BANDS = [
  { min: 120, text: "text-high", bar: "bg-high", border: "border-seam" },
  { min: 30, text: "text-critical", bar: "bg-critical", border: "border-critical/40" },
  { min: 0, text: "text-critical alarm-pulse", bar: "bg-critical", border: "border-critical/70" },
];

function Countdown({ seconds }) {
  const remaining = useCountdown(seconds);
  if (remaining == null) return null;

  const band = COUNTDOWN_BANDS.find((b) => remaining >= b.min) ?? COUNTDOWN_BANDS[2];
  const expired = remaining <= 0;
  const fraction = seconds > 0 ? Math.max(0, remaining / seconds) : 0;
  const mm = String(Math.floor(remaining / 60)).padStart(2, "0");
  const ss = String(Math.floor(remaining % 60)).padStart(2, "0");

  return (
    <div className={`border bg-panel px-3 py-2 ${band.border}`} data-testid="countdown">
      <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
        Time to critical at current trend
      </p>
      <p className={`mt-1 font-mono text-5xl font-semibold leading-none tabular-nums ${band.text}`}>
        {mm}:{ss}
      </p>
      <div className="mt-2 h-1 overflow-hidden bg-seam">
        <div
          className={`h-full transition-[width] duration-1000 ease-linear ${band.bar}`}
          style={{ width: `${fraction * 100}%` }}
        />
      </div>
      <p className="mt-1.5 font-mono text-[11px] leading-snug text-faint">
        {expired
          ? "Projected threshold reached -- reselect the zone to reassess."
          : "Linear projection from the last 60s of readings, not a guarantee."}
      </p>
    </div>
  );
}

function ZoneDetailPanel({ zoneId, onClose }) {
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (zoneId == null) return;
    setLoading(true);
    setAssessment(null);
    setError(null);
    fetch(`${API_BASE_URL}/agents/assess/${zoneId}`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(
            res.status === 503
              ? "Database unavailable -- check that Docker is running."
              : `Assessment failed (HTTP ${res.status}).`,
          );
        }
        return res.json();
      })
      .then(setAssessment)
      .catch((err) => {
        // A rejected fetch (backend down / mid-restart) throws a TypeError
        // with the opaque "Failed to fetch" -- replace it with an operator-
        // legible message. Our own res.ok errors already read cleanly.
        const networkError = err instanceof TypeError;
        setError(
          networkError
            ? "Backend unreachable -- check that the API is running on :8000."
            : err.message ?? "Assessment failed.",
        );
      })
      .finally(() => setLoading(false));
  }, [zoneId]);

  if (zoneId == null) {
    return (
      <div className="p-4">
        <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
          Zone assessment
        </p>
        <p className="mt-2 text-sm text-muted">
          Select a zone to run the full assessment: sensors, work permits,
          maintenance records, and applicable regulations.
        </p>
      </div>
    );
  }

  const level = assessment?.risk_level ?? "UNKNOWN";
  // A null sensor_score means the sensor agent found no readings in the
  // scoring window (sensors offline / just-cleared history). The fused
  // score then reflects only permits + maintenance, which would otherwise
  // read misleadingly as "0.0 / normal" -- so we label the gap explicitly.
  const noSensorData = assessment != null && assessment.sensor_score == null;
  // The fused-score breakdown, derived ONLY from the three fields rendered
  // below (sensor_score + permit_bonus + maintenance_bonus). One source,
  // shown twice, so the arithmetic can never disagree with the parts. The
  // backend caps the fused score at 100 (min(100, sum)); we surface that
  // cap explicitly -- but ONLY when the raw sum actually exceeds 100, so a
  // legitimately sub-100 zone shows a plain sum with no "capped" language.
  const permitBonus = assessment?.permit_bonus ?? 0;
  const maintBonus = assessment?.maintenance_bonus ?? 0;
  const rawSum =
    assessment?.sensor_score != null
      ? Number((assessment.sensor_score + permitBonus + maintBonus).toFixed(1))
      : null;
  const capped = rawSum != null && rawSum > 100;
  // Compound multiplier for the comparison's right column, read from the
  // engine's own compound signal (never re-derived on the client).
  const compoundSignal = assessment?.contributing_signals?.find((s) =>
    s.description?.startsWith("Compound risk"),
  );
  const multiplierText =
    typeof compoundSignal?.weight_contribution === "string"
      ? compoundSignal.weight_contribution.replace("x multiplier", "×")
      : null;

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto p-4">
      <div className="flex items-baseline justify-between">
        <h2 className="font-display text-xl font-semibold uppercase tracking-wide text-ink">
          {assessment?.zone_name ?? `Zone ${zoneId}`}
        </h2>
        <button
          onClick={onClose}
          className="font-mono text-xs text-faint hover:text-ink focus-visible:outline-2 focus-visible:outline-ink"
        >
          close
        </button>
      </div>

      {loading && (
        <div className="flex flex-col gap-3" aria-label="Loading assessment">
          <p className="font-mono text-xs text-muted">
            Running assessment -- sensors, permits, maintenance, regulations...
          </p>
          <div className="h-14 animate-pulse border border-seam bg-panel" />
          <div className="h-20 animate-pulse border border-seam bg-panel" />
          <div className="h-20 animate-pulse border border-seam bg-panel" />
        </div>
      )}

      {error && (
        <div className="border border-critical/60 bg-critical/10 p-3">
          <p className="font-mono text-xs text-critical">{error}</p>
          <p className="mt-1 text-xs text-muted">
            Reselect the zone to retry.
          </p>
        </div>
      )}

      {assessment && (
        <>
          <div className="border border-seam bg-panel px-3 py-2">
            <p className="font-mono text-[10px] uppercase tracking-widest text-faint">
              Full multi-agent assessment
            </p>
            <div className="mt-0.5 flex items-baseline gap-3">
              <span className={`font-mono text-4xl font-semibold tabular-nums ${RISK_TEXT_CLASS[level]}`}>
                {assessment.risk_score ?? "--"}
              </span>
              <span className={`font-mono text-sm uppercase tracking-widest ${RISK_TEXT_CLASS[level]}`}>
                {RISK_LABEL[level]}
              </span>
            </div>
          </div>

          {noSensorData && (
            <div className="border border-warn/50 bg-warn/10 px-3 py-2">
              <p className="font-mono text-[11px] uppercase tracking-widest text-warn">
                No recent sensor readings
              </p>
              <p className="mt-1 text-xs leading-snug text-muted">
                This zone has no sensor data in the last 60 seconds -- sensors may be
                offline. The score below reflects only permits and maintenance records
                until live readings resume.
              </p>
            </div>
          )}

          <Countdown seconds={assessment.time_to_critical_seconds} />

          {noSensorData ? (
            <div className="flex gap-4 font-mono text-[11px] text-faint">
              <span>sensors n/a</span>
              <span>permits +{permitBonus}</span>
              <span>maintenance +{maintBonus}</span>
            </div>
          ) : (
            <p className="font-mono text-[11px] leading-snug text-faint">
              sensors {assessment.sensor_score} + permits {permitBonus} + maintenance{" "}
              {maintBonus} = {rawSum}
              {capped && (
                <span className="text-muted"> &rarr; capped at 100</span>
              )}
            </p>
          )}

          {assessment.single_sensor_baseline && (
            <RiskComparison
              baseline={assessment.single_sensor_baseline}
              level={level}
              score={assessment.risk_score}
              multiplier={multiplierText}
            />
          )}

          <p className="mt-1 font-mono text-[11px] uppercase tracking-widest text-faint">
            Causal chain -- why this score
          </p>
          {assessment.contributing_signals?.length > 0 ? (
            <CausalChain signals={assessment.contributing_signals} />
          ) : (
            <p className="text-sm text-muted">
              {noSensorData
                ? "No sensor readings and no active permits or maintenance flags -- nothing to assess for this zone right now."
                : "No active risk signals. This zone is operating normally."}
            </p>
          )}

          <WhatIfPanel zoneId={zoneId} />
        </>
      )}
    </div>
  );
}

export default ZoneDetailPanel;
