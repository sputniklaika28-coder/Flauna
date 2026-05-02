import { useEffect } from "react";
import { useToastStore } from "../../stores";
import type { Toast } from "../../stores";

const SEVERITY_CLASSES: Record<Toast["severity"], string> = {
  info: "bg-gray-800 border-gray-600 text-gray-100",
  warn: "bg-amber-900 border-amber-600 text-amber-100",
  error: "bg-red-900 border-red-600 text-red-100",
};

const AUTO_DISMISS_MS = 4000;

interface ToastItemProps {
  toast: Toast;
}

function ToastItem({ toast }: ToastItemProps) {
  const dismissToast = useToastStore((s) => s.dismissToast);

  useEffect(() => {
    const t = setTimeout(() => dismissToast(toast.id), AUTO_DISMISS_MS);
    return () => clearTimeout(t);
  }, [toast.id, dismissToast]);

  return (
    <div
      role="status"
      data-testid={`toast-${toast.severity}`}
      className={`pointer-events-auto rounded border px-4 py-2 text-sm shadow-lg flex items-start gap-2 ${SEVERITY_CLASSES[toast.severity]}`}
    >
      <span className="flex-1 whitespace-pre-line">{toast.message}</span>
      <button
        type="button"
        onClick={() => dismissToast(toast.id)}
        aria-label="dismiss"
        className="opacity-60 hover:opacity-100"
      >
        ×
      </button>
    </div>
  );
}

export default function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);

  if (toasts.length === 0) return null;

  return (
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-80 max-w-[90vw]"
      data-testid="toast-container"
    >
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} />
      ))}
    </div>
  );
}
