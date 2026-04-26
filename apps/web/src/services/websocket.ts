import { nanoid } from "nanoid";

import type { ConnectionStatus } from "../types/server";

type MessageHandler = (msg: unknown) => void;

const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000];
const MAX_RECONNECT_MS = 60_000;

class TacExWebSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private handlers = new Set<MessageHandler>();

  private roomId = "";
  private token = "";
  private playerId = "";
  private lastSeenEventId = 0;

  onStatusChange: (status: ConnectionStatus) => void = () => undefined;

  connect(roomId: string, token: string, playerId: string, lastEventId = 0): void {
    this.roomId = roomId;
    this.token = token;
    this.playerId = playerId;
    this.lastSeenEventId = lastEventId;
    this.reconnectAttempt = 0;
    this._connect();
  }

  private _connect(): void {
    const wsBase =
      (import.meta.env.VITE_WS_BASE as string | undefined) ?? "ws://localhost:8000";
    this.ws = new WebSocket(`${wsBase}/room/${this.roomId}`);
    this.onStatusChange("CONNECTING");

    this.ws.onopen = () => {
      this.onStatusChange("AUTHENTICATING");
      this.ws!.send(
        JSON.stringify({
          action: "join_room",
          player_id: this.playerId,
          room_id: this.roomId,
          auth_token: this.token,
          last_seen_event_id: this.lastSeenEventId,
        })
      );
    };

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data as string) as { type: string };
      if (msg.type === "session_restore" || msg.type === "state_full") {
        this.onStatusChange("ACTIVE");
        this.reconnectAttempt = 0;
      }
      for (const h of this.handlers) h(msg);
    };

    this.ws.onclose = (event) => {
      const noReconnectCodes = new Set([4000, 4001, 4002, 4005]);
      if (noReconnectCodes.has(event.code)) {
        this.onStatusChange("SESSION_LOST");
        return;
      }
      this._scheduleReconnect();
    };
  }

  private _scheduleReconnect(): void {
    const elapsed = RECONNECT_DELAYS.slice(0, this.reconnectAttempt).reduce(
      (a, b) => a + b,
      0
    );
    if (elapsed >= MAX_RECONNECT_MS) {
      this.onStatusChange("SESSION_LOST");
      return;
    }
    const delay = RECONNECT_DELAYS[Math.min(this.reconnectAttempt, RECONNECT_DELAYS.length - 1)];
    this.reconnectAttempt++;
    this.onStatusChange("DISCONNECTED");
    this.reconnectTimer = setTimeout(() => this._connect(), delay);
  }

  send(message: Record<string, unknown>): void {
    this.ws?.send(JSON.stringify({ ...message, client_request_id: nanoid() }));
  }

  addMessageHandler(handler: MessageHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  disconnect(): void {
    if (this.reconnectTimer !== null) clearTimeout(this.reconnectTimer);
    this.ws?.close(1001);
    this.ws = null;
  }
}

export const wsClient = new TacExWebSocket();
