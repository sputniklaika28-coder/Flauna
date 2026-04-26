const BASE = "/api/v1";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw Object.assign(new Error(`HTTP ${res.status}`), { status: res.status, body });
  }
  return res.json() as Promise<T>;
}

export interface CreateRoomRequest {
  scenario_id: string;
  player_name: string;
}

export interface CreateRoomResponse {
  room_id: string;
  master_token: string;
  scenario_title: string;
}

export interface JoinRoomRequest {
  player_name: string;
}

export interface JoinRoomResponse {
  player_id: string;
  player_token: string;
  room_info: { room_id: string; title: string };
}

export function createRoom(req: CreateRoomRequest): Promise<CreateRoomResponse> {
  return fetchJson<CreateRoomResponse>("/rooms", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function joinRoom(roomId: string, req: JoinRoomRequest): Promise<JoinRoomResponse> {
  return fetchJson<JoinRoomResponse>(`/rooms/${roomId}/join`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}
