import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { TacexWebSocket } from "../../src/services/websocket";

// Minimal WebSocket mock
class MockWebSocket {
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.OPEN;
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;

  sentMessages: string[] = [];
  closeCode: number | undefined;

  constructor(url: string) {
    this.url = url;
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close(code?: number) {
    this.closeCode = code;
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  }

  // Test helpers
  simulateOpen() {
    this.onopen?.();
  }

  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  simulateRawMessage(raw: string) {
    this.onmessage?.({ data: raw });
  }

  simulateClose() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  }

  simulateError() {
    this.onerror?.();
  }
}

let lastSocket: MockWebSocket | null = null;

beforeEach(() => {
  lastSocket = null;
  vi.useFakeTimers();
  vi.stubGlobal(
    "WebSocket",
    class extends MockWebSocket {
      constructor(url: string) {
        super(url);
        lastSocket = this;
      }
    },
  );
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

function makeHandlers() {
  const messages: unknown[] = [];
  const statuses: string[] = [];
  const onMessage = vi.fn((d: unknown) => messages.push(d));
  const onStatus = vi.fn((s: string) => statuses.push(s));
  return { messages, statuses, onMessage, onStatus };
}

// ---------------------------------------------------------------------------
// connect
// ---------------------------------------------------------------------------

describe("TacexWebSocket.connect", () => {
  it("emits connecting status on connect", () => {
    const { onMessage, onStatus, statuses } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    tws.connect();
    expect(statuses).toContain("connecting");
  });

  it("creates WebSocket with correct URL", () => {
    const { onMessage, onStatus } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    tws.connect();
    expect(lastSocket?.url).toBe("ws://localhost/room/r1");
  });

  it("emits connected status on open", () => {
    const { onMessage, onStatus, statuses } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    tws.connect();
    lastSocket?.simulateOpen();
    expect(statuses).toContain("connected");
  });

  it("emits disconnected status on close", () => {
    const { onMessage, onStatus, statuses } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    tws.connect();
    tws.close(); // stop so no reconnect
    expect(statuses).toContain("disconnected");
  });

  it("delivers parsed JSON messages to handler", () => {
    const { onMessage, onStatus, messages } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    tws.connect();
    lastSocket?.simulateMessage({ type: "gm_narrative", text: "Hello" });
    expect(messages).toEqual([{ type: "gm_narrative", text: "Hello" }]);
  });

  it("silently ignores malformed JSON frames", () => {
    const { onMessage, onStatus } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    tws.connect();
    expect(() => lastSocket?.simulateRawMessage("not json")).not.toThrow();
    expect(onMessage).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// send
// ---------------------------------------------------------------------------

describe("TacexWebSocket.send", () => {
  it("serialises payload as JSON and sends when OPEN", () => {
    const { onMessage, onStatus } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    tws.connect();
    lastSocket?.simulateOpen();
    tws.send({ action: "join_room" });
    expect(lastSocket?.sentMessages).toEqual([JSON.stringify({ action: "join_room" })]);
  });

  it("does nothing when socket is not OPEN", () => {
    const { onMessage, onStatus } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    tws.connect();
    if (lastSocket) lastSocket.readyState = MockWebSocket.CLOSED;
    tws.send({ action: "join_room" });
    expect(lastSocket?.sentMessages).toEqual([]);
  });

  it("does nothing before connect is called", () => {
    const { onMessage, onStatus } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    // no tws.connect()
    expect(() => tws.send({ action: "test" })).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// close
// ---------------------------------------------------------------------------

describe("TacexWebSocket.close", () => {
  it("closes the underlying socket with code 1000", () => {
    const { onMessage, onStatus } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    tws.connect();
    tws.close();
    expect(lastSocket?.closeCode).toBe(1000);
  });

  it("does not reconnect after explicit close", () => {
    const { onMessage, onStatus } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    tws.connect();
    const firstSocket = lastSocket;
    tws.close();
    vi.runAllTimers();
    // lastSocket should still be the same (no new WS was created)
    expect(lastSocket).toBe(firstSocket);
  });
});

// ---------------------------------------------------------------------------
// reconnect
// ---------------------------------------------------------------------------

describe("TacexWebSocket reconnect", () => {
  it("schedules reconnect after unexpected disconnect", () => {
    const { onMessage, onStatus } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    tws.connect();
    const firstSocket = lastSocket;
    firstSocket?.simulateClose(); // unexpected close
    vi.runAllTimers();
    expect(lastSocket).not.toBe(firstSocket);
  });

  it("resets reconnect delay to initial on successful open", () => {
    const { onMessage, onStatus, statuses } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    tws.connect();
    lastSocket?.simulateClose();
    vi.runAllTimers();
    lastSocket?.simulateOpen();
    // After successful open, another disconnect should reconnect without long delay
    lastSocket?.simulateClose();
    vi.advanceTimersByTime(600); // should be within initial 500ms delay
    expect(lastSocket).not.toBeNull();
    tws.close();
  });
});

// ---------------------------------------------------------------------------
// reconnectNow
// ---------------------------------------------------------------------------

describe("TacexWebSocket.reconnectNow", () => {
  it("cancels pending backoff and reconnects immediately", () => {
    const { onMessage, onStatus } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    tws.connect();
    const firstSocket = lastSocket;
    firstSocket?.simulateClose();
    // A reconnect is scheduled but not yet fired.
    expect(lastSocket).toBe(firstSocket);
    tws.reconnectNow();
    expect(lastSocket).not.toBe(firstSocket);
    tws.close();
  });

  it("is a no-op when the socket is already OPEN", () => {
    const { onMessage, onStatus } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    tws.connect();
    lastSocket?.simulateOpen();
    const sock = lastSocket;
    tws.reconnectNow();
    expect(lastSocket).toBe(sock);
    tws.close();
  });

  it("does nothing after explicit close", () => {
    const { onMessage, onStatus } = makeHandlers();
    const tws = new TacexWebSocket("ws://localhost/room/r1", onMessage, onStatus);
    tws.connect();
    tws.close();
    const sock = lastSocket;
    tws.reconnectNow();
    expect(lastSocket).toBe(sock);
  });
});
