import { useEffect, useState } from "react";
import { API_BASE_URL } from "../api";

// Evaluation Results: a judge-facing screen mapping the offline benchmark to
// the hackathon's evaluation criteria. Every number is read live from
// GET /benchmark/results (the JSON the harness actually wrote) -- nothing is
// hardcoded, so a displayed figure cannot drift from the computed benchmark.
// All results are SYNTHETIC (generated scenarios), labeled visibly.

const pct1 = (x) => `${(x * 100).toFixed(1)}%`;
const pct0 = (x) => `${Math.round(x * 100)}%`;

function ConfusionMatrix({ title, cm, accent }) {
  const cell = (label, value, danger) => (
    <div
      className={`border p-3 ${
        danger ? "border-critical/50 bg-critical/5" : "border-seam bg-panel"
      }`}
    >
      <div className="font-mono text-[10px] uppercase tracking-widest text-faint">
        {label}
      </div>
      <div
        className={`mt-1 font-mono text-2xl tabular-nums ${
          danger ? "text-critical" : "text-ink"
        }`}
      >
        {value}
      </div>
    </div>
  );
  return (
    <div className="border border-seam bg-surface p-5">
      <div className="flex items-baseline justify-between">
        <h3 className={`font-display text-xl font-semibold uppercase tracking-wide ${accent}`}>
          {title}
        </h3>
        <span className="font-mono text-[11px] uppercase tracking-widest text-faint">
          FN rate {pct1(cm.false_negative_rate)}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        {cell("caught (TP)", cm.true_positives)}
        {cell("false alarm (FP)", cm.false_positives)}
        {cell("MISSED (FN)", cm.false_negatives, true)}
        {cell("clear (TN)", cm.true_negatives)}
      </div>
    </div>
  );
}

function Stat({ value, label, sub, tone = "text-ink" }) {
  return (
    <div className="border border-seam bg-surface p-5">
      <div className={`font-mono text-4xl font-semibold tabular-nums ${tone}`}>{value}</div>
      <div className="mt-1 font-mono text-[11px] uppercase tracking-widest text-faint">
        {label}
      </div>
      {sub && <p className="mt-2 text-xs leading-relaxed text-muted">{sub}</p>}
    </div>
  );
}

function EvaluationScreen() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/benchmark/results`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(setData)
      .catch(() =>
        setError("Benchmark results unavailable -- run python -m app.benchmark.run."),
      );
  }, []);

  const red = data?.false_negative_rate_reduction;
  const sent = data?.systems?.sentinel?.confusion;
  const base = data?.systems?.single_sensor_baseline?.confusion;
  const lt = data?.prediction_lead_time;

  return (
    <div className="h-full overflow-y-auto bg-bg">
      <div className="mx-auto max-w-4xl px-6 py-12">
        <div className="font-mono text-[11px] uppercase tracking-widest text-faint">
          Evaluation results — offline benchmark
        </div>

        {error && (
          <p className="mt-4 border border-critical/60 bg-critical/10 px-3 py-2 font-mono text-xs text-critical">
            {error}
          </p>
        )}

        {data && (
          <>
            <h2 className="mt-3 font-display text-5xl font-semibold uppercase leading-none tracking-wide text-ink">
              {pct0(red.relative_reduction)} fewer{" "}
              <span className="text-critical">missed</span> compound hazards
            </h2>

            {/* Prominent synthetic disclaimer */}
            <p className="mt-4 max-w-2xl border-l-2 border-warn/70 pl-3 font-mono text-xs leading-relaxed text-warn">
              Synthetic-scenario benchmark — demonstration, not real-incident
              validation. {data.scenario_count} generated scenarios (seed {data.seed}).
            </p>

            {/* Criterion 1: False-negative reduction */}
            <div className="mt-10 font-mono text-[11px] uppercase tracking-widest text-faint">
              False-negative reduction — the metric that saves lives
            </div>
            <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
              <Stat
                value={`${pct1(red.baseline_fnr)} → ${pct1(red.sentinel_fnr)}`}
                label="false-negative rate: baseline → SENTINEL"
                sub={`A ${pct0(red.relative_reduction)} relative reduction (${(red.absolute_reduction * 100).toFixed(1)} points).`}
                tone="text-ink"
              />
              <Stat
                value={data.compound_missed_by_baseline_caught_by_sentinel}
                label="compound hazards caught that the baseline missed entirely"
                sub={`Of ${data.compound_dangerous_total} genuine compound hazards — individually-moderate readings no single-sensor alarm would trip.`}
                tone="text-ink"
              />
              <Stat
                value={data.compound_missed_by_both}
                label="hazard missed by BOTH systems"
                sub="Reported honestly — SENTINEL is not flawless; the mildest compound case is missed too."
                tone="text-warn"
              />
            </div>

            {/* Criterion 2: Compound detection (confusion matrices) */}
            <div className="mt-10 font-mono text-[11px] uppercase tracking-widest text-faint">
              Compound detection — baseline vs SENTINEL
            </div>
            <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
              <ConfusionMatrix
                title="Single-sensor baseline"
                cm={base}
                accent="text-muted"
              />
              <ConfusionMatrix title="SENTINEL" cm={sent} accent="text-ink" />
            </div>

            {/* Criterion 3: Prediction lead time */}
            <div className="mt-10 font-mono text-[11px] uppercase tracking-widest text-faint">
              Prediction lead time — warning before critical
            </div>
            <div className="mt-4 border border-seam bg-surface p-5">
              {lt.sample_size ? (
                <>
                  <div className="flex flex-wrap items-baseline gap-x-3">
                    <span className="font-mono text-4xl font-semibold tabular-nums text-ink">
                      ~{Math.round(lt.median_seconds)}s
                    </span>
                    <span className="font-mono text-sm uppercase tracking-widest text-faint">
                      median warning lead time
                    </span>
                  </div>
                  <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
                    Across {lt.sample_size} rising compound hazards, SENTINEL flags the
                    zone a median of ~{Math.round(lt.median_seconds)} seconds before a
                    sensor reaches its critical threshold (range{" "}
                    {lt.min_seconds}–{Math.round(lt.max_seconds)}s).
                  </p>
                  <p className="mt-2 max-w-2xl font-mono text-[11px] leading-relaxed text-faint">
                    Mean is {lt.mean_seconds}s — higher than the median because a few
                    slow-ramp cases pull the tail right; the median is the representative
                    figure. Scoped to the elevated, hazard-driving sensors.
                  </p>
                </>
              ) : (
                <p className="text-sm text-muted">{lt.note}</p>
              )}
            </div>

            {/* Sourcing footer */}
            <p className="mt-10 border-t border-seam pt-4 font-mono text-[11px] leading-relaxed text-faint">
              {data.disclaimer} Both systems score the same inputs through their real
              code paths; ground truth is defined by construction (≥2 sensor types
              elevated = dangerous), never by either system's output.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default EvaluationScreen;
