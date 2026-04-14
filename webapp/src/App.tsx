import { useEffect } from "react";
import { useDataStore } from "./stores/data-store";
import { BuildingView } from "./components/BuildingView";
import { ChartsPanel } from "./components/ChartsPanel";
import { StatsBar } from "./components/StatsBar";
import { PlaybackControls } from "./components/PlaybackControls";

function RunSelector() {
  const runs = useDataStore((s) => s.runs);
  const selectedRun = useDataStore((s) => s.selectedRun);
  const selectedWorkload = useDataStore((s) => s.selectedWorkload);
  const selectedAlgorithm = useDataStore((s) => s.selectedAlgorithm);
  const selectRun = useDataStore((s) => s.selectRun);
  const selectWorkload = useDataStore((s) => s.selectWorkload);
  const selectAlgorithm = useDataStore((s) => s.selectAlgorithm);

  const currentRun = runs.find((r) => r.name === selectedRun);
  const workloads = currentRun?.manifest.config.workloads ?? [];
  const algorithms = currentRun?.manifest.config.algorithms ?? [];

  return (
    <div className="run-selector">
      <select
        value={selectedRun ?? ""}
        onChange={(e) => selectRun(e.target.value)}
      >
        {runs.map((r) => (
          <option key={r.name} value={r.name}>
            {r.name.replace("run_", "")}
          </option>
        ))}
      </select>
      <select
        value={selectedWorkload ?? ""}
        onChange={(e) => selectWorkload(e.target.value)}
      >
        {workloads.map((w) => (
          <option key={w} value={w}>
            {w}
          </option>
        ))}
      </select>
      <select
        value={selectedAlgorithm ?? ""}
        onChange={(e) => selectAlgorithm(e.target.value)}
      >
        {algorithms.map((a) => (
          <option key={a} value={a}>
            {a}
          </option>
        ))}
      </select>
    </div>
  );
}

export function App() {
  const fetchRuns = useDataStore((s) => s.fetchRuns);
  const loadingScenario = useDataStore((s) => s.loadingScenario);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  return (
    <div className="app-layout">
      <div className="app-topbar">
        <span className="app-title">LiftOS Sim</span>
        <RunSelector />
      </div>
      <StatsBar />
      <div className="app-body">
        <div className="app-building">
          {loadingScenario ? (
            <div className="loading">Loading...</div>
          ) : (
            <BuildingView />
          )}
        </div>
        <div className="app-charts">
          <ChartsPanel />
        </div>
      </div>
      <PlaybackControls />
    </div>
  );
}
