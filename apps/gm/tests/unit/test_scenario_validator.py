from __future__ import annotations

import pytest

from tacex_gm.models import (
    ActionSpawnEnemy,
    Scenario,
    ScenarioCharacter,
    ScenarioEvent,
    TriggerCharacterDies,
    TriggerEnterZone,
    VictoryAllEnemiesDefeated,
)
from tacex_gm.scenario import ScenarioValidationError, ScenarioValidator


def _enemies() -> dict[str, dict[str, object]]:
    return {
        "ukkoku_ageha": {"id": "ukkoku_ageha", "name": "鬱黒揚羽"},
        "ayakashi_ko": {"id": "ayakashi_ko", "name": "アヤカシの仔"},
    }


def _scenario(**overrides: object) -> Scenario:
    base: dict[str, object] = dict(
        scenario_id="test",
        title="テスト",
        map_size=(10, 10),
        respawn_point=(5, 5),
        obstacles=[(1, 1)],
        characters=[
            ScenarioCharacter(
                id="enemy1",
                name="鬱黒揚羽",
                faction="enemy",
                template="ukkoku_ageha",
                position=(8, 8),
            )
        ],
        events=[
            ScenarioEvent(
                id="event1",
                trigger=TriggerEnterZone(
                    type="enter_zone", zone=((4, 4), (6, 6)), who=["any_pc"]
                ),
                actions=[
                    ActionSpawnEnemy(
                        type="spawn_enemy",
                        template="ayakashi_ko",
                        count=1,
                        positions=[(7, 7)],
                    )
                ],
            )
        ],
        victory_conditions=[VictoryAllEnemiesDefeated(type="all_enemies_defeated")],
    )
    base.update(overrides)
    return Scenario(**base)  # type: ignore[arg-type]


class TestScenarioValidator:
    def test_happy_path(self) -> None:
        report = ScenarioValidator(enemy_templates=_enemies()).validate(_scenario())
        assert report.ok

    def test_unknown_template(self) -> None:
        scenario = _scenario(
            characters=[
                ScenarioCharacter(
                    id="enemy1",
                    name="???",
                    faction="enemy",
                    template="missing_template",
                    position=(1, 2),
                )
            ]
        )
        report = ScenarioValidator(enemy_templates=_enemies()).validate(scenario)
        assert any(i.code == "UNKNOWN_TEMPLATE" for i in report.issues)

    def test_out_of_bounds_position(self) -> None:
        scenario = _scenario(
            characters=[
                ScenarioCharacter(
                    id="enemy1",
                    name="x",
                    faction="enemy",
                    template="ukkoku_ageha",
                    position=(99, 99),
                )
            ]
        )
        report = ScenarioValidator(enemy_templates=_enemies()).validate(scenario)
        assert any(i.code == "OUT_OF_BOUNDS" for i in report.issues)

    def test_duplicate_character_id(self) -> None:
        scenario = _scenario(
            characters=[
                ScenarioCharacter(
                    id="dup",
                    name="a",
                    faction="enemy",
                    template="ukkoku_ageha",
                    position=(1, 1),
                ),
                ScenarioCharacter(
                    id="dup",
                    name="b",
                    faction="enemy",
                    template="ukkoku_ageha",
                    position=(2, 2),
                ),
            ]
        )
        report = ScenarioValidator(enemy_templates=_enemies()).validate(scenario)
        assert any(i.code == "DUPLICATE_CHARACTER_ID" for i in report.issues)

    def test_unknown_character_in_trigger(self) -> None:
        scenario = _scenario(
            events=[
                ScenarioEvent(
                    id="e1",
                    trigger=TriggerCharacterDies(
                        type="character_dies", character_id="ghost"
                    ),
                    actions=[],
                )
            ]
        )
        report = ScenarioValidator(enemy_templates=_enemies()).validate(scenario)
        assert any(i.code == "UNKNOWN_CHARACTER" for i in report.issues)

    def test_obstacle_out_of_bounds(self) -> None:
        scenario = _scenario(obstacles=[(99, 99)])
        report = ScenarioValidator(enemy_templates=_enemies()).validate(scenario)
        assert any(i.code == "OUT_OF_BOUNDS" for i in report.issues)

    def test_raise_if_failed(self) -> None:
        scenario = _scenario(obstacles=[(99, 99)])
        report = ScenarioValidator(enemy_templates=_enemies()).validate(scenario)
        with pytest.raises(ScenarioValidationError):
            report.raise_if_failed()
