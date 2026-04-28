export type Faction = "pc" | "enemy" | "neutral";
export type FirstMoveMode = "normal" | "tactical_maneuver" | "attack_focus";
export type MachineState =
  | "IDLE"
  | "RESOLVING_ACTION"
  | "AWAITING_PLAYER_INPUT"
  | "NARRATING"
  | "PAUSED";
export type GamePhase = "briefing" | "exploration" | "combat" | "assessment";
export type ConnectionStatus =
  | "CONNECTING"
  | "AUTHENTICATING"
  | "ACTIVE"
  | "DISCONNECTED"
  | "SESSION_LOST";

export interface StatusEffect {
  name: string;
  duration: number;
  payload: Record<string, number | string | boolean>;
}

export interface Character {
  id: string;
  name: string;
  player_id: string | null;
  faction: Faction;
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
  inventory: Record<string, number>;
  skills: string[];
  arts: string[];
  status_effects: StatusEffect[];
  has_acted_this_turn: boolean;
  movement_used_this_turn: number;
  first_move_mode: FirstMoveMode | null;
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
  current_turn_summary: unknown | null;
  pending_actions: unknown[];
}

export interface EvasionPending {
  pending_id: string;
  attacker_id: string;
  target_id: string;
  deadline_seconds: number;
}

export type ChatKind = "gm_narrative" | "player_statement" | "system";

export interface ChatEntry {
  id: string;
  kind: ChatKind;
  text: string;
  timestamp: string;
  isStreaming?: boolean;
}

export interface TurnAction {
  moves?: Array<[number, number]>;
  attack?: {
    target_id: string;
    weapon_id: string;
    style: string;
  };
  end_turn?: boolean;
}
