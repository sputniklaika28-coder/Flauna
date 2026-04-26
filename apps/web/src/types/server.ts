export type ConnectionStatus =
  | "CONNECTING"
  | "AUTHENTICATING"
  | "ACTIVE"
  | "DISCONNECTED"
  | "SESSION_LOST";

export type GamePhase = "briefing" | "exploration" | "combat" | "assessment";

export type MachineState =
  | "idle"
  | "resolving_action"
  | "awaiting_player_input"
  | "narrating"
  | "paused";

export interface Character {
  id: string;
  name: string;
  player_id: string | null;
  faction: "pc" | "ally_npc" | "enemy" | "neutral";
  is_boss: boolean;
  tai: number;
  rei: number;
  kou: number;
  jutsu: number;
  max_hp: number;
  max_mp: number;
  hp: number;
  mp: number;
  mobility: number;
  evasion_dice: number;
  max_evasion_dice: number;
  position: [number, number];
  equipped_weapons: string[];
  equipped_jacket: string | null;
  armor_value: number;
  has_acted_this_turn: boolean;
  movement_used_this_turn: number;
}

export interface GameState {
  room_id: string;
  version: number;
  seed: number;
  phase: GamePhase;
  machine_state: MachineState;
  turn_order: string[];
  current_turn_index: number;
  round_number: number;
  characters: Character[];
  map_size: [number, number];
  obstacles: [number, number][];
  next_event_id: number;
}

// Server → Client messages
export interface SessionRestoreMessage {
  type: "session_restore";
  event_id: number;
  timestamp: string;
  mode: "incremental" | "full_sync";
  current_state: GameState | null;
  missed_events: unknown[];
  missed_event_count: number;
  pending_for_you: unknown[];
  expired_pending: unknown[];
}

export interface ErrorMessage {
  type: "error";
  event_id: number;
  timestamp: string;
  code: string;
  message: string;
  detail: Record<string, unknown>;
  client_request_id: string | null;
}

export type ServerMessage = SessionRestoreMessage | ErrorMessage | { type: string };
