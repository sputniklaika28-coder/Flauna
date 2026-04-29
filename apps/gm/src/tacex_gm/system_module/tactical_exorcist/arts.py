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
