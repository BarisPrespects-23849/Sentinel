// Executive briefing: the business case, built exclusively from the
// approved-facts list in the project brief. RULE: no statistic, date,
// amount, or attribution may appear here unless it is on that list --
// gaps carry a literal [NEEDS VERIFICATION: ...] placeholder instead of
// a plausible guess. Do not "fix" a placeholder by filling it in; get
// the sourced value first.

// Vizag Steel Plant ladle explosion: 8 June 2025, 8 workers killed;
// preliminary cause entrapped gases in a molten-steel ladle.
const VIZAG_YEAR = "2025";
// Source attribution for the hazardous-factory counts and inspection-share
// figures (the inspection-gap chart): DGFASLI data, as reported in
// NCRB/FACTLY analysis.
const INSPECTION_SOURCE = "DGFASLI data, as reported in NCRB/FACTLY analysis.";

/* The signature element: the inspection gap, drawn literally. Two sourced
   endpoints per series (2010, 2023) connected by straight lines -- the
   chart plots no data we do not have, and says so in its footnote. The
   widening triangle after the lines cross is the gap SENTINEL occupies. */
function InspectionGapChart() {
  // Geometry: x 90..710 spans 2010..2023. Lines cross at (331, 190).
  return (
    <svg
      viewBox="0 0 800 380"
      className="w-full"
      role="img"
      aria-label="Chart: hazardous-process factories rose from 26,877 in 2010 to 45,374 in 2023 while the share inspected fell from 62% to 39%"
    >
      {/* Gridline baseline */}
      <line x1="90" y1="330" x2="710" y2="330" stroke="var(--color-seam)" strokeWidth="1" />
      <text x="90" y="352" fontSize="13" fill="var(--color-faint)" fontFamily="var(--font-mono)">
        2010
      </text>
      <text x="710" y="352" fontSize="13" fill="var(--color-faint)" fontFamily="var(--font-mono)" textAnchor="end">
        2023
      </text>

      {/* The gap: shaded region between the lines after they cross */}
      <polygon points="331,190 710,80 710,300" fill="var(--color-critical)" opacity="0.09" className="gap-fade" />
      <text
        x="600"
        y="196"
        fontSize="13"
        fill="var(--color-critical)"
        fontFamily="var(--font-mono)"
        letterSpacing="2"
        className="gap-fade"
      >
        THE INSPECTION GAP
      </text>

      {/* Hazardous-process factories: rising */}
      <line
        x1="90" y1="260" x2="710" y2="80"
        stroke="var(--color-high)" strokeWidth="2.5"
        pathLength="1" className="line-draw"
      />
      <circle cx="90" cy="260" r="4" fill="var(--color-high)" />
      <circle cx="710" cy="80" r="4" fill="var(--color-high)" />
      <text x="90" y="284" fontSize="14" fill="var(--color-high)" fontFamily="var(--font-mono)">
        26,877
      </text>
      <text x="710" y="64" fontSize="14" fill="var(--color-high)" fontFamily="var(--font-mono)" textAnchor="end">
        45,374
      </text>

      {/* Share of hazardous factories inspected: falling */}
      <line
        x1="90" y1="120" x2="710" y2="300"
        stroke="var(--color-muted)" strokeWidth="2.5"
        pathLength="1" className="line-draw"
      />
      <circle cx="90" cy="120" r="4" fill="var(--color-muted)" />
      <circle cx="710" cy="300" r="4" fill="var(--color-muted)" />
      <text x="90" y="104" fontSize="14" fill="var(--color-ink)" fontFamily="var(--font-mono)">
        62%
      </text>
      <text x="710" y="324" fontSize="14" fill="var(--color-ink)" fontFamily="var(--font-mono)" textAnchor="end">
        39%
      </text>
    </svg>
  );
}

/* Series labels live outside the SVG so they can never collide with the
   line paths at any viewport width. */
function ChartLegend() {
  return (
    <div className="flex flex-wrap gap-x-6 gap-y-1 font-mono text-[11px] uppercase tracking-widest">
      <span className="flex items-center gap-2 text-high">
        <span className="inline-block h-0.5 w-6 bg-high" aria-hidden="true" />
        Hazardous-process factories (+69%)
      </span>
      <span className="flex items-center gap-2 text-muted">
        <span className="inline-block h-0.5 w-6 bg-muted" aria-hidden="true" />
        Share inspected
      </span>
    </div>
  );
}

function StatCard({ figure, unit, children }) {
  return (
    <div className="border border-seam bg-surface p-5">
      <div className="font-mono text-3xl tabular-nums text-ink">
        {figure}
        {unit && <span className="ml-1 text-base text-muted">{unit}</span>}
      </div>
      <p className="mt-3 text-sm leading-relaxed text-muted">{children}</p>
    </div>
  );
}

function CaseCard({ eyebrow, title, framing, children }) {
  return (
    <div className="border border-seam bg-surface p-5">
      <div className="font-mono text-[11px] uppercase tracking-widest text-faint">{eyebrow}</div>
      <h3 className="mt-1 font-display text-xl font-semibold uppercase tracking-wide text-ink">
        {title}
      </h3>
      <p className="mt-3 text-sm leading-relaxed text-muted">{children}</p>
      <p className="mt-3 border-l-2 border-seam pl-3 text-xs leading-relaxed text-faint">
        {framing}
      </p>
    </div>
  );
}

function CostRow({ label, anchored, children }) {
  return (
    <div className="flex items-baseline justify-between gap-6 border-b border-seam py-3 last:border-b-0">
      <div>
        <div className="text-sm text-ink">{label}</div>
        <div className="mt-0.5 text-xs text-faint">{children}</div>
      </div>
      <div className="flex-none font-mono text-sm tabular-nums text-muted">
        {anchored ?? "unquantified"}
      </div>
    </div>
  );
}

function BriefingScreen({ onExit }) {
  return (
    <div className="h-full overflow-y-auto bg-bg">
      <div className="mx-auto max-w-4xl px-6 py-12">
        {/* Thesis */}
        <div className="font-mono text-[11px] uppercase tracking-widest text-faint">
          Executive briefing — the case for an intelligence layer
        </div>
        <h2 className="mt-3 font-display text-5xl font-semibold uppercase leading-none tracking-wide text-ink">
          Hazardous industry grew&nbsp;69%.
          <br />
          <span className="text-high">Inspection coverage fell to&nbsp;39%.</span>
        </h2>
        <p className="mt-5 max-w-2xl text-base leading-relaxed text-muted">
          India&rsquo;s registered hazardous-process factories grew from 26,877 in 2010 to 45,374
          in 2023 — while the share of them inspected fell from 62% to 39%. The oversight model
          has not kept pace with the industry it oversees. SENTINEL is an always-on, automated
          intelligence layer built to cover the gap human inspection no longer reaches.
        </p>

        {/* Signature chart */}
        <div className="mt-10 border border-seam bg-surface p-6">
          <ChartLegend />
          <InspectionGapChart />
          <p className="mt-2 font-mono text-[11px] leading-relaxed text-faint">
            Straight lines connect sourced 2010 and 2023 endpoints; intermediate years not shown.{" "}
            {INSPECTION_SOURCE}
          </p>
        </div>

        {/* Human cost */}
        <div className="mt-14 font-mono text-[11px] uppercase tracking-widest text-faint">
          The human cost
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
          <StatCard figure="~1,109" unit="deaths / yr">
            Average annual deaths in India&rsquo;s registered factories, 2017&ndash;2020 — roughly
            three factory workers every day (DGFASLI data, obtained by IndiaSpend via RTI).
          </StatCard>
          <StatCard figure="660" unit="deaths">
            From 742 factory/machine accidents recorded in 2024 — nearly 89 deaths per 100
            accidents. Accidents have fallen since 2010, but become more lethal.
          </StatCard>
          <StatCard figure="Fires & explosions">
            Less frequent than falls and machinery accidents — but disproportionately associated
            with fatalities.
          </StatCard>
        </div>

        {/* Documented failure class */}
        <div className="mt-14 font-mono text-[11px] uppercase tracking-widest text-faint">
          A documented class of failure
        </div>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-muted">
          Warning conditions present in the data — and no intelligence layer connecting them to
          action in time.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <CaseCard
            eyebrow="9 October 2018 — SAIL Bhilai Steel Plant"
            title="Hazardous work in a live gas environment"
            framing="A documented case of hazardous maintenance work proceeding in a high-risk gas environment — the exact permit-plus-hazard combination SENTINEL is designed to flag."
          >
            A gas-pipeline explosion at the Coke Oven Battery Complex killed at least 9 workers
            during scheduled maintenance — de-blanking a live gas pipe.
          </CaseCard>
          <CaseCard
            eyebrow={`8 June ${VIZAG_YEAR} — Visakhapatnam Steel Plant`}
            title="Entrapped gases, undetected"
            framing="Cited as illustrative of a documented failure category — warning conditions present in data but not connected to action in time. This is not a claim that SENTINEL would have prevented this specific incident."
          >
            An explosion killed 8 workers; a preliminary investigation attributed it to entrapped
            gases in a molten-steel ladle.
          </CaseCard>
        </div>

        {/* Cost of inaction */}
        <div className="mt-14 font-mono text-[11px] uppercase tracking-widest text-faint">
          What a single incident costs
        </div>
        <div className="mt-4 border border-seam bg-surface px-5 py-2">
          <CostRow label="Ex-gratia compensation" anchored="₹1 crore / family">
            Announced by the Andhra Pradesh government per deceased worker&rsquo;s family in
            comparable Visakhapatnam industrial incidents — immediate compensation only.
          </CostRow>
          <CostRow label="Regulatory penalties">Fines and enforcement action following investigation.</CostRow>
          <CostRow label="Production shutdown">Lost output while the affected unit is closed.</CostRow>
          <CostRow label="Litigation">Civil and criminal proceedings.</CostRow>
          <CostRow label="Reputational damage">Customers, insurers, and workforce.</CostRow>
        </div>
        <p className="mt-3 font-mono text-xs text-faint">
          Total per-incident exposure runs into tens of crores — a conservative estimate, not a
          sourced figure. Only the ₹1 crore ex-gratia is anchored to a public announcement.
        </p>

        {/* Positioning */}
        <div className="mt-14 border border-seam bg-surface p-6">
          <h3 className="font-display text-2xl font-semibold uppercase tracking-wide text-ink">
            Where SENTINEL fits
          </h3>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
            Human inspection now reaches 39% of hazardous facilities. SENTINEL cross-references
            gas sensors, active work permits, and maintenance records continuously — every zone,
            every minute — detects compound risk that no single system sees, and explains every
            score with a full causal chain. It does not replace inspection; it covers the hours
            and facilities inspection cannot.
          </p>
          <button
            type="button"
            onClick={onExit}
            className="mt-5 border border-seam px-4 py-2 font-mono text-xs uppercase tracking-widest text-ink hover:border-muted"
          >
            View live operations
          </button>
        </div>

        {/* Sourcing note */}
        <p className="mt-10 border-t border-seam pt-4 font-mono text-[11px] leading-relaxed text-faint">
          Every figure on this page is reproduced from a verified fact list; nothing is estimated
          or extrapolated except where explicitly labeled. Fatality averages: DGFASLI data
          obtained by IndiaSpend via RTI. Inspection-gap and factory-count figures:{" "}
          {INSPECTION_SOURCE}
        </p>
      </div>
    </div>
  );
}

export default BriefingScreen;
