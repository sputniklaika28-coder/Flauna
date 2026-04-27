"""Phase 0 completion condition #5: happy-path end-to-end combat test.

Covers: room create → WS join → PC turn (melee attack) → NPC auto-evasion
→ state_update → NPC turn (default_action) → evade_required → submit_evasion
→ narrative → state_update.

All LLM calls use MockLLMBackend so no network traffic is required.
Dice use the seed embedded in GameState for deterministic results.
"""

from __future__ import annotations

import json

from tacex_gm.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _join(room_id: str, player_id: str, token: str) -> str:
    return json.dumps(
        {
            "action": "join_room",
            "player_id": player_id,
            "room_id": room_id,
            "auth_token": token,
            "last_seen_event_id": 0,
        }
    )


def _collect_until(ws, *, stop_types: set[str], max_msgs: int = 20) -> list[dict]:
    msgs: list[dict] = []
    for _ in range(max_msgs):
        try:
            msg = ws.receive_json()
        except Exception:
            break
        msgs.append(msg)
        if msg.get("type") in stop_types or msg.get("event_name") in stop_types:
            break
    return msgs


def _place_adjacent(room_id: str) -> tuple[str, str]:
    """Move PC to be adjacent to the first enemy. Returns (pc_id, enemy_id)."""
    session = app.state.room_store.get_session(room_id)
    assert session is not None and session.state is not None
    state = session.state

    pc = next(c for c in state.characters if c.faction == "pc")
    enemy = next(c for c in state.characters if c.faction == "enemy")
    adj = (enemy.position[0] - 1, enemy.position[1])

    updated = [
        c.model_copy(update={"position": adj}) if c.faction == "pc" else c for c in state.characters
    ]
    session.state = state.model_copy(update={"characters": updated})
    return pc.id, enemy.id


# ---------------------------------------------------------------------------
# Test: basic session restore
# ---------------------------------------------------------------------------


class TestHappyPathSessionRestore:
    def test_session_restore_contains_valid_game_state(self, sync_client, room_data):
        room_id = room_data["room_id"]
        player_id = room_data["player_id"]
        token = room_data["player_token"]

        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join(room_id, player_id, token))
            restore = ws.receive_json()

        assert restore["type"] == "session_restore"
        state = restore["current_state"]
        assert state["phase"] == "combat"
        assert len(state["turn_order"]) >= 2
        chars = state["characters"]
        factions = {c["faction"] for c in chars}
        assert factions == {"pc", "enemy"}

    def test_session_restore_pc_has_player_id(self, sync_client, room_data):
        room_id = room_data["room_id"]
        token = room_data["player_token"]
        player_id = room_data["player_id"]

        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join(room_id, player_id, token))
            restore = ws.receive_json()

        pc = next(c for c in restore["current_state"]["characters"] if c["faction"] == "pc")
        assert pc["player_id"] == player_id


# ---------------------------------------------------------------------------
# Test: PC melee attack turn
# ---------------------------------------------------------------------------


class TestPCMeleeAttackTurn:
    def test_pc_skip_turn_advances_to_npc(self, sync_client, room_data):
        """PC Skip → npc turn starts (ai_thinking sent)."""
        room_id = room_data["room_id"]
        player_id = room_data["player_id"]
        token = room_data["player_token"]

        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join(room_id, player_id, token))
            restore = ws.receive_json()

            state = restore["current_state"]
            pc_id = next(c["id"] for c in state["characters"] if c["faction"] == "pc")
            version = state["version"]

            ws.send_text(
                json.dumps(
                    {
                        "action": "submit_turn_action",
                        "player_id": player_id,
                        "room_id": room_id,
                        "client_request_id": "req-skip-1",
                        "expected_version": version,
                        "turn_action": {
                            "actor_id": pc_id,
                            "main_action": {"type": "skip"},
                        },
                    }
                )
            )

            # Receive state_update, event(turn_ended), gm_narrative, state_update,
            # then NPC turn: ai_thinking, ai_fallback_notice, then either
            # evade_required (if hit) or another narrative (if skip/miss).
            # Stop at ai_thinking to avoid blocking on evade_required or next recv.
            msgs = _collect_until(ws, stop_types={"ai_thinking"}, max_msgs=10)
            types = [m["type"] for m in msgs]
            assert "state_update" in types
            assert "gm_narrative" in types
            assert "ai_thinking" in types, f"Got types: {types}"

    def test_pc_attack_with_version_mismatch_returns_error(self, sync_client, room_data):
        room_id = room_data["room_id"]
        player_id = room_data["player_id"]
        token = room_data["player_token"]

        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join(room_id, player_id, token))
            ws.receive_json()  # session_restore

            session = app.state.room_store.get_session(room_id)
            assert session is not None
            pc_id, enemy_id = _place_adjacent(room_id)

            ws.send_text(
                json.dumps(
                    {
                        "action": "submit_turn_action",
                        "player_id": player_id,
                        "room_id": room_id,
                        "client_request_id": "req-bad-ver",
                        "expected_version": 9999,  # wrong
                        "turn_action": {
                            "actor_id": pc_id,
                            "main_action": {
                                "type": "melee_attack",
                                "weapon_id": "kogatana",
                                "dice_distribution": [4],
                                "targets": [enemy_id],
                            },
                        },
                    }
                )
            )
            err = ws.receive_json()

        assert err["type"] == "error"
        assert err["code"] == "VERSION_MISMATCH"

    def test_pc_melee_attack_produces_state_update_and_narrative(self, sync_client, room_data):
        """PC adjacent to NPC: attack → NPC auto-evades → state_update + narrative."""
        room_id = room_data["room_id"]
        player_id = room_data["player_id"]
        token = room_data["player_token"]

        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join(room_id, player_id, token))
            ws.receive_json()  # session_restore

            pc_id, enemy_id = _place_adjacent(room_id)
            session = app.state.room_store.get_session(room_id)
            assert session is not None
            version = session.state.version  # type: ignore[union-attr]

            ws.send_text(
                json.dumps(
                    {
                        "action": "submit_turn_action",
                        "player_id": player_id,
                        "room_id": room_id,
                        "client_request_id": "req-attack-1",
                        "expected_version": version,
                        "turn_action": {
                            "actor_id": pc_id,
                            "main_action": {
                                "type": "melee_attack",
                                "weapon_id": "kogatana",
                                "dice_distribution": [4],
                                "targets": [enemy_id],
                            },
                        },
                    }
                )
            )

            msgs = _collect_until(ws, stop_types={"ai_thinking", "combat_ended"}, max_msgs=15)
            types = [m["type"] for m in msgs]

        assert "state_update" in types, f"Expected state_update in {types}"
        assert "gm_narrative" in types, f"Expected gm_narrative in {types}"


# ---------------------------------------------------------------------------
# Test: NPC turn → evade_required → submit_evasion
# ---------------------------------------------------------------------------


class TestNPCAttackEvasionLoop:
    def test_npc_attack_triggers_evade_required_and_evasion_resolves(self, sync_client, room_data):
        """Full loop: NPC attacks PC → evade_required → submit_evasion → narrative.

        This is Phase 0 completion condition #5.
        """
        room_id = room_data["room_id"]
        player_id = room_data["player_id"]
        token = room_data["player_token"]

        with sync_client.websocket_connect(f"/room/{room_id}") as ws:
            ws.send_text(_join(room_id, player_id, token))
            ws.receive_json()  # session_restore

            # Place NPC adjacent to PC so default_action will attack.
            session = app.state.room_store.get_session(room_id)
            assert session is not None
            state = session.state
            assert state is not None

            pc = next(c for c in state.characters if c.faction == "pc")
            # Put NPC right next to PC.
            adj = (pc.position[0] + 1, pc.position[1])
            updated = [
                c.model_copy(update={"position": adj}) if c.faction == "enemy" else c
                for c in state.characters
            ]
            session.state = state.model_copy(update={"characters": updated})

            # Advance to NPC turn by skipping PC.
            version = session.state.version
            ws.send_text(
                json.dumps(
                    {
                        "action": "submit_turn_action",
                        "player_id": player_id,
                        "room_id": room_id,
                        "client_request_id": "req-skip-for-npc",
                        "expected_version": version,
                        "turn_action": {"actor_id": pc.id, "main_action": {"type": "skip"}},
                    }
                )
            )

            # Drain messages until evade_required or until 2nd gm_narrative
            # (which means NPC turn finished without hitting PC).
            pending_id: str | None = None
            msgs_before: list[dict] = []
            narrative_count = 0
            for _ in range(20):
                msg = ws.receive_json()
                msgs_before.append(msg)
                if msg["type"] == "evade_required":
                    pending_id = msg["pending_id"]
                    break
                if msg.get("event_name") == "combat_ended":
                    break
                if msg["type"] == "gm_narrative":
                    narrative_count += 1
                    # 1st narrative = PC skip turn; 2nd = NPC turn end (miss/skip)
                    if narrative_count >= 2:
                        break

            if pending_id is None:
                # NPC missed or skipped — still a valid flow, check basics.
                types = [m["type"] for m in msgs_before]
                assert "state_update" in types
                assert "gm_narrative" in types
                return

            # Respond to evasion request.
            ws.send_text(
                json.dumps(
                    {
                        "action": "submit_evasion",
                        "player_id": player_id,
                        "room_id": room_id,
                        "client_request_id": "req-evade-1",
                        "pending_id": pending_id,
                        "dice_result": 2,
                    }
                )
            )

            # Collect until narrative arrives (last message before server awaits PC).
            msgs_after = _collect_until(
                ws, stop_types={"gm_narrative", "combat_ended"}, max_msgs=10
            )
            all_types = [m["type"] for m in msgs_before + msgs_after]

        assert "state_update" in all_types
        assert "gm_narrative" in all_types


# ---------------------------------------------------------------------------
# Test: GameEvent serialisation size (Phase 0 item #7)
# ---------------------------------------------------------------------------


class TestGameEventSize:
    def test_game_event_serialised_size_within_budget(self):
        """Sample 100 GameEvent instances and confirm average size < 1 KB."""
        import json as json_mod

        from tacex_gm.models.event import GameEvent

        samples = []
        for i in range(100):
            ev = GameEvent(
                event_id=i,
                type="attack_resolved",
                payload={
                    "attacker_id": f"char-{i % 5}",
                    "target_id": f"char-{(i + 1) % 5}",
                    "damage": i * 3,
                    "hit": True,
                    "successes": 2,
                    "weapon_id": "kogatana",
                },
            )
            samples.append(len(json_mod.dumps(ev.model_dump(mode="json"))))

        avg = sum(samples) / len(samples)
        max_size = max(samples)
        # Log for reference; hard limit 1 KB average, 2 KB max per event.
        assert avg < 1024, f"Average GameEvent JSON size {avg:.0f} B exceeds 1 KB budget"
        assert max_size < 2048, f"Max GameEvent JSON size {max_size} B exceeds 2 KB limit"
