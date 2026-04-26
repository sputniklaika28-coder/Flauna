import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

type ConnectionStatus = "connecting" | "connected" | "disconnected";

interface SessionRestoreMessage {
  type: "session_restore";
  event_id: number;
  timestamp: string;
  mode: "incremental" | "full_sync";
  missed_events: unknown[];
  missed_event_count: number;
}

export default function Room() {
  const { roomId } = useParams<{ roomId: string }>();
  const { t } = useTranslation();
  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [messages, setMessages] = useState<string[]>([]);

  useEffect(() => {
    if (!roomId) return;

    const token = sessionStorage.getItem(`token:${roomId}`) ?? "";
    const playerId = sessionStorage.getItem(`playerId:${roomId}`) ?? "player-unknown";

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocol}://${window.location.host}/room/${roomId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(
        JSON.stringify({
          action: "join_room",
          player_id: playerId,
          room_id: roomId,
          auth_token: token,
          last_seen_event_id: 0,
        }),
      );
    };

    ws.onmessage = (ev: MessageEvent<string>) => {
      const msg: unknown = JSON.parse(ev.data);
      if (
        msg !== null &&
        typeof msg === "object" &&
        "type" in msg &&
        (msg as Record<string, unknown>)["type"] === "session_restore"
      ) {
        setStatus("connected");
      }
      setMessages((prev) => [...prev, ev.data]);
    };

    ws.onerror = () => setStatus("disconnected");
    ws.onclose = () => setStatus("disconnected");

    return () => {
      ws.close();
    };
  }, [roomId]);

  const statusLabel =
    status === "connecting"
      ? t("room.connecting")
      : status === "connected"
        ? t("room.connected")
        : t("room.disconnected");

  return (
    <main style={{ padding: "2rem" }}>
      <h1>{t("room.title")}</h1>
      <p>
        {t("lobby.roomId")}: <code>{roomId}</code> — {statusLabel}
      </p>
      <section style={{ fontFamily: "monospace", fontSize: "0.85rem" }}>
        {messages.map((m, i) => (
          <div key={i}>{m}</div>
        ))}
      </section>
    </main>
  );
}
