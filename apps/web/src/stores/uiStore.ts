import { create } from "zustand";

type ActiveModal = "evasion" | "action_detail" | "character_detail" | "settings" | null;

interface UIStore {
  mapZoom: number;
  selectedCharId: string | null;
  contextMenuCharId: string | null;
  contextMenuPos: { x: number; y: number } | null;
  activeModal: ActiveModal;

  setMapZoom: (zoom: number) => void;
  setSelectedChar: (id: string | null) => void;
  openContextMenu: (charId: string, pos: { x: number; y: number }) => void;
  closeContextMenu: () => void;
  openModal: (modal: ActiveModal) => void;
  closeModal: () => void;
}

export const useUIStore = create<UIStore>()((set) => ({
  mapZoom: 40,
  selectedCharId: null,
  contextMenuCharId: null,
  contextMenuPos: null,
  activeModal: null,

  setMapZoom: (zoom) => set({ mapZoom: Math.min(64, Math.max(30, zoom)) }),
  setSelectedChar: (id) => set({ selectedCharId: id }),
  openContextMenu: (charId, pos) =>
    set({ contextMenuCharId: charId, contextMenuPos: pos }),
  closeContextMenu: () =>
    set({ contextMenuCharId: null, contextMenuPos: null }),
  openModal: (modal) => set({ activeModal: modal }),
  closeModal: () => set({ activeModal: null }),
}));
