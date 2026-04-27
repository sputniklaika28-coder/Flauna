"""Victory / failure condition checker (GM spec §14-3, §15-3).

Phase 2 MVP supports:
- ``all_enemies_defeated`` → victory
- ``all_pcs_defeated``    → defeat

Phase 6+ conditions (``round_reached``, ``reach_zone``, etc.) are not yet
evaluated; the presence of such conditions is silently ignored.
"""

from __future__ import annotations

from typing import Literal

from tacex_gm.models import GameState
from tacex_gm.models.scenario import (
    FailureAllPCsDefeated,
    VictoryAllEnemiesDefeated,
)

CombatOutcome = Literal["victory", "defeat", None]


def check_combat_outcome(state: GameState) -> CombatOutcome:
    """Return ``'victory'``, ``'defeat'``, or ``None`` (still going)."""

    enemies = [c for c in state.characters if c.faction == "enemy"]
    pcs = [c for c in state.characters if c.faction == "pc"]

    for vc in state.scenario.victory_conditions:
        if (
            isinstance(vc, VictoryAllEnemiesDefeated)
            and enemies
            and all(not c.is_alive for c in enemies)
        ):
            return "victory"

    for fc in state.scenario.failure_conditions:
        if isinstance(fc, FailureAllPCsDefeated) and pcs and all(not c.is_alive for c in pcs):
            return "defeat"

    return None
