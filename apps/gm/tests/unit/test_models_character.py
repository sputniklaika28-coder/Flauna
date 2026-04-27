from __future__ import annotations

import pytest
from pydantic import ValidationError

from tacex_gm.models import Character


def _base_kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = dict(
        id="char-1",
        name="アリス",
        player_id="player-1",
        faction="pc",
        tai=4,
        rei=3,
        kou=5,
        jutsu=1,
        max_hp=20,
        max_mp=4,
        hp=20,
        mp=4,
        evasion_dice=3,
        max_evasion_dice=3,
        position=(5, 5),
    )
    base.update(overrides)
    return base


class TestCharacter:
    def test_default_pc(self) -> None:
        c = Character(**_base_kwargs())  # type: ignore[arg-type]
        assert c.is_alive
        assert c.faction == "pc"
        # mobility = ceil(max(tai, kou)/2) = ceil(5/2) = 3
        assert c.mobility == 3

    def test_mobility_floor_at_2(self) -> None:
        c = Character(**_base_kwargs(tai=1, kou=1, jutsu=0, max_mp=0, mp=0))  # type: ignore[arg-type]
        assert c.mobility == 2

    def test_hp_cannot_exceed_max(self) -> None:
        with pytest.raises(ValidationError):
            Character(**_base_kwargs(hp=999))  # type: ignore[arg-type]

    def test_pc_requires_player_id(self) -> None:
        with pytest.raises(ValidationError):
            Character(**_base_kwargs(faction="pc", player_id=None))  # type: ignore[arg-type]

    def test_enemy_must_not_have_player_id(self) -> None:
        with pytest.raises(ValidationError):
            Character(**_base_kwargs(faction="enemy"))  # type: ignore[arg-type]

    def test_enemy_without_player_id_ok(self) -> None:
        c = Character(**_base_kwargs(faction="enemy", player_id=None))  # type: ignore[arg-type]
        assert c.player_id is None
        assert c.faction == "enemy"

    def test_dead_when_hp_zero(self) -> None:
        c = Character(**_base_kwargs(hp=0))  # type: ignore[arg-type]
        assert not c.is_alive
