"""Phase 5 mechanic tests: 祓魔術, 結界システム, OpenAI互換バックエンド."""

from __future__ import annotations

import json
import pathlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from tacex_gm.ai.backend import Message, ToolDefinition
from tacex_gm.ai.openai_compat import OpenAICompatBackend, _to_openai_tool
from tacex_gm.models.state import Barrier, GameState, MapObject, Pillar, Wire
from tacex_gm.models.turn_action import (
    ActivateBarrier,
    CastArt,
    ConsumeKatashiroForMP,
    DeployWire,
    DispelBarrier,
    PlacePillar,
    Skip,
    TurnAction,
    UseItem,
)
from tacex_gm.system_module.tactical_exorcist.arts import (
    ArtDefinition,
    ArtRegistry,
    can_cast,
    load_art_registry,
    validate_cast_target,
)

_DATA_DIR = pathlib.Path(__file__).parent.parent.parent / "data"


@pytest.fixture(scope="module")
def registry() -> ArtRegistry:
    return load_art_registry(_DATA_DIR)


# ---------------------------------------------------------------------------
# Arts registry
# ---------------------------------------------------------------------------


class TestArtRegistry:
    def test_all_six_arts_loaded(self, registry: ArtRegistry):
        expected = {"加護防壁", "反閃歩法", "霊力放出", "霊弾発射", "呪祝詛詞", "式神使役"}
        assert set(registry.all_names()) == expected

    def test_get_known_art(self, registry: ArtRegistry):
        art = registry.get("加護防壁")
        assert art is not None
        assert art.name == "加護防壁"

    def test_get_unknown_art_returns_none(self, registry: ArtRegistry):
        assert registry.get("存在しない術") is None

    def test_contains_known_art(self, registry: ArtRegistry):
        assert "霊弾発射" in registry

    def test_mp_cost_is_positive(self, registry: ArtRegistry):
        for name in registry.all_names():
            art = registry.get(name)
            assert art is not None
            assert art.mp_cost >= 1

    def test_mp_cost_lookup(self, registry: ArtRegistry):
        assert registry.mp_cost("加護防壁") == 2

    def test_mp_cost_unknown_raises(self, registry: ArtRegistry):
        with pytest.raises(KeyError):
            registry.mp_cost("存在しない術")


class TestCanCast:
    def test_can_cast_when_mp_sufficient(self):
        art = ArtDefinition(name="test", mp_cost=2, target_type="self", description="x")
        assert can_cast(art, current_mp=2) is True

    def test_can_cast_with_excess_mp(self):
        art = ArtDefinition(name="test", mp_cost=2, target_type="self", description="x")
        assert can_cast(art, current_mp=5) is True

    def test_cannot_cast_when_mp_insufficient(self):
        art = ArtDefinition(name="test", mp_cost=3, target_type="self", description="x")
        assert can_cast(art, current_mp=2) is False

    def test_cannot_cast_with_zero_mp(self):
        art = ArtDefinition(name="test", mp_cost=1, target_type="self", description="x")
        assert can_cast(art, current_mp=0) is False


class TestValidateCastTarget:
    def test_single_art_requires_target(self):
        art = ArtDefinition(name="test", mp_cost=1, target_type="single", description="x")
        err = validate_cast_target(art, target=None)
        assert err is not None

    def test_single_art_with_target_is_ok(self):
        art = ArtDefinition(name="test", mp_cost=1, target_type="single", description="x")
        assert validate_cast_target(art, target="enemy-1") is None

    def test_self_art_rejects_target(self):
        art = ArtDefinition(name="test", mp_cost=1, target_type="self", description="x")
        err = validate_cast_target(art, target="ally-1")
        assert err is not None

    def test_self_art_without_target_is_ok(self):
        art = ArtDefinition(name="test", mp_cost=1, target_type="self", description="x")
        assert validate_cast_target(art, target=None) is None

    def test_none_art_rejects_target(self):
        art = ArtDefinition(name="test", mp_cost=1, target_type="none", description="x")
        assert validate_cast_target(art, target="x") is not None

    def test_area_art_allows_no_target(self):
        art = ArtDefinition(name="test", mp_cost=1, target_type="area", description="x")
        assert validate_cast_target(art, target=None) is None


# ---------------------------------------------------------------------------
# Phase 5 action models
# ---------------------------------------------------------------------------


class TestCastArt:
    def test_cast_art_round_trips(self):
        action = CastArt(art_name="加護防壁", target="pc1")
        data = action.model_dump()
        restored = CastArt.model_validate(data)
        assert restored.art_name == "加護防壁"
        assert restored.target == "pc1"

    def test_cast_art_no_target(self):
        action = CastArt(art_name="反閃歩法")
        assert action.target is None

    def test_cast_art_with_center_position(self):
        action = CastArt(art_name="霊力放出", center_position=(5, 5))
        assert action.center_position == (5, 5)


class TestDeployWire:
    def test_deploy_wire_round_trips(self):
        action = DeployWire(pillar_id="pillar-a")
        assert action.type == "deploy_wire"
        assert action.pillar_id == "pillar-a"


class TestDispelBarrier:
    def test_dispel_barrier_round_trips(self):
        action = DispelBarrier(barrier_id="barrier-x")
        assert action.type == "dispel_barrier"
        assert action.barrier_id == "barrier-x"


class TestUseItem:
    def test_use_item_with_target(self):
        action = UseItem(item_name="霊符", target="pc1")
        assert action.item_name == "霊符"
        assert action.target == "pc1"

    def test_use_item_no_target(self):
        action = UseItem(item_name="回復薬")
        assert action.target is None


class TestSubActions:
    def test_place_pillar(self):
        sub = PlacePillar(position=(3, 4))
        assert sub.type == "place_pillar"
        assert sub.position == (3, 4)

    def test_activate_barrier(self):
        sub = ActivateBarrier(pillar_id="p1", effect="barrier_wall")
        assert sub.type == "activate_barrier"
        assert sub.effect == "barrier_wall"

    def test_consume_katashiro_mp(self):
        sub = ConsumeKatashiroForMP()
        assert sub.type == "consume_katashiro_mp"

    def test_turn_action_with_sub_actions(self):
        action = TurnAction(
            actor_id="pc1",
            main_action=Skip(),
            sub_actions=[PlacePillar(position=(1, 2))],
        )
        assert len(action.sub_actions) == 1
        assert isinstance(action.sub_actions[0], PlacePillar)

    def test_turn_action_discriminator_routes_correctly(self):
        raw = {
            "actor_id": "pc1",
            "main_action": {"type": "cast_art", "art_name": "加護防壁", "target": "pc2"},
            "sub_actions": [
                {"type": "place_pillar", "position": [3, 4]},
                {"type": "activate_barrier", "pillar_id": "p1", "effect": "armor_dissolve"},
            ],
        }
        ta = TurnAction.model_validate(raw)
        assert isinstance(ta.main_action, CastArt)
        assert ta.main_action.art_name == "加護防壁"
        assert isinstance(ta.sub_actions[0], PlacePillar)
        assert isinstance(ta.sub_actions[1], ActivateBarrier)


# ---------------------------------------------------------------------------
# GameState with Pillar / Wire / Barrier / MapObject
# ---------------------------------------------------------------------------


def _minimal_state() -> dict:
    from tacex_gm.models.scenario import Scenario

    return {
        "room_id": "room-1",
        "seed": 0,
        "map_size": (20, 20),
        "scenario": Scenario(
            scenario_id="test",
            title="テスト",
            map_size=(20, 20),
        ),
    }


class TestPillarModel:
    def test_pillar_round_trips(self):
        p = Pillar(id="p1", owner_id="pc1", position=(3, 4))
        assert p.is_active is True
        restored = Pillar.model_validate(p.model_dump())
        assert restored.position == (3, 4)


class TestWireModel:
    def test_wire_round_trips(self):
        w = Wire(id="w1", pillar_a_id="p1", pillar_b_id="p2")
        assert w.pillar_a_id == "p1"


class TestBarrierModel:
    def test_barrier_round_trips(self):
        b = Barrier(id="b1", wire_id="w1", effect="barrier_wall", owner_id="pc1")
        assert b.effect == "barrier_wall"
        assert b.is_active is True


class TestMapObjectModel:
    def test_map_object_defaults(self):
        obj = MapObject(id="obj1", position=(5, 5), strength=3)
        assert obj.armor == 0
        assert obj.label == ""


class TestGameStatePhase5Fields:
    def test_game_state_has_phase5_fields(self):
        state = GameState(**_minimal_state())
        assert state.pillars == []
        assert state.wires == []
        assert state.barriers == []
        assert state.objects == []

    def test_find_pillar(self):
        state = GameState(
            **_minimal_state(),
            pillars=[Pillar(id="p1", owner_id="pc1", position=(1, 1))],
        )
        assert state.find_pillar("p1") is not None
        assert state.find_pillar("missing") is None

    def test_find_barrier(self):
        state = GameState(
            **_minimal_state(),
            barriers=[Barrier(id="b1", wire_id="w1", effect="evasion_block", owner_id="pc1")],
        )
        assert state.find_barrier("b1") is not None
        assert state.find_barrier("missing") is None

    def test_find_wire(self):
        state = GameState(
            **_minimal_state(),
            wires=[Wire(id="w1", pillar_a_id="p1", pillar_b_id="p2")],
        )
        assert state.find_wire("w1") is not None
        assert state.find_wire("missing") is None


# ---------------------------------------------------------------------------
# OpenAI-compat backend (unit — no real HTTP)
# ---------------------------------------------------------------------------


class TestOpenAICompatToolTranslation:
    def test_tool_definition_translates_to_openai_format(self):
        tool = ToolDefinition(
            name="do_simple_attack",
            description="攻撃する",
            input_schema={"type": "object", "properties": {"target_id": {"type": "string"}}},
        )
        result = _to_openai_tool(tool)
        assert result["type"] == "function"
        assert result["function"]["name"] == "do_simple_attack"
        assert "parameters" in result["function"]
        assert result["function"]["parameters"] == tool.input_schema

    def test_backend_name(self):
        backend = OpenAICompatBackend(api_key="test", model="gpt-4o")
        assert backend.name == "openai_compat"


@pytest.mark.asyncio
class TestOpenAICompatChatCompletion:
    async def test_text_response(self):
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "テストナラティブ"
        mock_choice.message.tool_calls = None
        mock_choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        backend = OpenAICompatBackend(client=mock_client)
        result = await backend.chat_completion(
            messages=[Message(role="user", content="こんにちは")],
        )
        assert result.text == "テストナラティブ"
        assert result.stop_reason == "end_turn"
        assert result.usage.input_tokens == 10
        assert result.usage.output_tokens == 20

    async def test_tool_call_response(self):
        mock_client = MagicMock()
        mock_tc = MagicMock()
        mock_tc.id = "call_abc"
        mock_tc.function.name = "do_simple_attack"
        mock_tc.function.arguments = json.dumps({"target_id": "enemy-1"})

        mock_choice = MagicMock()
        mock_choice.message.content = ""
        mock_choice.message.tool_calls = [mock_tc]
        mock_choice.finish_reason = "tool_calls"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 15
        mock_response.usage.completion_tokens = 5

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        backend = OpenAICompatBackend(client=mock_client)
        result = await backend.chat_completion(
            messages=[Message(role="user", content="攻撃して")],
            tools=[
                ToolDefinition(
                    name="do_simple_attack",
                    description="攻撃する",
                    input_schema={"type": "object"},
                )
            ],
        )
        assert result.stop_reason == "tool_use"
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "do_simple_attack"
        assert result.tool_calls[0].input == {"target_id": "enemy-1"}

    async def test_system_prompt_injected(self):
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "ok"
        mock_choice.message.tool_calls = None
        mock_choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = None

        captured: list[list[dict]] = []

        async def fake_create(**kwargs):
            captured.append(kwargs["messages"])
            return mock_response

        mock_client.chat.completions.create = fake_create

        backend = OpenAICompatBackend(client=mock_client)
        await backend.chat_completion(
            messages=[Message(role="user", content="hello")],
            system="あなたはGMです",
        )
        assert captured[0][0]["role"] == "system"
        assert captured[0][0]["content"] == "あなたはGMです"

    async def test_api_error_raises_backend_error(self):
        from openai import APIError

        from tacex_gm.ai.backend import LLMBackendError

        mock_client = MagicMock()

        async def fail(**kwargs):
            raise APIError("boom", request=MagicMock(), body=None)

        mock_client.chat.completions.create = fail

        backend = OpenAICompatBackend(client=mock_client)
        with pytest.raises(LLMBackendError):
            await backend.chat_completion(messages=[Message(role="user", content="hi")])
