import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { useGameStore } from "../stores/gameStore";
import { wsClient } from "../services/websocket";
import type { ConnectionStatus, ServerMessage } from "../types/server";

const STATUS_LABELS: Record<ConnectionStatus, string> = {
  CONNECTING: "room.connecting",
  AUTHENTICATING: "room.connecting",
  ACTIVE: "room.connected",
  DISCONNECTED: "room.disconnected",
  SESSION_LOST: "room.sessionLost",
};

export default function Room() {
  const { t } = useTranslation();
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();
  const { connectionStatus, setConnectionStatus, setLastSeenEventId } = useGameStore();

  useEffect(() => {
    if (!roomId) return;

    const token =
      sessionStorage.getItem("master_token") ??
      sessionStorage.getItem("player_token") ??
      "";
    const playerId = sessionStorage.getItem("player_id") ?? "master";

    wsClient.onStatusChange = setConnectionStatus;
    wsClient.connect(roomId, token, playerId);

    const removeHandler = wsClient.addMessageHandler((msg) => {
      const m = msg as ServerMessage;
      if ("event_id" in m && typeof m.event_id === "number") {
        setLastSeenEventId(m.event_id);
      }
    });

    return () => {
      removeHandler();
      wsClient.disconnect();
    };
  }, [roomId, setConnectionStatus, setLastSeenEventId]);

  function handleQuit() {
    wsClient.disconnect();
    void navigate("/");
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      <header className="p-4 border-b border-gray-700 flex items-center justify-between">
        <h1 className="text-xl font-bold">TacEx</h1>
        <span className="text-sm text-gray-400">{t(STATUS_LABELS[connectionStatus])}</span>
        <button
          className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-sm"
          onClick={handleQuit}
        >
          {t("settings.quit")}
        </button>
      </header>
      <main className="flex-1 p-8 text-center text-gray-400 flex items-center justify-center">
        <div>
          <p className="text-lg">{roomId}</p>
          <p className="text-sm mt-2">{t(STATUS_LABELS[connectionStatus])}</p>
        </div>
      </main>
    </div>
  );
}
