"""NPC evasion heuristic (GM spec §10-4).

NPCs do not have a human player to decide how many dice to roll; instead
the heuristic inspects the character's ``evasion_policy`` and the
incoming attacks to choose a number of evasion dice.

Decision logic (simplified for Phase 2 MVP):
1. Sum the expected damage from all incoming attacks.
2. If the character has no dice left or no policy, use 0.
3. Otherwise spend ``min(available, ceil(aggression * available))`` dice,
   but always keep at least ``save_dice_threshold`` in reserve *if possible*.
"""

from __future__ import annotations

import math

from tacex_gm.models import Character
from tacex_gm.models.pending import IncomingAttack


def npc_decide_evasion_dice(
    character: Character,
    incoming_attacks: list[IncomingAttack],
) -> int:
    """Return the number of evasion dice the NPC will use.

    The returned value is clamped to ``[0, character.evasion_dice]``.
    """

    available = character.evasion_dice
    if available <= 0:
        return 0

    policy = character.evasion_policy
    if policy is None:
        # No policy: use all available dice (defensive default).
        return available

    # Compute expected total damage to gauge urgency.
    expected_damage = _expected_total_damage(incoming_attacks)
    if expected_damage == 0:
        return 0

    # How many dice the policy wants to spend.
    spend = math.ceil(policy.aggression * available)

    # Reserve at least save_dice_threshold, but not if it leaves nothing.
    reserve = min(policy.save_dice_threshold, available - 1) if available > 1 else 0
    dice = max(0, min(spend, available - reserve))

    return dice


def _expected_total_damage(attacks: list[IncomingAttack]) -> float:
    """Rough expected damage: parse ``NdM+K`` from each attack's formula."""

    total = 0.0
    for atk in attacks:
        total += _formula_expected(atk.damage_formula)
    return total


def _formula_expected(raw: str) -> float:
    """Return expected damage for a ``NdM``, ``NdM+K``, or constant formula."""

    raw = raw.strip()
    n, m, k = 0, 6, 0

    if "d" in raw:
        parts = raw.split("d", 1)
        try:
            n = int(parts[0]) if parts[0] else 1
        except ValueError:
            n = 1
        rest = parts[1]
        if "+" in rest:
            m_str, k_str = rest.split("+", 1)
        elif "-" in rest:
            m_str, k_str_neg = rest.split("-", 1)
            k_str = f"-{k_str_neg}"
        else:
            m_str, k_str = rest, "0"
        try:
            m = int(m_str)
        except ValueError:
            m = 6
        try:
            k = int(k_str)
        except ValueError:
            k = 0
        return n * (m + 1) / 2.0 + k
    else:
        try:
            return float(raw)
        except ValueError:
            return 3.0  # safe fallback
