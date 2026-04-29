"""Assessment phase logic (GM spec §15, Phase 7).

Entered after combat resolves to 'victory' or 'defeat'.
Calculates a session score and proposes growth opportunities for PC characters.
"""

from __future__ import annotations

from typing import Literal

from tacex_gm.models.assessment import Grade, SessionScore
from tacex_gm.models.state import GameState


def _compute_grade(
    outcome: Literal["victory", "defeat"],
    rounds_taken: int,
    pcs_alive: int,
    pcs_total: int,
) -> Grade:
    if outcome == "defeat":
        return "D"
    survival_rate = pcs_alive / pcs_total if pcs_total > 0 else 0.0
    if survival_rate == 1.0 and rounds_taken <= 5:
        return "S"
    if survival_rate >= 0.75:
        return "A"
    if survival_rate >= 0.5:
        return "B"
    if survival_rate > 0.0:
        return "C"
    return "D"


def score_session(
    state: GameState,
    outcome: Literal["victory", "defeat"],
) -> SessionScore:
    """Derive a SessionScore from the current GameState."""
    pcs = [c for c in state.characters if c.faction == "pc"]
    enemies = [c for c in state.characters if c.faction == "enemy"]
    pcs_alive = sum(1 for c in pcs if c.is_alive)
    enemies_defeated = sum(1 for c in enemies if not c.is_alive)
    grade = _compute_grade(outcome, state.round_number, pcs_alive, len(pcs))
    return SessionScore(
        outcome=outcome,
        rounds_taken=state.round_number,
        pcs_alive=pcs_alive,
        pcs_total=len(pcs),
        enemies_defeated=enemies_defeated,
        enemies_total=len(enemies),
        grade=grade,
    )


def enter_assessment(
    state: GameState,
    outcome: Literal["victory", "defeat"],
) -> tuple[GameState, SessionScore]:
    """Transition state to assessment phase and compute the session score.

    Returns the updated GameState and the SessionScore.
    """
    score = score_session(state, outcome)
    new_state = state.model_copy(
        update={
            "phase": "assessment",
            "assessment_result": score,
        }
    )
    return new_state, score
