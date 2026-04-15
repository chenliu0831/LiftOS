import type {
  Manifest,
  RunInfo,
  ElevatorEntry,
  PassengerEntry,
  DispatchEntry,
} from "../types";

function parseJsonl<T>(text: string): T[] {
  const trimmed = text.trim();
  if (!trimmed) return [];
  return trimmed.split("\n").map((line) => JSON.parse(line) as T);
}

// In dev mode the Vite plugin serves /api/runs from the local filesystem.
// In production (static build) data lives under <base>/data/.
const isDev = import.meta.env.DEV;

function runsUrl(): string {
  return isDev ? "/api/runs" : `${import.meta.env.BASE_URL}data/runs.json`;
}

function runFileUrl(run: string, ...parts: string[]): string {
  const joined = [run, ...parts].join("/");
  return isDev
    ? `/api/runs/${joined}`
    : `${import.meta.env.BASE_URL}data/${joined}`;
}

export async function fetchRunList(): Promise<RunInfo[]> {
  const res = await fetch(runsUrl());
  const names: string[] = await res.json();

  const runs = await Promise.all(
    names.map(async (name) => {
      try {
        const mRes = await fetch(runFileUrl(name, "manifest.json"));
        if (!mRes.ok) return null;
        const manifest: Manifest = await mRes.json();
        return { name, manifest } satisfies RunInfo;
      } catch {
        return null;
      }
    }),
  );

  return runs.filter((r): r is RunInfo => r !== null);
}

export async function fetchScenarioRaw(
  run: string,
  workload: string,
  algorithm: string,
): Promise<{
  manifest: Manifest;
  elevatorEntries: ElevatorEntry[];
  passengerEntries: PassengerEntry[];
  dispatchEntries: DispatchEntry[];
}> {
  const dir = `${workload}/${algorithm}`;

  const [manifestRes, elevatorRes, passengerRes, dispatchRes] =
    await Promise.all([
      fetch(runFileUrl(run, "manifest.json")),
      fetch(runFileUrl(run, dir, "elevator_log.jsonl")),
      fetch(runFileUrl(run, dir, "passenger_log.jsonl")),
      fetch(runFileUrl(run, dir, "dispatch_log.jsonl")),
    ]);

  const [manifest, elevatorText, passengerText, dispatchText] =
    await Promise.all([
      manifestRes.json() as Promise<Manifest>,
      elevatorRes.text(),
      passengerRes.text(),
      dispatchRes.text(),
    ]);

  return {
    manifest,
    elevatorEntries: parseJsonl<ElevatorEntry>(elevatorText),
    passengerEntries: parseJsonl<PassengerEntry>(passengerText),
    dispatchEntries: parseJsonl<DispatchEntry>(dispatchText),
  };
}
