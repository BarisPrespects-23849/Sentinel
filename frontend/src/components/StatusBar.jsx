import { useEffect, useState } from "react";

// Thin control-room status strip: identity, live plant clock (the seeded
// plant is near Bengaluru, so IST), and backend link state.

function AlarmSummary({ plantData }) {
  const features = plantData?.zones?.features ?? [];
  const alarmed = features.filter((f) => (f.properties.risk_score ?? 0) >= 30);
  if (features.length === 0 || alarmed.length === 0) return null;
  const worst = alarmed.reduce((a, b) =>
    (a.properties.risk_score ?? 0) >= (b.properties.risk_score ?? 0) ? a : b,
  );
  const critical = (worst.properties.risk_score ?? 0) >= 85;
  return (
    <span
      className={`border px-2 py-0.5 font-mono text-[11px] uppercase tracking-widest ${
        critical
          ? "alarm-pulse border-critical/60 bg-critical/15 text-critical"
          : "border-warn/60 bg-warn/10 text-warn"
      }`}
    >
      {alarmed.length === 1
        ? `${worst.properties.name}: ${worst.properties.risk_level}`
        : `${alarmed.length} zones need attention`}
    </span>
  );
}

// Operations vs. executive-briefing view switch. Styled as flat mono
// tabs, not pill buttons -- consistent with the annunciator idiom.
function ViewTabs({ view, onViewChange }) {
  const tabs = [
    { id: "operations", label: "Operations" },
    { id: "briefing", label: "Briefing" },
    { id: "coverage", label: "Coverage" },
    { id: "evaluation", label: "Evaluation" },
  ];
  return (
    <nav className="flex items-center gap-1 border border-seam p-0.5">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onViewChange(tab.id)}
          aria-current={view === tab.id ? "page" : undefined}
          className={`px-2.5 py-1 font-mono text-[11px] uppercase tracking-widest ${
            view === tab.id
              ? "bg-seam text-ink"
              : "text-faint hover:text-muted"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}

function StatusBar({ backendStatus, plantData, view, onViewChange }) {
  const [clock, setClock] = useState("");

  useEffect(() => {
    const tick = () =>
      setClock(
        new Intl.DateTimeFormat("en-IN", {
          timeZone: "Asia/Kolkata",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        }).format(new Date()),
      );
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, []);

  const online = backendStatus === "ok";

  return (
    <header className="flex flex-none items-center justify-between border-b border-seam bg-surface px-4 py-2">
      <div className="flex items-baseline gap-3">
        <h1 className="font-display text-2xl font-semibold uppercase tracking-widest text-ink">
          Sentinel
        </h1>
        <span className="hidden font-mono text-[11px] uppercase tracking-widest text-faint sm:inline">
          {view === "briefing" ? "Executive briefing" : "Plant overview"}
        </span>
      </div>
      <ViewTabs view={view} onViewChange={onViewChange} />
      <div className="flex items-center gap-4 font-mono text-xs text-muted">
        <AlarmSummary plantData={plantData} />
        <span className="tabular-nums">{clock} IST</span>
        <span className="flex items-center gap-1.5">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              online ? "bg-normal" : "bg-critical alarm-pulse"
            }`}
          />
          {online ? "link ok" : "link down"}
        </span>
      </div>
    </header>
  );
}

export default StatusBar;
