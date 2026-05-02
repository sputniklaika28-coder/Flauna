import { useEffect, useState } from "react";

/**
 * Track `navigator.onLine` and refresh on `online` / `offline` window events.
 * Returns `true` when the browser believes it has network connectivity.
 *
 * Phase 9 — combined with WebSocket disconnect detection per spec §10-3.
 */
export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState<boolean>(() =>
    typeof navigator === "undefined" ? true : navigator.onLine,
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    const handleOnline = () => setOnline(true);
    const handleOffline = () => setOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return online;
}
