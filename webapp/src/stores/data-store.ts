import { create } from "zustand";
import type { RunInfo, ScenarioData } from "../types";
import { fetchRunList, fetchScenarioRaw } from "../data/loader";
import { buildScenarioData } from "../data/indexer";
import { usePlaybackStore } from "./playback-store";

interface DataState {
  runs: RunInfo[];
  loadingRuns: boolean;
  selectedRun: string | null;
  selectedWorkload: string | null;
  selectedAlgorithm: string | null;
  scenario: ScenarioData | null;
  loadingScenario: boolean;

  fetchRuns: () => Promise<void>;
  selectRun: (run: string) => void;
  selectWorkload: (workload: string) => void;
  selectAlgorithm: (algorithm: string) => void;
  loadScenario: () => Promise<void>;
}

export const useDataStore = create<DataState>((set, get) => ({
  runs: [],
  loadingRuns: false,
  selectedRun: null,
  selectedWorkload: null,
  selectedAlgorithm: null,
  scenario: null,
  loadingScenario: false,

  fetchRuns: async () => {
    set({ loadingRuns: true });
    const runs = await fetchRunList();
    set({ runs, loadingRuns: false });

    // Auto-select first run
    if (runs.length > 0) {
      get().selectRun(runs[0]!.name);
    }
  },

  selectRun: (run: string) => {
    const info = get().runs.find((r) => r.name === run);
    if (!info) return;
    const workloads = info.manifest.config.workloads;
    const algorithms = info.manifest.config.algorithms;
    set({
      selectedRun: run,
      selectedWorkload: workloads[0] ?? null,
      selectedAlgorithm: algorithms[0] ?? null,
    });
    get().loadScenario();
  },

  selectWorkload: (workload: string) => {
    set({ selectedWorkload: workload });
    get().loadScenario();
  },

  selectAlgorithm: (algorithm: string) => {
    set({ selectedAlgorithm: algorithm });
    get().loadScenario();
  },

  loadScenario: async () => {
    const { selectedRun, selectedWorkload, selectedAlgorithm } = get();
    if (!selectedRun || !selectedWorkload || !selectedAlgorithm) return;

    set({ loadingScenario: true });
    try {
      const raw = await fetchScenarioRaw(
        selectedRun,
        selectedWorkload,
        selectedAlgorithm,
      );
      const scenario = buildScenarioData(
        raw.manifest,
        raw.elevatorEntries,
        raw.passengerEntries,
        raw.dispatchEntries,
      );
      set({ scenario, loadingScenario: false });
      usePlaybackStore.getState().reset(scenario.maxTick);
    } catch (e) {
      console.error("Failed to load scenario:", e);
      set({ loadingScenario: false });
    }
  },
}));
