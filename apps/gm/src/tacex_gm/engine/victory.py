"""Victory / failure condition checker (GM spec §14-3, §15-3).

Phase 2 MVP:
- ``all_enemies_defeated`` → victory
- ``all_pcs_defeated``    → defeat

Phase 7 adds:
- ``reach_zone``   → victory when any qualifying character enters the zone
- ``round_limit``  → defeat when the round counter exceeds the limit
"""

from __future__ import annotations

from typing import Literal

from tacex_gm.models import GameState
from tacex_gm.models.scenario import (
    FailureAllPCsDefeated,
    FailureRoundLimit,
    VictoryAllEnemiesDefeated,
    VictoryReachZone,
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

        if isinstance(vc, VictoryReachZone):
            (x0, y0), (x1, y1) = vc.zone
            who = vc.who
            for c in state.characters:
                if not c.is_alive:
                    continue
                if "any_pc" in who and c.faction != "pc":
                    continue
                if "any_pc" not in who and c.id not in who:
                    continue
                x, y = c.position
                if min(x0, x1) <= x <= max(x0, x1) and min(y0, y1) <= y <= max(y0, y1):
                    return "victory"

    for fc in state.scenario.failure_conditions:
        if isinstance(fc, FailureAllPCsDefeated) and pcs and all(not c.is_alive for c in pcs):
            return "defeat"

        if isinstance(fc, FailureRoundLimit) and state.round_number > fc.round:
            return "defeat"

    return None
