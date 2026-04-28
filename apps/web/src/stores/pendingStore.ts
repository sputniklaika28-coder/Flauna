import { create } from "zustand";
import type { EvasionPending } from "../types";

interface PendingStore {
  evasionRequest: EvasionPending | null;
  setEvasionRequest: (req: EvasionPending | null) => void;
}

export const usePendingStore = create<PendingStore>()((set) => ({
  evasionRequest: null,
  setEvasionRequest: (req) => set({ evasionRequest: req }),
}));
