const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";

export interface CreateRoomResponse {
  room_id: string;
  master_token: string;
  scenario_title: string;
}

export interface JoinRoomResponse {
  player_id: string;
  player_token: string;
  room_info: Record<string, string>;
}

export async function createRoom(
  scenarioId: string,
  playerName: string
): Promise<CreateRoomResponse> {
  const res = await fetch(`${API_BASE}/api/v1/rooms`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario_id: scenarioId, player_name: playerName }),
  });
  if (!res.ok) throw new Error(`Failed to create room: ${res.statusText}`);
  return res.json() as Promise<CreateRoomResponse>;
}

export async function joinRoom(
  roomId: string,
  playerName: string
): Promise<JoinRoomResponse> {
  const res = await fetch(`${API_BASE}/api/v1/rooms/${roomId}/join`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ player_name: playerName }),
  });
  if (!res.ok) throw new Error(`Failed to join room: ${res.statusText}`);
  return res.json() as Promise<JoinRoomResponse>;
}
