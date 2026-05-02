type MessageHandler = (data: unknown) => void;
type StatusHandler = (status: "connecting" | "connected" | "disconnected") => void;

const INITIAL_DELAY_MS = 500;
const MAX_DELAY_MS = 16_000;
const BACKOFF_MULTIPLIER = 2;

export class TacexWebSocket {
  private ws: WebSocket | null = null;
  private reconnectDelay = INITIAL_DELAY_MS;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private stopped = false;

  constructor(
    private readonly url: string,
    private readonly onMessage: MessageHandler,
    private readonly onStatus: StatusHandler,
  ) {}

  connect(): void {
    if (this.stopped) return;
    this.onStatus("connecting");
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.reconnectDelay = INITIAL_DELAY_MS;
      this.onStatus("connected");
    };

    this.ws.onmessage = (event) => {
      try {
        const data: unknown = JSON.parse(event.data as string);
        this.onMessage(data);
      } catch {
        // ignore malformed frames
      }
    };

    this.ws.onclose = () => {
      this.onStatus("disconnected");
      if (!this.stopped) this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  send(payload: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  close(): void {
    this.stopped = true;
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close(1000);
  }

  /**
   * Cancel any pending backoff and reconnect immediately. Used when the
   * browser reports that the network has come back online so the user does
   * not have to wait through the exponential delay.
   */
  reconnectNow(): void {
    if (this.stopped) return;
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.reconnectDelay = INITIAL_DELAY_MS;
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;
    this.connect();
  }

  private scheduleReconnect(): void {
    this.reconnectTimer = setTimeout(() => {
      this.reconnectDelay = Math.min(this.reconnectDelay * BACKOFF_MULTIPLIER, MAX_DELAY_MS);
      this.connect();
    }, this.reconnectDelay);
  }
}
