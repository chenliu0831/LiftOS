import type {
  Manifest,
  ElevatorEntry,
  PassengerEntry,
  DispatchEntry,
  CarState,
  TickSnapshot,
  TickStats,
  ScenarioData,
} from "../types";

function insortRight(arr: number[], val: number): void {
  let lo = 0;
  let hi = arr.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (arr[mid]! <= val) lo = mid + 1;
    else hi = mid;
  }
  arr.splice(lo, 0, val);
}

function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0;
  const idx = Math.min(
    Math.floor(sorted.length * p),
    sorted.length - 1,
  );
  return sorted[idx]!;
}

function mean(arr: number[]): number {
  if (arr.length === 0) return 0;
  let sum = 0;
  for (const v of arr) sum += v;
  return sum / arr.length;
}

export function buildScenarioData(
  manifest: Manifest,
  elevatorEntries: ElevatorEntry[],
  passengers: PassengerEntry[],
  dispatches: DispatchEntry[],
): ScenarioData {
  // Step 1: Index elevator entries by tick, de-duplicate per (tick, car_id)
  const byTick = new Map<number, Map<string, CarState>>();
  let maxTick = 0;
  const carIdSet = new Set<string>();

  for (const e of elevatorEntries) {
    if (!byTick.has(e.tick)) byTick.set(e.tick, new Map());
    byTick.get(e.tick)!.set(e.car_id, {
      car_id: e.car_id,
      floor: e.floor,
      direction: e.direction,
      passenger_count: e.passenger_count,
    });
    carIdSet.add(e.car_id);
    if (e.tick > maxTick) maxTick = e.tick;
  }

  const carIds = [...carIdSet].sort();

  const elevatorByTick = new Map<number, CarState[]>();
  for (const [tick, carMap] of byTick) {
    elevatorByTick.set(
      tick,
      carIds.map(
        (id) =>
          carMap.get(id) ?? {
            car_id: id,
            floor: 1,
            direction: "idle" as const,
            passenger_count: 0,
          },
      ),
    );
  }

  // Step 2: Index passengers by event tick
  const requestsByTick = new Map<number, PassengerEntry[]>();
  const pickupsByTick = new Map<number, PassengerEntry[]>();
  const dropoffsByTick = new Map<number, PassengerEntry[]>();

  for (const p of passengers) {
    if (!requestsByTick.has(p.request_tick))
      requestsByTick.set(p.request_tick, []);
    requestsByTick.get(p.request_tick)!.push(p);

    if (!pickupsByTick.has(p.pickup_tick))
      pickupsByTick.set(p.pickup_tick, []);
    pickupsByTick.get(p.pickup_tick)!.push(p);

    if (!dropoffsByTick.has(p.dropoff_tick))
      dropoffsByTick.set(p.dropoff_tick, []);
    dropoffsByTick.get(p.dropoff_tick)!.push(p);
  }

  // Step 3: Single forward pass — build TickSnapshot[]
  const tickSnapshots: TickSnapshot[] = [];
  let served = 0;
  let waiting = 0;
  let inTransit = 0;
  let totalPassengers = 0;

  const completedWaits: number[] = [];
  const completedTotals: number[] = [];
  const waitingByFloor = new Map<number, number>();

  // Sliding window counters
  const WINDOW = 20;
  const pickupCounts = new Array<number>(maxTick + 1).fill(0);
  const dropoffCounts = new Array<number>(maxTick + 1).fill(0);

  // Pre-fill per-tick event counts for sliding window
  for (const p of passengers) {
    if (p.pickup_tick <= maxTick) pickupCounts[p.pickup_tick]!++;
    if (p.dropoff_tick <= maxTick) dropoffCounts[p.dropoff_tick]!++;
  }

  let pickupsInWindow = 0;
  let dropoffsInWindow = 0;

  // Default car states for tick 0
  const defaultCars: CarState[] = carIds.map((id) => ({
    car_id: id,
    floor: 1,
    direction: "idle" as const,
    passenger_count: 0,
  }));
  let lastCars = defaultCars;

  for (let tick = 0; tick <= maxTick; tick++) {
    // Requests arriving
    const newRequests = requestsByTick.get(tick);
    if (newRequests) {
      for (const p of newRequests) {
        waiting++;
        totalPassengers++;
        waitingByFloor.set(p.source, (waitingByFloor.get(p.source) ?? 0) + 1);
      }
    }

    // Pickups
    const newPickups = pickupsByTick.get(tick);
    if (newPickups) {
      for (const p of newPickups) {
        waiting--;
        inTransit++;
        const cur = waitingByFloor.get(p.source) ?? 1;
        if (cur <= 1) waitingByFloor.delete(p.source);
        else waitingByFloor.set(p.source, cur - 1);
      }
    }

    // Dropoffs
    const newDropoffs = dropoffsByTick.get(tick);
    if (newDropoffs) {
      for (const p of newDropoffs) {
        inTransit--;
        served++;
        insortRight(completedWaits, p.pickup_tick - p.request_tick);
        insortRight(completedTotals, p.dropoff_tick - p.request_tick);
      }
    }

    // Sliding window throughput
    pickupsInWindow += pickupCounts[tick]!;
    dropoffsInWindow += dropoffCounts[tick]!;
    if (tick >= WINDOW) {
      pickupsInWindow -= pickupCounts[tick - WINDOW]!;
      dropoffsInWindow -= dropoffCounts[tick - WINDOW]!;
    }

    // Car states
    const cars = elevatorByTick.get(tick) ?? lastCars;
    lastCars = cars;

    const stats: TickStats = {
      served,
      waiting,
      inTransit,
      totalPassengers,
      waitMean: mean(completedWaits),
      waitP95: percentile(completedWaits, 0.95),
      waitMin: completedWaits.length > 0 ? completedWaits[0]! : 0,
      waitMax:
        completedWaits.length > 0
          ? completedWaits[completedWaits.length - 1]!
          : 0,
      totalMean: mean(completedTotals),
      totalP95: percentile(completedTotals, 0.95),
      totalMin: completedTotals.length > 0 ? completedTotals[0]! : 0,
      totalMax:
        completedTotals.length > 0
          ? completedTotals[completedTotals.length - 1]!
          : 0,
      carOccupancy: cars.map((c) => c.passenger_count),
      pickupsInWindow,
      dropoffsInWindow,
    };

    tickSnapshots.push({
      tick,
      cars,
      waitingByFloor: new Map(waitingByFloor),
      stats,
    });
  }

  return {
    manifest,
    passengers,
    dispatches,
    maxTick,
    carIds,
    tickSnapshots,
  };
}
