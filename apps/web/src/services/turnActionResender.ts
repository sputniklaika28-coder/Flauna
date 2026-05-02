/**
 * VERSION_MISMATCH 自動再送 (per spec §7-4).
 *
 * `submit_turn_action` を送るたびに `rememberSubmit` で控えておき、
 * VERSION_MISMATCH を受けたら最新の `expected_version` に差し替えて
 * 同じ turn_action を再送する。サーバー側は client_request_id で
 * 冪等にハンドルし、最新状態で改めて検証する。
 *
 * 再送結果として別のエラーコード (OUT_OF_RANGE 等) が返った場合は
 * 通常のエラーハンドリングが拾うので、ここでは関与しない。
 */
/**
 * Shape of an outgoing submit_turn_action payload. The local `TurnAction`
 * type only covers the MVP fields; the server schema is broader (CastArt,
 * MeleeAttack with style/dice, etc.) so we keep `turn_action` as a record
 * here and trust the call sites to build it correctly.
 */
export interface TurnActionPayload {
  action: "submit_turn_action";
  player_id: string;
  room_id: string;
  client_request_id: string;
  expected_version: number;
  turn_action: Record<string, unknown>;
}

let lastPayload: TurnActionPayload | null = null;

export function rememberSubmit(payload: TurnActionPayload): void {
  lastPayload = payload;
}

export function clearLastSubmit(): void {
  lastPayload = null;
}

export function getLastSubmit(): TurnActionPayload | null {
  return lastPayload;
}

export interface ResubmitDeps {
  send: (p: unknown) => void;
  getCurrentVersion: () => number | undefined;
  newRequestId: () => string;
}

/**
 * Re-send the last submit_turn_action with a fresh client_request_id and the
 * current GameState.version. Returns true if a payload was queued, false if
 * there's nothing to resubmit (no prior payload, or version unavailable).
 */
export function resubmitWithCurrentVersion(deps: ResubmitDeps): boolean {
  if (!lastPayload) return false;
  const v = deps.getCurrentVersion();
  if (typeof v !== "number") return false;
  // Don't bother re-sending if the version hasn't actually advanced past the
  // one we already sent — the server will just return VERSION_MISMATCH again.
  if (v <= lastPayload.expected_version) return false;
  const next: TurnActionPayload = {
    ...lastPayload,
    client_request_id: deps.newRequestId(),
    expected_version: v,
  };
  lastPayload = next;
  deps.send(next);
  return true;
}
