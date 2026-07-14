import { useRef, useState } from "react";
import { API_BASE_URL } from "../api";

// Demo scenario controls: inject a scripted gas+temperature compound-risk
// event into the live simulator, or command everything back to calm. Lives
// at the bottom of the zone rail, styled as a maintenance-panel utility --
// present for the operator (and the judge), but visually subordinate to
// the live alarm surfaces above it.

function DemoControls({ selectedZoneId }) {
  const [status, setStatus] = useState(null); // { kind: "ok" | "error", text }
  const [busy, setBusy] = useState(false);
  const clearTimer = useRef(null);

  const send = async (body, okText) => {
    setBusy(true);
    clearTimeout(clearTimer.current);
    try {
      const res = await fetch(`${API_BASE_URL}/demo/scenario`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`);
      setStatus({ kind: "ok", text: okText });
    } catch (err) {
      setStatus({ kind: "error", text: err.message });
    } finally {
      setBusy(false);
      clearTimer.current = setTimeout(() => setStatus(null), 8000);
    }
  };

  return (
    <div className="border-t border-seam px-4 py-3">
      <div className="font-mono text-[11px] uppercase tracking-widest text-faint">
        Demo scenario
      </div>
      <div className="mt-2 flex gap-2">
        <button
          type="button"
          disabled={busy || selectedZoneId == null}
          onClick={() =>
            send(
              { scenario: "compound", zone_id: selectedZoneId },
              "Compound event injected -- risk ramps over ~30s.",
            )
          }
          className="flex-1 border border-seam px-2 py-1.5 font-mono text-[11px] uppercase tracking-wider text-ink hover:border-high hover:text-high disabled:cursor-not-allowed disabled:text-faint disabled:hover:border-seam"
          data-testid="demo-compound"
        >
          Inject compound
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() =>
            send({ scenario: "calm" }, "Reset sent -- scores settle within ~60s.")
          }
          className="flex-1 border border-seam px-2 py-1.5 font-mono text-[11px] uppercase tracking-wider text-muted hover:border-muted hover:text-ink disabled:cursor-not-allowed disabled:text-faint"
          data-testid="demo-calm"
        >
          Reset to calm
        </button>
      </div>
      <p
        className={`mt-2 min-h-4 font-mono text-[11px] leading-snug ${
          status?.kind === "error" ? "text-critical" : "text-faint"
        }`}
        data-testid="demo-status"
      >
        {status?.text ??
          (selectedZoneId == null ? "Select a zone to enable injection." : "")}
      </p>
    </div>
  );
}

export default DemoControls;
