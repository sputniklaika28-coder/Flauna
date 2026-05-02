import { create } from "zustand";

export type ToastSeverity = "info" | "warn" | "error";

export interface Toast {
  id: string;
  message: string;
  severity: ToastSeverity;
}

interface ToastStore {
  toasts: Toast[];
  pushToast: (toast: Omit<Toast, "id"> & { id?: string }) => string;
  dismissToast: (id: string) => void;
  clearToasts: () => void;
}

let counter = 0;
function nextId(): string {
  counter += 1;
  return `t${Date.now().toString(36)}-${counter}`;
}

export const useToastStore = create<ToastStore>()((set) => ({
  toasts: [],
  pushToast: (toast) => {
    const id = toast.id ?? nextId();
    set((s) => ({ toasts: [...s.toasts, { ...toast, id }] }));
    return id;
  },
  dismissToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
  clearToasts: () => set({ toasts: [] }),
}));
