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

export async function fetchRunList(): Promise<RunInfo[]> {
  const res = await fetch("/api/runs");
  const names: string[] = await res.json();

  const runs = await Promise.all(
    names.map(async (name) => {
      try {
        const mRes = await fetch(`/api/runs/${name}/manifest.json`);
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
  const base = `/api/runs/${run}`;
  const dir = `${base}/${workload}/${algorithm}`;

  const [manifestRes, elevatorRes, passengerRes, dispatchRes] =
    await Promise.all([
      fetch(`${base}/manifest.json`),
      fetch(`${dir}/elevator_log.jsonl`),
      fetch(`${dir}/passenger_log.jsonl`),
      fetch(`${dir}/dispatch_log.jsonl`),
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
