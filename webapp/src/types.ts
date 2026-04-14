// === Raw log shapes (parsed from JSONL) ===

export interface ElevatorEntry {
  tick: number;
  car_id: string;
  floor: number;
  direction: "up" | "down" | "idle";
  passenger_count: number;
}

export interface PassengerEntry {
  id: string;
  source: number;
  dest: number;
  request_tick: number;
  pickup_tick: number;
  dropoff_tick: number;
  car_id: string;
}

export interface DispatchEntry {
  tick: number;
  passenger_id: string;
  car_id: string;
  scores?: Record<string, number>;
}

export interface Manifest {
  timestamp: string;
  commit: string;
  config: {
    floors: number;
    elevators: number;
    capacity: number;
    workloads: string[];
    algorithms: string[];
    passengers: number;
    seed: number;
    max_ticks: number;
  };
}

// === Indexed / pre-computed structures ===

export interface CarState {
  car_id: string;
  floor: number;
  direction: "up" | "down" | "idle";
  passenger_count: number;
}

export interface TickStats {
  served: number;
  waiting: number;
  inTransit: number;
  totalPassengers: number;
  waitMean: number;
  waitP95: number;
  waitMin: number;
  waitMax: number;
  totalMean: number;
  totalP95: number;
  totalMin: number;
  totalMax: number;
  carOccupancy: number[];
  pickupsInWindow: number;
  dropoffsInWindow: number;
}

export interface TickSnapshot {
  tick: number;
  cars: CarState[];
  waitingByFloor: Map<number, number>;
  stats: TickStats;
}

export interface ScenarioData {
  manifest: Manifest;
  passengers: PassengerEntry[];
  dispatches: DispatchEntry[];
  maxTick: number;
  carIds: string[];
  tickSnapshots: TickSnapshot[];
}

// === Run listing ===

export interface RunInfo {
  name: string;
  manifest: Manifest;
}
