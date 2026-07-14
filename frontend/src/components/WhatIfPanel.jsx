import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "../api";
import { RISK_LABEL, RISK_TEXT_CLASS } from "../lib/risk";
import RiskComparison from "./RiskComparison";

// The what-if simulator: sliders for each sensor type in the zone, scored
// live through the REAL risk engine (POST /risk/simulate runs the same
// rules + ML code path as live scoring). Requests are debounced while
// dragging, and stale responses are dropped via a sequence counter.

const DEBOUNCE_MS = 250;
const COUNT_UP_MS = 450;

// Animates a number toward its target with an ease-out curve, so score
// changes read as movement on an instrument rather than value swaps.
// The first value renders instantly (no 0 -> n count on zone open), and
// prefers-reduced-motion disables the tween entirely.
function useAnimatedNumber(target, resetKey) {
  const [display, setDisplay] = useState(target);
  const displayRef = useRef(target);
  const rafRef = useRef(null);
  const firstRef = useRef(true);

  // A new zone is a new instrument -- render its first score instantly
  // instead of tweening from the previous zone's value.
  useEffect(() => {
    firstRef.current = true;
  }, [resetKey]);

  useEffect(() => {
    if (target == null) return undefined;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (firstRef.current || reduced) {
      firstRef.current = false;
      displayRef.current = target;
      setDisplay(target);
      return undefined;
    }
    const from = displayRef.current;
    const start = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - start) / COUNT_UP_MS);
      const eased = 1 - (1 - t) ** 3;
      const value = from + (target - from) * eased;
      displayRef.current = value;
      setDisplay(value);
      if (t < 1) rafRef.current = requestAnimationFrame(step);
    };
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target]);

  return display;
}

function WhatIfPanel({ zoneId }) {
  const [controls, setControls] = useState(null);
  const [values, setValues] = useState({});
  const [result, setResult] = useState(null);
  const debounceTimer = useRef(null);
  const requestSeq = useRef(0);

  const [stale, setStale] = useState(false);

  const runSimulation = useCallback(
    (zone, vals) => {
      const seq = ++requestSeq.current;
      fetch(`${API_BASE_URL}/risk/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ zone_id: zone, values: vals }),
      })
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => {
          // A slower earlier response must not overwrite a newer one.
          if (seq === requestSeq.current) {
            setResult(data);
            setStale(false);
          }
        })
        .catch(() => {
          // Keep the last good result but mark it as not reflecting the
          // current slider positions.
          if (seq === requestSeq.current) setStale(true);
        });
    },
    [],
  );

  // Load slider config + initialize from current live values.
  useEffect(() => {
    setControls(null);
    setResult(null);
    if (zoneId == null) return;
    fetch(`${API_BASE_URL}/risk/simulate/${zoneId}`)
      .then((res) => res.json())
      .then((ctx) => {
        setControls(ctx.controls);
        const initial = Object.fromEntries(
          ctx.controls.map((c) => [c.sensor_type, c.current_value]),
        );
        setValues(initial);
        runSimulation(zoneId, initial);
      })
      .catch(() => {});
  }, [zoneId, runSimulation]);

  const handleChange = (sensorType, raw) => {
    const next = { ...values, [sensorType]: Number(raw) };
    setValues(next);
    clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(
      () => runSimulation(zoneId, next),
      DEBOUNCE_MS,
    );
  };

  const handleReset = () => {
    if (!controls) return;
    const initial = Object.fromEntries(
      controls.map((c) => [c.sensor_type, c.current_value]),
    );
    setValues(initial);
    runSimulation(zoneId, initial);
  };

  const animatedScore = useAnimatedNumber(result?.risk_score ?? null, zoneId);

  if (!controls) return null;

  const level = result?.risk_level ?? "UNKNOWN";
  // The engine itself decides when readings compound -- the frontend only
  // presents its signal, never re-derives the threshold logic.
  const compoundSignal = result?.contributing_signals?.find((s) =>
    s.description?.startsWith("Compound risk"),
  );
  const elevatedTypes = [
    ...new Set(
      (result?.contributing_signals ?? [])
        .filter((s) => s.source === "rule" && s.sensor_type)
        .map((s) => s.sensor_type),
    ),
  ];
  const multiplierText =
    typeof compoundSignal?.weight_contribution === "string"
      ? compoundSignal.weight_contribution.replace("x multiplier", "×")
      : null;

  return (
    <section className="border-t border-seam pt-3">
      <div className="flex items-baseline justify-between">
        <h3 className="font-mono text-[11px] uppercase tracking-widest text-faint">
          What-if simulation
        </h3>
        <button
          onClick={handleReset}
          className="font-mono text-[11px] text-faint hover:text-ink focus-visible:outline-2 focus-visible:outline-ink"
        >
          reset to live
        </button>
      </div>
      <p className="mt-1 text-xs leading-snug text-muted">
        Drag to test hypothetical readings. Scored by the same engine as the
        live data.
      </p>

      <div className="mt-3 flex flex-col gap-4">
        {controls.map((c) => {
          const value = values[c.sensor_type] ?? c.baseline;
          const fill = ((value - c.min) / (c.max - c.min)) * 100;
          return (
            <div key={c.sensor_type}>
              <div className="flex items-baseline justify-between font-mono text-xs">
                <span className="uppercase tracking-wide text-muted">
                  {c.sensor_type}
                </span>
                <span className="tabular-nums text-ink">
                  {value.toFixed(1)} {c.unit}
                  <span className="ml-2 text-faint">
                    normal ~{c.baseline}
                  </span>
                </span>
              </div>
              <input
                type="range"
                className="wif-slider mt-1.5"
                data-testid={`wif-${c.sensor_type}`}
                min={c.min}
                max={c.max}
                step={c.step}
                value={value}
                style={{ "--fill": `${fill}%` }}
                onChange={(e) => handleChange(c.sensor_type, e.target.value)}
                aria-label={`Simulated ${c.sensor_type} (${c.unit})`}
              />
            </div>
          );
        })}
      </div>

      {result && (
        <>
        <div data-testid="wif-result" className="mt-4 border border-seam bg-panel px-3 py-2">
          <div className="flex items-baseline gap-3">
            <span
              className={`font-mono text-3xl font-semibold tabular-nums transition-colors duration-300 ${RISK_TEXT_CLASS[level]}`}
            >
              {animatedScore != null ? animatedScore.toFixed(1) : "--"}
            </span>
            <span
              className={`font-mono text-xs uppercase tracking-widest ${RISK_TEXT_CLASS[level]}`}
            >
              {RISK_LABEL[level]}
            </span>
          </div>
          <p className="mt-1 font-mono text-[11px] text-faint">
            rules {result.rule_score} · ml {result.ml_score}% compound
            probability
          </p>
          {compoundSignal && (
            <div
              data-testid="wif-compound"
              // Remount on the elevated-type combination so the flash
              // re-fires when the compound composition changes, not just
              // on first detection.
              key={elevatedTypes.join("+")}
              className="compound-flash mt-2 border border-critical/60 px-3 py-2"
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-mono text-xs font-semibold uppercase tracking-widest text-critical">
                  Compound risk detected
                </span>
                <span className="font-mono text-[11px] tabular-nums text-critical">
                  {typeof compoundSignal.weight_contribution === "string"
                    ? compoundSignal.weight_contribution.replace("x multiplier", "×")
                    : ""}
                </span>
              </div>
              <p className="mt-0.5 font-mono text-[11px] leading-snug text-ink/80">
                {elevatedTypes.join(" + ")} elevated simultaneously -- risk
                compounds beyond any single reading.
              </p>
            </div>
          )}
          {stale && (
            <p className="mt-1 font-mono text-[11px] text-warn">
              Simulation request failed -- shown score may not match the
              sliders. Drag again to retry.
            </p>
          )}
        </div>
        <div className="mt-2">
          <RiskComparison
            baseline={result.single_sensor_baseline}
            level={level}
            score={result.risk_score}
            multiplier={multiplierText}
          />
        </div>
        </>
      )}
    </section>
  );
}

export default WhatIfPanel;
