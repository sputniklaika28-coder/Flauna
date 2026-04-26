// AUTO-GENERATED — do not edit manually. Run: bash packages/ws-schema/scripts/generate.sh
// This file will be overwritten by the code generator once schemas/*.json are produced.

export type ClientMessageAction =
  | "join_room"
  | "submit_turn_action"
  | "submit_evasion"
  | "submit_death_avoidance"
  | "player_statement";

export type ServerMessageType =
  | "session_restore"
  | "state_update"
  | "state_full"
  | "gm_narrative"
  | "event"
  | "ai_thinking"
  | "evade_required"
  | "ai_fallback_notice"
  | "session_lost"
  | "error";
