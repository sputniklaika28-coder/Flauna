import { create } from "zustand";
import type { TurnAction } from "../types";

interface DraftStore {
  draft: TurnAction | null;
  setDraft: (draft: TurnAction) => void;
  clearDraft: () => void;
}

export const useDraftStore = create<DraftStore>()((set) => ({
  draft: null,
  setDraft: (draft) => set({ draft }),
  clearDraft: () => set({ draft: null }),
}));
