import { create } from "zustand";
import type { DeathAvoidancePending, EvasionPending } from "../types";

interface PendingStore {
  evasionRequest: EvasionPending | null;
  setEvasionRequest: (req: EvasionPending | null) => void;
  deathAvoidanceRequest: DeathAvoidancePending | null;
  setDeathAvoidanceRequest: (req: DeathAvoidancePending | null) => void;
}

export const usePendingStore = create<PendingStore>()((set) => ({
  evasionRequest: null,
  setEvasionRequest: (req) => set({ evasionRequest: req }),
  deathAvoidanceRequest: null,
  setDeathAvoidanceRequest: (req) => set({ deathAvoidanceRequest: req }),
}));
