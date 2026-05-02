import { create } from "zustand";
import type { DeathAvoidancePending, EvasionPending } from "../types";

interface PendingStore {
  evasionRequest: EvasionPending | null;
  setEvasionRequest: (req: EvasionPending | null) => void;
  deathAvoidanceRequest: DeathAvoidancePending | null;
  setDeathAvoidanceRequest: (req: DeathAvoidancePending | null) => void;
  // Spec §6-4: 楽観的UI更新の方針 — submit_turn_action 在中の送信中インジケータ。
  // サーバー応答 (state_full または非リトライ系 error) を受けるまで true。
  submittingTurnAction: boolean;
  setSubmittingTurnAction: (v: boolean) => void;
}

export const usePendingStore = create<PendingStore>()((set) => ({
  evasionRequest: null,
  setEvasionRequest: (req) => set({ evasionRequest: req }),
  deathAvoidanceRequest: null,
  setDeathAvoidanceRequest: (req) => set({ deathAvoidanceRequest: req }),
  submittingTurnAction: false,
  setSubmittingTurnAction: (v) => set({ submittingTurnAction: v }),
}));
