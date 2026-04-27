"""Skill prerequisite registry (GM spec §6-9).

Phase 1 covers the MVP-relevant subset; later phases extend the dictionary.
"""

from __future__ import annotations

from typing import Final


class SkillRequirement:
    """Static description of a skill prerequisite."""

    __slots__ = ("name", "requires_aptitude", "min_jutsu", "description")

    def __init__(
        self,
        name: str,
        *,
        requires_aptitude: tuple[str, ...] = (),
        min_jutsu: int = 0,
        description: str = "",
    ) -> None:
        self.name = name
        self.requires_aptitude = requires_aptitude
        self.min_jutsu = min_jutsu
        self.description = description


# Phase 1 baseline. Extend as new skills are introduced.
SKILL_REQUIREMENTS: Final[dict[str, SkillRequirement]] = {
    "踏み込み": SkillRequirement(
        name="踏み込み",
        requires_aptitude=("白兵戦適性",),
        description="近接攻撃前に1マスの追加移動を行う基本技。",
    ),
    "見切り": SkillRequirement(
        name="見切り",
        requires_aptitude=("回避適性",),
        description="回避ダイスを1個追加。",
    ),
    "狙撃眼": SkillRequirement(
        name="狙撃眼",
        requires_aptitude=("射撃適性",),
        description="長距離射撃の難易度を1段階下げる。",
    ),
    "祓魔の心得": SkillRequirement(
        name="祓魔の心得",
        min_jutsu=1,
        description="祓魔術の使用に必要な基礎修養。",
    ),
}


def get_requirement(name: str) -> SkillRequirement | None:
    return SKILL_REQUIREMENTS.get(name)


def character_meets_requirement(
    skill_name: str,
    *,
    aptitudes: set[str],
    jutsu: int,
) -> bool:
    """Return True if the character satisfies the skill's prerequisites."""

    requirement = SKILL_REQUIREMENTS.get(skill_name)
    if requirement is None:
        return False
    if requirement.min_jutsu > jutsu:
        return False
    return all(req in aptitudes for req in requirement.requires_aptitude)
