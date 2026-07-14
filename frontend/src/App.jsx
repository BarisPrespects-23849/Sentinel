import { useCallback, useEffect, useState } from "react";
import StatusBar from "./components/StatusBar";
import ZoneRail from "./components/ZoneRail";
import PlantMap from "./components/PlantMap";
import ZoneDetailPanel from "./components/ZoneDetailPanel";
import BriefingScreen from "./components/BriefingScreen";
import CoverageScreen from "./components/CoverageScreen";
import EvaluationScreen from "./components/EvaluationScreen";
import { API_BASE_URL } from "./api";

const POLL_INTERVAL_MS = 5000;

// ?view=briefing / coverage / evaluation deep-link those screens (also lets
// the Playwright verification script screenshot them directly).
const VIEW_PARAM = new URLSearchParams(window.location.search).get("view");
const initialView = ["briefing", "coverage", "evaluation"].includes(VIEW_PARAM)
  ? VIEW_PARAM
  : "operations";

function App() {
  const [backendStatus, setBackendStatus] = useState("checking");
  const [plantData, setPlantData] = useState(null);
  const [selectedZoneId, setSelectedZoneId] = useState(null);
  const [view, setView] = useState(initialView);

  // One poller feeds both the map and the zone rail. This is the cheap
  // sensor-only score -- the expensive multi-agent path only runs on click.
  useEffect(() => {
    const fetchPlant = () => {
      fetch(`${API_BASE_URL}/geo/plant`)
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => {
          setPlantData(data);
          setBackendStatus("ok");
        })
        .catch(() => setBackendStatus("unreachable"));
    };
    fetchPlant();
    const interval = setInterval(fetchPlant, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  const handleZoneClick = useCallback((zoneId) => {
    setSelectedZoneId((current) => (current === zoneId ? null : zoneId));
  }, []);

  return (
    <div className="flex h-screen w-screen flex-col bg-bg text-ink">
      <StatusBar
        backendStatus={backendStatus}
        plantData={plantData}
        view={view}
        onViewChange={setView}
      />
      {view === "briefing" ? (
        <div className="flex-1 overflow-hidden">
          <BriefingScreen onExit={() => setView("operations")} />
        </div>
      ) : view === "coverage" ? (
        <div className="flex-1 overflow-hidden">
          <CoverageScreen />
        </div>
      ) : view === "evaluation" ? (
        <div className="flex-1 overflow-hidden">
          <EvaluationScreen />
        </div>
      ) : (
        <div className="flex flex-1 overflow-hidden">
          <ZoneRail
            plantData={plantData}
            selectedZoneId={selectedZoneId}
            onSelect={handleZoneClick}
          />
          <main className="relative flex-1">
            <PlantMap
              plantData={plantData}
              selectedZoneId={selectedZoneId}
              onZoneClick={handleZoneClick}
            />
            {backendStatus === "unreachable" && (
              <div className="absolute left-3 top-3 border border-critical/60 bg-critical/15 px-3 py-1.5 font-mono text-xs text-critical">
                Live data unavailable. Check that the backend is running on :8000.
              </div>
            )}
          </main>
          <aside className="w-96 flex-none border-l border-seam bg-surface">
            <ZoneDetailPanel zoneId={selectedZoneId} onClose={() => setSelectedZoneId(null)} />
          </aside>
        </div>
      )}
    </div>
  );
}

export default App;
