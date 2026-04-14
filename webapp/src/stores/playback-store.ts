import { create } from "zustand";

type PlaybackStatus = "idle" | "playing" | "paused" | "finished";

interface PlaybackState {
  status: PlaybackStatus;
  currentTick: number;
  speed: number;
  maxTick: number;

  play: () => void;
  pause: () => void;
  stepForward: () => void;
  stepBackward: () => void;
  setTick: (tick: number) => void;
  setSpeed: (speed: number) => void;
  reset: (maxTick?: number) => void;
  advanceTick: () => void;
}

export const usePlaybackStore = create<PlaybackState>((set, get) => ({
  status: "idle",
  currentTick: 0,
  speed: 5,
  maxTick: 0,

  play: () => {
    const { status, currentTick, maxTick } = get();
    if (maxTick === 0) return;
    if (status === "finished") {
      set({ currentTick: 0, status: "playing" });
    } else if (currentTick >= maxTick) {
      set({ currentTick: 0, status: "playing" });
    } else {
      set({ status: "playing" });
    }
  },

  pause: () => set({ status: "paused" }),

  stepForward: () => {
    const { currentTick, maxTick } = get();
    if (currentTick < maxTick) {
      set({ currentTick: currentTick + 1, status: "paused" });
    }
  },

  stepBackward: () => {
    const { currentTick } = get();
    if (currentTick > 0) {
      set({ currentTick: currentTick - 1, status: "paused" });
    }
  },

  setTick: (tick: number) => {
    const { maxTick } = get();
    set({
      currentTick: Math.max(0, Math.min(tick, maxTick)),
      status: "paused",
    });
  },

  setSpeed: (speed: number) => set({ speed }),

  reset: (maxTick?: number) => {
    set({
      status: "idle",
      currentTick: 0,
      maxTick: maxTick ?? get().maxTick,
    });
  },

  advanceTick: () => {
    const { currentTick, maxTick } = get();
    if (currentTick >= maxTick) {
      set({ status: "finished" });
    } else {
      set({ currentTick: currentTick + 1 });
    }
  },
}));
