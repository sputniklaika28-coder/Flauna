"""Character growth system (GM spec Phase 7).

After assessment, each PC may acquire one new skill or art.
Growth proposals are derived from session performance (grade).
"""

from __future__ import annotations

from tacex_gm.models.assessment import GrowthProposal, GrowthType, SessionScore
from tacex_gm.models.character import Character

__all__ = ["GrowthProposal", "GrowthType", "apply_growth", "propose_growth"]

# Skills/arts available as growth rewards, keyed by minimum grade.
_SKILL_POOL_BY_GRADE: dict[str, list[str]] = {
    "S": ["踏み込み", "連続攻撃", "白兵戦適性", "回避強化"],
    "A": ["白兵戦適性", "回避強化", "精密攻撃適性"],
    "B": ["回避強化", "精密攻撃適性"],
    "C": ["精密攻撃適性"],
    "D": [],
}

_ART_POOL_BY_GRADE: dict[str, list[str]] = {
    "S": ["霊力放出", "加護防壁", "反閃歩法"],
    "A": ["加護防壁", "反閃歩法"],
    "B": ["反閃歩法"],
    "C": [],
    "D": [],
}

_GRADE_ORDER = ["D", "C", "B", "A", "S"]


def _pool_for_grade(grade: str, pool_map: dict[str, list[str]]) -> list[str]:
    """Collect all entries available at or below this grade level."""
    idx = _GRADE_ORDER.index(grade)
    result: list[str] = []
    for g in _GRADE_ORDER[: idx + 1]:
        for item in pool_map.get(g, []):
            if item not in result:
                result.append(item)
    return result


def propose_growth(
    character: Character,
    score: SessionScore,
) -> list[GrowthProposal]:
    """Return growth proposals for a single PC character based on session score.

    Only PC characters that survived are eligible.
    Each proposal represents one new skill or art the player may accept.
    """
    if character.faction != "pc" or not character.is_alive:
        return []

    proposals: list[GrowthProposal] = []
    grade = score.grade

    for skill in _pool_for_grade(grade, _SKILL_POOL_BY_GRADE):
        if skill not in character.skills:
            proposals.append(
                GrowthProposal(character_id=character.id, grow_type="skill", name=skill)
            )

    for art in _pool_for_grade(grade, _ART_POOL_BY_GRADE):
        if art not in character.arts:
            proposals.append(GrowthProposal(character_id=character.id, grow_type="art", name=art))

    return proposals


def apply_growth(character: Character, proposal: GrowthProposal) -> Character:
    """Return a new Character with the proposed growth applied.

    Silently ignores the proposal if the character already has the skill/art.
    Raises ValueError if the proposal is for a different character.
    """
    if proposal.character_id != character.id:
        raise ValueError(
            f"Proposal is for character '{proposal.character_id}', not '{character.id}'"
        )
    if proposal.grow_type == "skill":
        if proposal.name in character.skills:
            return character
        return character.model_copy(update={"skills": [*character.skills, proposal.name]})
    else:
        if proposal.name in character.arts:
            return character
        return character.model_copy(update={"arts": [*character.arts, proposal.name]})
