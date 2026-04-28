"""WebSocket handler — Phase 4 combat loop (GM spec §7-6, §8, §10-1, §10-2).

Phase 3 additions:
  - 攻撃集中 (attack_focus): no first move, attack difficulty −1
  - 戦術機動 (tactical_maneuver): 巧 NORMAL check, double mobility, action difficulty +1
  - 連撃 (RENGEKI): even dice distribution validation
  - Evasion dice tracking: consumed on use, restored at turn start

Phase 4 additions:
  - 全スタイル: style-based difficulty modifiers for MeleeStyle / RangedStyle
  - 形代システム: death avoidance when damage > current HP × 2 (§10-2, D34)
  - リスポーン: HP half-restore, status clear, move to respawn_point (D36)

Flow per turn:
  PC turn  → wait for submit_turn_action → resolve attack (NPC auto-evades)
           → apply damage → narrate → advance
  NPC turn → select_default_action → resolve attack → send evade_required
           → wait for submit_evasion → check death avoidance → apply damage
           → narrate → advance
"""

from __future__ import annotations

import contextlib
import datetime
import json
import logging
import uuid
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError

from tacex_gm.auth import verify_token
from tacex_gm.engine.combat import (
    apply_damage,
    build_incoming_attacks,
    compute_damage,
    resolve_attack,
    resolve_evasion,
)
from tacex_gm.engine.default_actions import select_default_action
from tacex_gm.engine.dice import PythonDiceEngine
from tacex_gm.engine.npc_evasion import npc_decide_evasion_dice
from tacex_gm.engine.session_builder import build_initial_state
from tacex_gm.engine.victory import check_combat_outcome
from tacex_gm.errors import CloseCode, ErrorCode
from tacex_gm.models import (
    Character,
    GameState,
    MachineState,
    MeleeAttack,
    Movement,
    RangedAttack,
    TurnAction,
)
from tacex_gm.models.constants import DIFFICULTY_NORMAL, MeleeStyle, RangedStyle
from tacex_gm.models.event import TurnSummary
from tacex_gm.models.pending import DeathAvoidanceRequest, EvasionRequest, IncomingAttack
from tacex_gm.models.turn_action import PegAttack
from tacex_gm.room.session import RoomSession, RoomStore
from tacex_gm.scenario.loader import load_scenario
from tacex_gm.ws.messages import (
    AiFallbackNotice,
    AiThinking,
    ClientMessage,
    DeathAvoidanceRequired,
    ErrorMessage,
    EvadeRequired,
    GameEventMessage,
    GmNarrative,
    JoinRoom,
    SessionRestore,
    StateFull,
    SubmitDeathAvoidance,
    SubmitEvasion,
    SubmitTurnAction,
)

logger = logging.getLogger(__name__)

_client_message_adapter: TypeAdapter[ClientMessage] = TypeAdapter(ClientMessage)

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def handle_room_websocket(
    websocket: WebSocket,
    room_id: str,
    room_store: RoomStore,
    scenario_dir: str,
) -> None:
    await websocket.accept()
    logger.info("WS connected: room=%s", room_id)

    try:
        await _run_session(websocket, room_id, room_store, scenario_dir)
    except WebSocketDisconnect:
        logger.info("WS disconnected: room=%s", room_id)
    except Exception:
        logger.exception("Unhandled error in WS handler: room=%s", room_id)
        with contextlib.suppress(Exception):
            await websocket.close(CloseCode.AUTH_FAILED)


# ---------------------------------------------------------------------------
# Session setup
# ---------------------------------------------------------------------------


async def _run_session(
    websocket: WebSocket,
    room_id: str,
    room_store: RoomStore,
    scenario_dir: str,
) -> None:
    # 1. Receive join_room (first message must be this).
    raw = await websocket.receive_text()
    msg = _parse_client_message(raw)
    if msg is None or not isinstance(msg, JoinRoom):
        await _send_error(websocket, ErrorCode.INVALID_MESSAGE, "First message must be join_room")
        await websocket.close(CloseCode.AUTH_FAILED)
        return

    # 2. Verify auth token.
    token_payload = verify_token(msg.auth_token)
    if token_payload is None or token_payload["room_id"] != room_id:
        await _send_error(websocket, ErrorCode.AUTH_INVALID_TOKEN, "Invalid or expired token")
        await websocket.close(CloseCode.AUTH_FAILED)
        return

    player_id = token_payload["player_id"]

    # 3. Look up session.
    session = room_store.get_session(room_id)
    if session is None:
        await _send_error(websocket, ErrorCode.ROOM_NOT_FOUND, "Room not found")
        await websocket.close(CloseCode.AUTH_FAILED)
        return

    # 4. Initialise GameState on first connection (lazy).
    async with session._init_lock:
        if session.state is None:
            slot = session.player_slots.get(player_id)
            if slot is None:
                await _send_error(
                    websocket, ErrorCode.AUTH_PERMISSION_DENIED, "Player not registered in room"
                )
                await websocket.close(CloseCode.AUTH_FAILED)
                return

            from pathlib import Path

            scenario_path = Path(scenario_dir) / f"{session.scenario_id}.yaml"
            scenario = load_scenario(scenario_path)

            state, pc_char_id = build_initial_state(
                room_id=room_id,
                scenario=scenario,
                enemy_catalog=session.enemy_catalog,
                player_id=player_id,
                player_name=slot.player_name,
            )
            session.state = state
            session.set_character_id(player_id, pc_char_id)

    state = session.state
    assert state is not None

    # 5. Send session_restore.
    restore = SessionRestore(
        type="session_restore",
        event_id=state.next_event_id,
        timestamp=_now(),
        mode="full_sync",
        current_state=state.model_dump(mode="json"),
    )
    await websocket.send_text(restore.model_dump_json())

    # 6. Run the combat loop (WebSocketDisconnect exits cleanly).
    with contextlib.suppress(WebSocketDisconnect):
        await _combat_loop(websocket, session, player_id)


# ---------------------------------------------------------------------------
# Combat loop
# ---------------------------------------------------------------------------


async def _combat_loop(
    websocket: WebSocket,
    session: RoomSession,
    player_id: str,
) -> None:
    state = session.state
    assert state is not None

    dice = PythonDiceEngine(seed=state.seed)

    while True:
        # Check for combat end before each turn.
        outcome = check_combat_outcome(state)
        if outcome is not None:
            await _emit_event(websocket, state, "combat_ended", {"outcome": outcome})
            narrative = _render_combat_end(session, outcome)
            await _send_narrative(websocket, state, narrative)
            break

        actor = state.current_actor()
        if actor is None:
            break

        if actor.faction == "pc":
            await _run_pc_turn(websocket, session, player_id, dice)
        else:
            await _run_npc_turn(websocket, session, player_id, dice)

        # Refresh state reference (may have been replaced by model_copy).
        state = session.state
        assert state is not None


# ---------------------------------------------------------------------------
# PC turn
# ---------------------------------------------------------------------------


async def _run_pc_turn(
    websocket: WebSocket,
    session: RoomSession,
    player_id: str,
    dice: PythonDiceEngine,
) -> None:
    # Wait for player's action. Re-raise disconnect so the loop exits cleanly.
    try:
        raw = await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError) as exc:
        raise WebSocketDisconnect() from exc
    msg = _parse_client_message(raw)

    if msg is None:
        await _send_error(websocket, ErrorCode.INVALID_MESSAGE, "Invalid message")
        return
    if not isinstance(msg, SubmitTurnAction):
        await _send_error(websocket, ErrorCode.OUT_OF_TURN, "Expected submit_turn_action")
        return

    # Idempotency check.
    cached = session.idempotency.get(msg.client_request_id)
    if cached is not None:
        await websocket.send_text(cached)
        return

    async with session.lock.acquire():
        state = session.state
        assert state is not None

        # version check
        if state.version != msg.expected_version:
            err = _make_error(
                state,
                ErrorCode.VERSION_MISMATCH,
                "State version mismatch",
                detail={
                    "current_version": state.version,
                    "expected_version": msg.expected_version,
                },
                client_request_id=msg.client_request_id,
            )
            await websocket.send_text(err.model_dump_json())
            return

        actor = state.current_actor()
        if actor is None or actor.player_id != player_id:
            await _send_error(websocket, ErrorCode.OUT_OF_TURN, "Not your turn")
            return

        # Parse TurnAction from raw dict.
        try:
            turn_action = TurnAction.model_validate(msg.turn_action)
        except Exception as exc:
            await _send_error(
                websocket, ErrorCode.INVALID_ACTION_SEQUENCE, f"Invalid turn_action: {exc}"
            )
            return

        state = state.model_copy(update={"machine_state": MachineState.RESOLVING_ACTION})
        session.state = state

        # Restore actor's evasion dice at start of their turn (§19 rule).
        actor = _restore_evasion_dice(actor)
        state = _replace_character(state, actor)
        session.state = state

        # Determine style_modifier from first_move.mode (Phase 3 §19 rules).
        style_modifier = 0
        narrative_parts_pre: list[str] = []

        if turn_action.first_move is not None:
            if turn_action.first_move.mode == "attack_focus":
                # No actual movement; attack difficulty −1.
                style_modifier = -1
                narrative_parts_pre.append(f"{actor.name}は攻撃に集中した！（難易度-1）")
            elif turn_action.first_move.mode == "tactical_maneuver":
                # Roll 巧 at NORMAL; double mobility on success; action difficulty +1.
                kou_roll = await dice.roll_pool(count=actor.kou, threshold=DIFFICULTY_NORMAL)
                if kou_roll.successes >= 1:
                    narrative_parts_pre.append(
                        f"{actor.name}は戦術機動に成功！（機動力2倍、難易度+1）"
                    )
                else:
                    narrative_parts_pre.append(
                        f"{actor.name}は戦術機動を試みたが失敗。（難易度+1）"
                    )
                style_modifier = 1
                state = _apply_movement(state, actor.id, turn_action.first_move)
                session.state = state
                actor = state.find_character(actor.id)
                assert actor is not None
            else:
                state = _apply_movement(state, actor.id, turn_action.first_move)
                session.state = state
                actor = state.find_character(actor.id)
                assert actor is not None

        # Resolve main_action (attack).
        summary = TurnSummary(actor_id=actor.id)
        narrative_parts: list[str] = [*narrative_parts_pre]

        if isinstance(turn_action.main_action, (MeleeAttack, RangedAttack, PegAttack)):
            attack = turn_action.main_action
            weapon = session.weapon_catalog.get(attack.weapon_id)
            if weapon is None:
                await _send_error(
                    websocket, ErrorCode.UNKNOWN_WEAPON, f"Unknown weapon: {attack.weapon_id}"
                )
                state = state.model_copy(update={"machine_state": MachineState.IDLE})
                session.state = state
                return

            targets = [state.find_character(tid) for tid in attack.targets]
            if any(t is None for t in targets):
                await _send_error(websocket, ErrorCode.UNKNOWN_TARGET, "Unknown target character")
                state = state.model_copy(update={"machine_state": MachineState.IDLE})
                session.state = state
                return
            targets_valid: list[Character] = [t for t in targets if t is not None]

            # Validate 連撃 even distribution (Phase 3).
            if (
                isinstance(attack, MeleeAttack)
                and attack.style == MeleeStyle.RENGEKI
                and len(attack.dice_distribution) > 1
            ):
                total_dice = sum(attack.dice_distribution)
                if total_dice > 0:
                    expected = total_dice // len(attack.dice_distribution)
                    remainder = total_dice % len(attack.dice_distribution)
                    for i, d in enumerate(attack.dice_distribution):
                        expected_i = expected + (1 if i < remainder else 0)
                        if d != expected_i:
                            await _send_error(
                                websocket,
                                ErrorCode.INVALID_ACTION_SEQUENCE,
                                "連撃: dice must be distributed evenly across targets",
                            )
                            state = state.model_copy(update={"machine_state": MachineState.IDLE})
                            session.state = state
                            return

            # Phase 4: add attack-style difficulty modifier on top of movement modifier.
            if isinstance(attack, MeleeAttack):
                style_modifier += _melee_style_modifier(attack.style)
            elif isinstance(attack, (RangedAttack, PegAttack)):
                style_modifier += _ranged_style_modifier(
                    attack.style if isinstance(attack, RangedAttack) else RangedStyle.NONE
                )

            hit_outcomes = await resolve_attack(
                attacker=actor,
                weapon=weapon,
                targets=targets_valid,
                dice_distribution=attack.dice_distribution,
                dice_engine=dice,
                obstacles=state.obstacles,
                style_modifier=style_modifier,
            )

            # For each NPC target that was hit: auto-evasion, then damage.
            incoming_by_target = build_incoming_attacks(
                attacker=actor, weapon=weapon, hit_outcomes=hit_outcomes
            )
            for target in targets_valid:
                hits = incoming_by_target.get(target.id)
                if not hits:
                    narrative_parts.append(f"{actor.name}の攻撃は{target.name}に当たらなかった。")
                    continue

                # NPC auto-evade — consume evasion dice (Phase 3).
                npc_dice = npc_decide_evasion_dice(target, hits)
                evasion_outcome = await resolve_evasion(
                    pending_id=str(uuid.uuid4()),
                    target=target,
                    dice_used=npc_dice,
                    dice_engine=dice,
                )
                target = _consume_evasion_dice(target, npc_dice)
                state = _replace_character(state, target)
                session.state = state

                if evasion_outcome.succeeded:
                    narrative_parts.append(f"{target.name}は{actor.name}の攻撃を回避した！")
                    continue

                # Apply damage for each hit.
                for _ in hits:
                    dmg = await compute_damage(
                        attacker=actor, target=target, weapon=weapon, dice_engine=dice
                    )
                    new_target = apply_damage(target, dmg)
                    state = _replace_character(state, new_target)
                    session.state = state
                    summary.damage_dealt[target.id] = (
                        summary.damage_dealt.get(target.id, 0) + dmg.final_damage
                    )
                    narrative_parts.append(
                        f"{actor.name}の{weapon.name}が{target.name}に{dmg.final_damage}ダメージ！"
                        f"（残りHP: {new_target.hp}/{new_target.max_hp}）"
                    )

                    if not new_target.is_alive:
                        narrative_parts.append(f"{target.name}は倒れた！")
                        await _emit_event(
                            websocket, state, "character_died", {"character_id": target.id}
                        )
                    target = new_target

        # Apply second_move.
        if turn_action.second_move is not None:
            state = _apply_movement(state, actor.id, turn_action.second_move)
            session.state = state

        # Advance state version and turn.
        state = state.model_copy(
            update={
                "version": state.version + 1,
                "machine_state": MachineState.NARRATING,
                "current_turn_summary": summary,
            }
        )
        session.state = state

        # Emit state_update.
        await _send_state_update(websocket, state)
        await _emit_event(websocket, state, "turn_ended", {"actor_id": actor.id})

        # Narrate.
        narrative = "\n".join(narrative_parts) if narrative_parts else f"{actor.name}は行動した。"
        await _send_narrative(websocket, state, narrative)

        # Advance turn.
        state = _advance_turn(state)
        state = state.model_copy(update={"machine_state": MachineState.IDLE})
        session.state = state
        await _send_state_update(websocket, state)


# ---------------------------------------------------------------------------
# NPC turn
# ---------------------------------------------------------------------------


async def _run_npc_turn(
    websocket: WebSocket,
    session: RoomSession,
    player_id: str,
    dice: PythonDiceEngine,
) -> None:
    async with session.lock.acquire():
        state = session.state
        assert state is not None

        actor = state.current_actor()
        if actor is None:
            return

        state = state.model_copy(update={"machine_state": MachineState.RESOLVING_ACTION})
        session.state = state

        # Restore NPC's evasion dice at start of their turn (Phase 3 §19 rule).
        actor = _restore_evasion_dice(actor)
        state = _replace_character(state, actor)
        session.state = state

        # Signal AI thinking (using default action selector).
        await _send_ws(
            websocket,
            AiThinking(
                type="ai_thinking",
                event_id=state.next_event_id,
                timestamp=_now(),
                stage="deciding_action",
            ),
        )
        await _send_ws(
            websocket,
            AiFallbackNotice(
                type="ai_fallback_notice",
                event_id=state.next_event_id,
                timestamp=_now(),
                reason="default_action_table",
            ),
        )

        turn_action = select_default_action(actor, state, session.weapon_catalog)

        summary = TurnSummary(actor_id=actor.id)
        narrative_parts: list[str] = []

        # Apply first_move.
        if turn_action.first_move is not None:
            state = _apply_movement(state, actor.id, turn_action.first_move)
            session.state = state
            actor = state.find_character(actor.id)
            assert actor is not None

        # Emit partial state_update for movement.
        if turn_action.first_move is not None:
            state = state.model_copy(update={"version": state.version + 1})
            session.state = state
            await _send_state_update(websocket, state)

        # Resolve main_action.
        evasion_request: EvasionRequest | None = None
        attack_context: dict[str, Any] = {}  # stores weapon + actor for post-evasion step

        if isinstance(turn_action.main_action, (MeleeAttack, RangedAttack, PegAttack)):
            attack = turn_action.main_action
            weapon = session.weapon_catalog.get(attack.weapon_id)
            if weapon is None:
                state = state.model_copy(update={"machine_state": MachineState.IDLE})
                session.state = state
                _advance_turn(state)
                return

            targets = [state.find_character(tid) for tid in attack.targets]
            targets_valid: list[Character] = [t for t in targets if t is not None]

            hit_outcomes = await resolve_attack(
                attacker=actor,
                weapon=weapon,
                targets=targets_valid,
                dice_distribution=attack.dice_distribution,
                dice_engine=dice,
                obstacles=state.obstacles,
            )

            incoming_by_target = build_incoming_attacks(
                attacker=actor, weapon=weapon, hit_outcomes=hit_outcomes
            )

            # For PC targets: build EvasionRequest and suspend.
            for target in targets_valid:
                if target.faction != "pc":
                    continue
                hits = incoming_by_target.get(target.id)
                if not hits:
                    narrative_parts.append(f"{actor.name}の攻撃は{target.name}に当たらなかった。")
                    continue

                pending_id = str(uuid.uuid4())
                evasion_request = EvasionRequest.with_default_deadline(
                    pending_id=pending_id,
                    target_character_id=target.id,
                    target_player_id=player_id,
                    incoming_attacks=hits,
                    max_evasion_dice=target.evasion_dice,
                )
                state = state.model_copy(
                    update={
                        "pending_actions": [*state.pending_actions, evasion_request],
                        "machine_state": MachineState.AWAITING_PLAYER_INPUT,
                    }
                )
                session.state = state
                attack_context = {"weapon": weapon, "actor": actor, "hits": hits}
                break  # MVP: single target

        if evasion_request is None:
            # No hit on PC: narrate and advance.
            state = state.model_copy(
                update={"version": state.version + 1, "machine_state": MachineState.NARRATING}
            )
            session.state = state
            await _send_state_update(websocket, state)
            await _emit_event(websocket, state, "turn_ended", {"actor_id": actor.id})
            narrative = (
                "\n".join(narrative_parts) if narrative_parts else f"{actor.name}は行動した。"
            )
            await _send_narrative(websocket, state, narrative)
            state = _advance_turn(state)
            state = state.model_copy(update={"machine_state": MachineState.IDLE})
            session.state = state
            await _send_state_update(websocket, state)
            return

    # --- Outside the lock: send evade_required and wait for response. ---
    assert evasion_request is not None

    await _send_ws(
        websocket,
        EvadeRequired(
            type="evade_required",
            event_id=state.next_event_id,
            timestamp=_now(),
            pending_id=evasion_request.pending_id,
            attacker_id=evasion_request.incoming_attacks[0].attacker_id,
            target_id=evasion_request.target_character_id,
            deadline_seconds=60,
        ),
    )

    evasion_msg = await _wait_for_evasion(websocket, evasion_request.pending_id)

    # Phase 4: may be filled when a hit triggers death avoidance.
    death_avoidance_context: dict[str, Any] = {}

    async with session.lock.acquire():
        state = session.state
        assert state is not None

        # Remove pending action.
        state = state.model_copy(
            update={
                "pending_actions": [
                    p for p in state.pending_actions if p.pending_id != evasion_request.pending_id
                ],
                "machine_state": MachineState.RESOLVING_ACTION,
            }
        )
        session.state = state

        weapon = attack_context["weapon"]
        actor_char: Character = attack_context["actor"]
        attack_hits: list[IncomingAttack] = attack_context["hits"]

        evade_target = state.find_character(evasion_request.target_character_id)
        if evade_target is None:
            state = _advance_turn(state)
            state = state.model_copy(update={"machine_state": MachineState.IDLE})
            session.state = state
            return

        dice_used = evasion_msg.dice_result if evasion_msg is not None else 0
        dice_used = max(0, min(dice_used, evade_target.evasion_dice))

        evasion_outcome = await resolve_evasion(
            pending_id=evasion_request.pending_id,
            target=evade_target,
            dice_used=dice_used,
            dice_engine=dice,
        )

        # Consume player evasion dice (Phase 3).
        evade_target = _consume_evasion_dice(evade_target, dice_used)
        state = _replace_character(state, evade_target)
        session.state = state

        if evasion_outcome.succeeded:
            narrative_parts.append(f"{evade_target.name}は{actor_char.name}の攻撃を回避した！")
        else:
            for _ in attack_hits:
                dmg = await compute_damage(
                    attacker=actor_char, target=evade_target, weapon=weapon, dice_engine=dice
                )
                # Phase 4: check death avoidance trigger (§10-2, D34).
                if (
                    evade_target.faction == "pc"
                    and _death_avoidance_triggered(dmg.final_damage, evade_target.hp)
                    and _katashiro_count(evade_target) >= _KATASHIRO_COST
                ):
                    pending_da_id = str(uuid.uuid4())
                    _valid = ("physical", "spiritual")
                    _dmg_type = dmg.damage_type if dmg.damage_type in _valid else "physical"
                    _pending_da = DeathAvoidanceRequest.with_default_deadline(
                        pending_id=pending_da_id,
                        target_character_id=evade_target.id,
                        target_player_id=player_id,
                        incoming_damage=dmg.final_damage,
                        damage_type=_dmg_type,  # type: ignore[arg-type]
                        katashiro_required=_KATASHIRO_COST,
                        katashiro_remaining=_katashiro_count(evade_target),
                        timeout_seconds=_DEATH_AVOIDANCE_TIMEOUT,
                    )
                    state = state.model_copy(
                        update={
                            "pending_actions": [*state.pending_actions, _pending_da],
                            "machine_state": MachineState.AWAITING_PLAYER_INPUT,
                        }
                    )
                    session.state = state
                    death_avoidance_context = {
                        "da_request": _pending_da,
                        "dmg": dmg,
                        "target_id": evade_target.id,
                        "actor_char": actor_char,
                        "weapon": weapon,
                    }
                    break  # Suspend; handle outside the lock.

                new_target = apply_damage(evade_target, dmg)
                state = _replace_character(state, new_target)
                session.state = state
                summary.damage_dealt[evade_target.id] = (
                    summary.damage_dealt.get(evade_target.id, 0) + dmg.final_damage
                )
                narrative_parts.append(
                    f"{actor_char.name}の{weapon.name}が{evade_target.name}に{dmg.final_damage}ダメージ！"
                    f"（残りHP: {new_target.hp}/{new_target.max_hp}）"
                )
                if not new_target.is_alive:
                    narrative_parts.append(f"{evade_target.name}は倒れた！")
                    await _emit_event(
                        websocket, state, "character_died", {"character_id": evade_target.id}
                    )
                evade_target = new_target

        if not death_avoidance_context:
            state = state.model_copy(
                update={
                    "version": state.version + 1,
                    "machine_state": MachineState.NARRATING,
                    "current_turn_summary": summary,
                }
            )
            session.state = state
            await _send_state_update(websocket, state)
            await _emit_event(websocket, state, "turn_ended", {"actor_id": actor_char.id})

            narrative = (
                "\n".join(narrative_parts) if narrative_parts else f"{actor_char.name}は行動した。"
            )
            await _send_narrative(websocket, state, narrative)

            state = _advance_turn(state)
            state = state.model_copy(update={"machine_state": MachineState.IDLE})
            session.state = state
            await _send_state_update(websocket, state)

    # ---------------------------------------------------------------------------
    # Phase 4: Death avoidance flow — outside the lock.
    # ---------------------------------------------------------------------------
    if not death_avoidance_context:
        return

    da_request: DeathAvoidanceRequest = death_avoidance_context["da_request"]
    da_dmg = death_avoidance_context["dmg"]
    da_actor: Character = death_avoidance_context["actor_char"]
    da_weapon = death_avoidance_context["weapon"]
    da_target_id: str = death_avoidance_context["target_id"]

    await _send_ws(
        websocket,
        DeathAvoidanceRequired(
            type="death_avoidance_required",
            event_id=state.next_event_id,
            timestamp=_now(),
            pending_id=da_request.pending_id,
            target_character_id=da_request.target_character_id,
            target_player_id=da_request.target_player_id,
            incoming_damage=da_dmg.final_damage,
            damage_type=da_dmg.damage_type,
            katashiro_required=_KATASHIRO_COST,
            katashiro_remaining=da_request.katashiro_remaining,
            deadline_seconds=_DEATH_AVOIDANCE_TIMEOUT,
        ),
    )

    da_msg = await _wait_for_death_avoidance(websocket, da_request.pending_id)
    choice = da_msg.choice if da_msg is not None else "accept_death"

    async with session.lock.acquire():
        state = session.state
        assert state is not None

        state = state.model_copy(
            update={
                "pending_actions": [
                    p for p in state.pending_actions if p.pending_id != da_request.pending_id
                ],
                "machine_state": MachineState.RESOLVING_ACTION,
            }
        )
        session.state = state

        da_target = state.find_character(da_target_id)
        if da_target is None:
            state = _advance_turn(state)
            state = state.model_copy(update={"machine_state": MachineState.IDLE})
            session.state = state
            return

        if choice == "avoid_death" and _katashiro_count(da_target) >= _KATASHIRO_COST:
            da_target = _consume_katashiro(da_target, _KATASHIRO_COST)
            da_target = da_target.model_copy(update={"hp": 1})
            state = _replace_character(state, da_target)
            session.state = state
            narrative_parts.append(
                f"{da_target.name}は形代{_KATASHIRO_COST}枚を消費して死の淵から生還した！（HP: 1）"
            )
        elif choice == "respawn" and _katashiro_count(da_target) >= _KATASHIRO_COST:
            respawn_point = state.scenario.respawn_point or (0, 0)
            da_target = _consume_katashiro(da_target, _KATASHIRO_COST)
            da_target = _apply_respawn(da_target, respawn_point)
            state = _replace_character(state, da_target)
            session.state = state
            narrative_parts.append(
                f"{da_target.name}は形代{_KATASHIRO_COST}枚を消費してリスポーン地点に転移した！"
                f"（HP: {da_target.hp}/{da_target.max_hp}）"
            )
            await _emit_event(
                websocket, state, "character_respawned", {"character_id": da_target.id}
            )
        else:
            # accept_death or insufficient katashiro — apply damage.
            new_target = apply_damage(da_target, da_dmg)
            state = _replace_character(state, new_target)
            session.state = state
            summary.damage_dealt[da_target.id] = (
                summary.damage_dealt.get(da_target.id, 0) + da_dmg.final_damage
            )
            narrative_parts.append(
                f"{da_actor.name}の{da_weapon.name}が{da_target.name}に{da_dmg.final_damage}ダメージ！"
                f"（残りHP: {new_target.hp}/{new_target.max_hp}）"
            )
            if not new_target.is_alive:
                narrative_parts.append(f"{da_target.name}は倒れた！")
                await _emit_event(
                    websocket, state, "character_died", {"character_id": da_target.id}
                )

        state = state.model_copy(
            update={
                "version": state.version + 1,
                "machine_state": MachineState.NARRATING,
                "current_turn_summary": summary,
            }
        )
        session.state = state
        await _send_state_update(websocket, state)
        await _emit_event(websocket, state, "turn_ended", {"actor_id": da_actor.id})

        narrative = (
            "\n".join(narrative_parts) if narrative_parts else f"{da_actor.name}は行動した。"
        )
        await _send_narrative(websocket, state, narrative)

        state = _advance_turn(state)
        state = state.model_copy(update={"machine_state": MachineState.IDLE})
        session.state = state
        await _send_state_update(websocket, state)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _wait_for_evasion(websocket: WebSocket, pending_id: str) -> SubmitEvasion | None:
    """Wait for the matching submit_evasion; re-raises WebSocketDisconnect."""
    raw = await websocket.receive_text()  # raises WebSocketDisconnect on close
    msg = _parse_client_message(raw)
    if isinstance(msg, SubmitEvasion) and msg.pending_id == pending_id:
        return msg
    return None


def _apply_movement(state: GameState, char_id: str, movement: Movement) -> GameState:
    if not movement.path:
        return state
    new_pos = movement.path[-1]
    char = state.find_character(char_id)
    if char is None:
        return state
    new_char = char.model_copy(update={"position": new_pos})
    return _replace_character(state, new_char)


def _restore_evasion_dice(char: Character) -> Character:
    """Reset evasion_dice to max at the start of the character's turn (§19 rule)."""
    if char.evasion_dice == char.max_evasion_dice:
        return char
    return char.model_copy(update={"evasion_dice": char.max_evasion_dice})


def _consume_evasion_dice(char: Character, dice_used: int) -> Character:
    """Subtract used evasion dice from the character's current pool."""
    if dice_used <= 0:
        return char
    new_dice = max(0, char.evasion_dice - dice_used)
    return char.model_copy(update={"evasion_dice": new_dice})


def _replace_character(state: GameState, updated: Character) -> GameState:
    new_chars = [updated if c.id == updated.id else c for c in state.characters]
    return state.model_copy(update={"characters": new_chars})


def _advance_turn(state: GameState) -> GameState:
    if not state.turn_order:
        return state
    new_idx = (state.current_turn_index + 1) % len(state.turn_order)
    new_round = state.round_number
    if new_idx == 0:
        new_round += 1
    return state.model_copy(update={"current_turn_index": new_idx, "round_number": new_round})


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _next_event_id(state: GameState) -> tuple[int, GameState]:
    eid = state.next_event_id
    return eid, state.model_copy(update={"next_event_id": eid + 1})


async def _emit_event(
    websocket: WebSocket, state: GameState, event_name: str, payload: dict[str, Any]
) -> None:
    eid, _ = _next_event_id(state)
    msg = GameEventMessage(
        type="event",
        event_id=eid,
        timestamp=_now(),
        event_name=event_name,
        payload=payload,
    )
    await _send_ws(websocket, msg)


async def _send_state_update(websocket: WebSocket, state: GameState) -> None:
    msg = StateFull(
        type="state_full",
        event_id=state.next_event_id,
        timestamp=_now(),
        version=state.version,
        state=state.model_dump(mode="json"),
    )
    await _send_ws(websocket, msg)


async def _send_narrative(websocket: WebSocket, state: GameState, text: str) -> None:
    eid, _ = _next_event_id(state)
    msg = GmNarrative(
        type="gm_narrative",
        event_id=eid,
        timestamp=_now(),
        text=text,
    )
    await _send_ws(websocket, msg)


async def _send_error(websocket: WebSocket, code: ErrorCode, message: str) -> None:
    msg = ErrorMessage(
        type="error",
        event_id=0,
        timestamp=_now(),
        code=code,
        message=message,
    )
    await websocket.send_text(msg.model_dump_json())


def _make_error(
    state: GameState,
    code: ErrorCode,
    message: str,
    detail: dict[str, Any] | None = None,
    client_request_id: str | None = None,
) -> ErrorMessage:
    return ErrorMessage(
        type="error",
        event_id=state.next_event_id,
        timestamp=_now(),
        code=code,
        message=message,
        detail=detail,
        client_request_id=client_request_id,
    )


def _parse_client_message(raw: str) -> ClientMessage | None:
    try:
        data = json.loads(raw)
        return _client_message_adapter.validate_python(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Failed to parse client message: %s", exc)
        return None


async def _send_ws(websocket: WebSocket, msg: Any) -> None:
    await websocket.send_text(msg.model_dump_json())


def _render_combat_end(session: RoomSession, outcome: str) -> str:
    if outcome == "victory":
        return "全ての敵を倒した。任務完了だ。"
    return "全滅……。今回は退くしかない。"


# ---------------------------------------------------------------------------
# Phase 4: Style modifiers (§6-7, §19)
# ---------------------------------------------------------------------------

_MELEE_STYLE_MODIFIER: dict[MeleeStyle, int] = {
    MeleeStyle.NONE: 0,
    MeleeStyle.RENGEKI: 0,       # Distribution handled elsewhere; no difficulty shift.
    MeleeStyle.SEIMITSU: -1,     # 精密攻撃: aim carefully → easier to hit.
    MeleeStyle.KYOUKOUGEKI: 1,   # 強攻撃: heavy blow → harder to land.
    MeleeStyle.ZENRYOKU: 1,      # 全力攻撃: all-out → overextended → harder.
}

_RANGED_STYLE_MODIFIER: dict[RangedStyle, int] = {
    RangedStyle.NONE: 0,
    RangedStyle.NIKAI_SHAGEKI: 0,  # 2回射撃: two shots, standard accuracy each.
    RangedStyle.RENSHA: 0,         # 連射: rapid fire spread.
    RangedStyle.RENSHA_II: 0,      # 連射II: more targets, same accuracy.
    RangedStyle.SOGEKI: -2,        # 狙撃: sniper — precise, much easier to hit.
    RangedStyle.NUKIUCHI: 0,       # 抜き撃ち: quick draw, no accuracy trade.
}


def _melee_style_modifier(style: MeleeStyle) -> int:
    return _MELEE_STYLE_MODIFIER.get(style, 0)


def _ranged_style_modifier(style: RangedStyle) -> int:
    return _RANGED_STYLE_MODIFIER.get(style, 0)


# ---------------------------------------------------------------------------
# Phase 4: Death avoidance helpers (§10-2, D34, D36)
# ---------------------------------------------------------------------------

_KATASHIRO_COST = 2
_DEATH_AVOIDANCE_TIMEOUT = 60


def _death_avoidance_triggered(damage: int, current_hp: int) -> bool:
    """True when physical damage exceeds current HP × 2 (GM spec §10-2 / D34)."""
    return damage > current_hp * 2


def _katashiro_count(char: Character) -> int:
    return char.inventory.get("katashiro", 0)


def _consume_katashiro(char: Character, count: int) -> Character:
    current = _katashiro_count(char)
    new_count = max(0, current - count)
    new_inventory = {**char.inventory, "katashiro": new_count}
    return char.model_copy(update={"inventory": new_inventory})


def _apply_respawn(char: Character, respawn_point: tuple[int, int]) -> Character:
    """Half-HP restore, status effects cleared, cannot act this turn (D36)."""
    return char.model_copy(
        update={
            "hp": max(1, char.max_hp // 2),
            "status_effects": [],
            "position": respawn_point,
            "has_acted_this_turn": True,
        }
    )


async def _wait_for_death_avoidance(
    websocket: WebSocket, pending_id: str
) -> SubmitDeathAvoidance | None:
    """Wait for the matching submit_death_avoidance message."""
    raw = await websocket.receive_text()
    msg = _parse_client_message(raw)
    if isinstance(msg, SubmitDeathAvoidance) and msg.pending_id == pending_id:
        return msg
    return None
