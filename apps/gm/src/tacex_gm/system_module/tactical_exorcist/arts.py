"""祓魔術 (exorcism arts) loader and validator (Phase 5, GM spec §6-5).

Arts are loaded once at startup from ``data/arts.yaml``.  The module exposes a
single registry object and lookup helpers used by the rule engine when
processing :class:`~tacex_gm.models.turn_action.CastArt` actions.
"""

from __future__ import annotations

import pathlib
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

ArtName = Literal["加護防壁", "反閃歩法", "霊力放出", "霊弾発射", "呪祝詛詞", "式神使役"]
TargetType = Literal["none", "single", "area", "self"]

_DATA_DIR = pathlib.Path(__file__).parent.parent.parent.parent.parent / "data"


class ArtDefinition(BaseModel):
    """Single art entry as loaded from arts.yaml."""

    name: str
    mp_cost: int = Field(ge=1)
    target_type: TargetType
    description: str
    effect: dict[str, Any] = Field(default_factory=dict)


class ArtRegistry:
    """In-memory registry of all art definitions."""

    def __init__(self, arts: list[ArtDefinition]) -> None:
        self._by_name: dict[str, ArtDefinition] = {a.name: a for a in arts}

    def get(self, name: str) -> ArtDefinition | None:
        return self._by_name.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._by_name

    def all_names(self) -> list[str]:
        return list(self._by_name)

    def mp_cost(self, name: str) -> int:
        art = self._by_name.get(name)
        if art is None:
            raise KeyError(f"Unknown art: {name!r}")
        return art.mp_cost


def load_art_registry(data_dir: pathlib.Path | None = None) -> ArtRegistry:
    """Load arts from ``arts.yaml`` in *data_dir* (defaults to the package data dir)."""

    path = (data_dir or _DATA_DIR) / "arts.yaml"
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    arts = [ArtDefinition.model_validate(entry) for entry in raw.get("arts", [])]
    return ArtRegistry(arts)


def can_cast(art: ArtDefinition, current_mp: int) -> bool:
    """Return True if the caster has enough MP to cast *art*."""

    return current_mp >= art.mp_cost


def validate_cast_target(art: ArtDefinition, target: str | None) -> str | None:
    """Return an error string if the target spec is invalid for *art*, else None."""

    if art.target_type in ("single",) and target is None:
        return f"Art '{art.name}' requires a target_id"
    if art.target_type in ("none", "self") and target is not None:
        return f"Art '{art.name}' does not accept a target_id"
    return None


# ---------------------------------------------------------------------------
# Phase 8: 複数術修得 — multi-art mastery validation
# ---------------------------------------------------------------------------


def known_arts(character: object) -> list[str]:
    """Return the list of arts the character has learned.

    Accepts anything with an ``arts`` attribute (typically
    :class:`~tacex_gm.models.character.Character`).  Lookups elsewhere can
    rely on this helper instead of reaching into the model directly.
    """
    arts = getattr(character, "arts", None)
    if not isinstance(arts, list):
        return []
    return [str(a) for a in arts]


def caster_knows_art(character: object, art_name: str) -> bool:
    """True iff the character has learned *art_name* (Phase 8)."""
    return art_name in known_arts(character)


def validate_caster(
    character: object,
    art: ArtDefinition,
) -> str | None:
    """Aggregate prerequisite check for casting *art*.

    Validates, in order:
    1. The caster has the art in their known list (multi-art mastery).
    2. The caster has the 祓魔の心得 skill (基礎前提, spec §6-5).
    3. The caster has 祓魔術ランク (jutsu) ≥ 1.
    4. The caster has enough MP.

    Returns the first failing reason as a Japanese error message, or None
    if all checks pass.
    """
    if not caster_knows_art(character, art.name):
        return f"術者は '{art.name}' を修得していません"

    skills = getattr(character, "skills", []) or []
    if "祓魔の心得" not in skills:
        return "術者は『祓魔の心得』を持っていません"

    jutsu = getattr(character, "jutsu", 0) or 0
    if jutsu < 1:
        return "術者の祓魔術ランクが不足しています"

    current_mp = getattr(character, "mp", 0) or 0
    if current_mp < art.mp_cost:
        return f"MPが不足しています（必要 {art.mp_cost}, 現在 {current_mp}）"

    return None
