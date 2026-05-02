import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useGameStore, useToastStore } from "../stores";
import type { ConnectionStatus } from "../types";

/**
 * Surfaces the §9-3 reconnection UX as toasts. Fires "再接続中…" when the
 * WebSocket drops after we were once ACTIVE, and "再接続しました" when ACTIVE
 * is reached again. Suppressed while the OS reports the user is offline —
 * `useOnlineStatus` already shows a dedicated toast for that case.
 */
export function useReconnectToast(online: boolean): void {
  const { t } = useTranslation();
  const connectionStatus = useGameStore((s) => s.connectionStatus);
  const pushToast = useToastStore((s) => s.pushToast);
  const wasConnectedRef = useRef(false);
  const prevStatusRef = useRef<ConnectionStatus | null>(null);

  useEffect(() => {
    const prev = prevStatusRef.current;
    prevStatusRef.current = connectionStatus;

    if (connectionStatus === "SESSION_LOST") return;

    if (connectionStatus === "ACTIVE") {
      if (wasConnectedRef.current && prev !== null && prev !== "ACTIVE") {
        pushToast({
          message: t("room.notice.reconnected"),
          severity: "info",
        });
      }
      wasConnectedRef.current = true;
      return;
    }

    if (
      online &&
      wasConnectedRef.current &&
      prev === "ACTIVE" &&
      (connectionStatus === "DISCONNECTED" || connectionStatus === "CONNECTING")
    ) {
      pushToast({
        message: t("room.notice.reconnecting"),
        severity: "warn",
      });
    }
  }, [connectionStatus, online, pushToast, t]);
}
