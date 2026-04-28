import { create } from "zustand";

type ActiveModal = "evasion" | "action_detail" | "character_detail" | "settings" | null;
export type CombatResult = "victory" | "defeat" | null;

export interface DamageEvent {
  id: string;
  charId: string;
  amount: number;
  gridX: number;
  gridY: number;
}

interface UIStore {
  mapZoom: number;
  selectedCharId: string | null;
  contextMenuCharId: string | null;
  contextMenuPos: { x: number; y: number } | null;
  activeModal: ActiveModal;
  damageEvents: DamageEvent[];
  combatResult: CombatResult;

  setMapZoom: (zoom: number) => void;
  setSelectedChar: (id: string | null) => void;
  openContextMenu: (charId: string, pos: { x: number; y: number }) => void;
  closeContextMenu: () => void;
  openModal: (modal: ActiveModal) => void;
  closeModal: () => void;
  addDamageEvent: (event: DamageEvent) => void;
  removeDamageEvent: (id: string) => void;
  setCombatResult: (result: CombatResult) => void;
}

export const useUIStore = create<UIStore>()((set) => ({
  mapZoom: 40,
  selectedCharId: null,
  contextMenuCharId: null,
  contextMenuPos: null,
  activeModal: null,
  damageEvents: [],
  combatResult: null,

  setMapZoom: (zoom) => set({ mapZoom: Math.min(64, Math.max(30, zoom)) }),
  setSelectedChar: (id) => set({ selectedCharId: id }),
  openContextMenu: (charId, pos) =>
    set({ contextMenuCharId: charId, contextMenuPos: pos }),
  closeContextMenu: () =>
    set({ contextMenuCharId: null, contextMenuPos: null }),
  openModal: (modal) => set({ activeModal: modal }),
  closeModal: () => set({ activeModal: null }),
  addDamageEvent: (event) =>
    set((s) => ({ damageEvents: [...s.damageEvents, event] })),
  removeDamageEvent: (id) =>
    set((s) => ({ damageEvents: s.damageEvents.filter((e) => e.id !== id) })),
  setCombatResult: (result) => set({ combatResult: result }),
}));
