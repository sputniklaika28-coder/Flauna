from __future__ import annotations

from tacex_gm.models.skill import (
    SKILL_REQUIREMENTS,
    character_meets_requirement,
    get_requirement,
)


class TestSkillRequirements:
    def test_known_skills(self) -> None:
        assert "踏み込み" in SKILL_REQUIREMENTS
        assert get_requirement("踏み込み") is not None

    def test_unknown_skill_returns_none(self) -> None:
        assert get_requirement("does_not_exist") is None

    def test_meets_requirement_passes(self) -> None:
        assert character_meets_requirement(
            "踏み込み", aptitudes={"白兵戦適性"}, jutsu=0
        )

    def test_missing_aptitude_fails(self) -> None:
        assert not character_meets_requirement(
            "踏み込み", aptitudes=set(), jutsu=0
        )

    def test_jutsu_minimum(self) -> None:
        assert not character_meets_requirement(
            "祓魔の心得", aptitudes=set(), jutsu=0
        )
        assert character_meets_requirement(
            "祓魔の心得", aptitudes=set(), jutsu=2
        )
