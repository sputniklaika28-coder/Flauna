// §9-3: Translate the spec-shaped `pending_for_you` / `expired_pending`
// fields on a session_restore message into store mutations + chat entries.
// Kept as a pure function so it can be unit-tested without rendering Room.tsx.
import type { EvasionPending, DeathAvoidancePending } from "../types";

export type RestoredEvasion = {
  type: "evasion_request";
  pending_id: string;
  target_character_id: string;
  target_player_id: string | null;
  deadline_at: string;
  incoming_attacks?: { attacker_id: string }[];
};
export type RestoredDeathAvoidance = {
  type: "death_avoidance_request";
  pending_id: string;
  target_character_id: string;
  target_player_id: string;
  incoming_damage: number;
  damage_type: string;
  katashiro_required: number;
  katashiro_remaining: number;
  deadline_at: string;
};
export type RestoredPending = RestoredEvasion | RestoredDeathAvoidance;

export interface ExpiredPending {
  pending_id: string;
  type: "evasion_request" | "death_avoidance_request";
  auto_choice?: string;
  reason?: string;
}

export interface SessionRestoreLike {
  pending_for_you?: RestoredPending[];
  expired_pending?: ExpiredPending[];
}

export interface ApplyDeps {
  myPlayerId: string | null;
  now?: () => number;
  setEvasionRequest: (req: EvasionPending) => void;
  setDeathAvoidanceRequest: (req: DeathAvoidancePending) => void;
  addSystemEntry: (text: string) => void;
  t: (key: string, vars?: Record<string, unknown>) => string;
  playSe: (cue: "evade_alert" | "death_avoidance_alert") => void;
}

export function deadlineSecondsFrom(
  deadlineAt: string,
  now: () => number = Date.now,
): number {
  const t = Date.parse(deadlineAt);
  if (Number.isNaN(t)) return 0;
  return Math.max(0, Math.round((t - now()) / 1000));
}

export function applySessionRestorePendings(
  msg: SessionRestoreLike,
  deps: ApplyDeps,
): void {
  const now = deps.now ?? Date.now;
  (msg.pending_for_you ?? []).forEach((p) => {
    if (p.type === "evasion_request") {
      const firstAttack = p.incoming_attacks?.[0];
      deps.setEvasionRequest({
        pending_id: p.pending_id,
        attacker_id: firstAttack?.attacker_id ?? "",
        target_id: p.target_character_id,
        deadline_seconds: deadlineSecondsFrom(p.deadline_at, now),
      });
      deps.addSystemEntry(deps.t("room.system.pendingRestoredEvasion"));
      if (p.target_player_id && p.target_player_id === deps.myPlayerId) {
        deps.playSe("evade_alert");
      }
    } else if (p.type === "death_avoidance_request") {
      deps.setDeathAvoidanceRequest({
        pending_id: p.pending_id,
        target_character_id: p.target_character_id,
        target_player_id: p.target_player_id,
        incoming_damage: p.incoming_damage,
        damage_type: p.damage_type,
        katashiro_required: p.katashiro_required,
        katashiro_remaining: p.katashiro_remaining,
        deadline_seconds: deadlineSecondsFrom(p.deadline_at, now),
      });
      deps.addSystemEntry(deps.t("room.system.pendingRestoredDeathAvoidance"));
      if (p.target_player_id === deps.myPlayerId) {
        deps.playSe("death_avoidance_alert");
      }
    }
  });

  (msg.expired_pending ?? []).forEach((ep) => {
    const key =
      ep.type === "death_avoidance_request"
        ? "room.system.pendingExpiredDeathAvoidance"
        : "room.system.pendingExpiredEvasion";
    deps.addSystemEntry(
      deps.t(key, { reason: ep.reason ?? ep.auto_choice ?? "" }),
    );
  });
}
