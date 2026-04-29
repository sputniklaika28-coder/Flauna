"""Cast-art resolution helpers (Phase 8 — multi-art mastery).

This module wires :class:`~tacex_gm.models.turn_action.CastArt` actions to
the art registry: it validates that the actor has learned the art, pays
the MP cost, and returns a small structured outcome that the WS handler
or assessment systems can fold into the broader turn resolution.
"""

from __future__ import annotations

from dataclasses import dataclass

from tacex_gm.models.character import Character
from tacex_gm.models.turn_action import CastArt
from tacex_gm.system_module.tactical_exorcist.arts import (
    ArtRegistry,
    validate_cast_target,
    validate_caster,
)


@dataclass(frozen=True)
class CastArtResolution:
    """Result of attempting to resolve a CastArt action."""

    success: bool
    error: str | None
    art_name: str
    mp_spent: int
    updated_caster: Character | None
    narrative: str


def resolve_cast_art(
    actor: Character,
    action: CastArt,
    registry: ArtRegistry,
) -> CastArtResolution:
    """Validate and (on success) apply the MP cost of *action*.

    The function intentionally does **not** apply the art's gameplay
    effect (damage, status, summon) — that's left to dedicated effect
    handlers introduced incrementally.  Phase 8's contribution is
    covering the *prerequisites* uniformly so a character with multiple
    learned arts can switch between them safely.
    """
    art = registry.get(action.art_name)
    if art is None:
        return CastArtResolution(
            success=False,
            error=f"Unknown art: {action.art_name}",
            art_name=action.art_name,
            mp_spent=0,
            updated_caster=None,
            narrative="",
        )

    target_error = validate_cast_target(art, action.target)
    if target_error is not None:
        return CastArtResolution(
            success=False,
            error=target_error,
            art_name=art.name,
            mp_spent=0,
            updated_caster=None,
            narrative="",
        )

    caster_error = validate_caster(actor, art)
    if caster_error is not None:
        return CastArtResolution(
            success=False,
            error=caster_error,
            art_name=art.name,
            mp_spent=0,
            updated_caster=None,
            narrative="",
        )

    new_mp = max(0, actor.mp - art.mp_cost)
    updated = actor.model_copy(update={"mp": new_mp})
    narrative = f"{actor.name}は『{art.name}』を発動した。（MP -{art.mp_cost}）"
    return CastArtResolution(
        success=True,
        error=None,
        art_name=art.name,
        mp_spent=art.mp_cost,
        updated_caster=updated,
        narrative=narrative,
    )
