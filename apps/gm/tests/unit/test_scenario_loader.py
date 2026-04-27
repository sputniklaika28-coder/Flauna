from __future__ import annotations

from pathlib import Path

import pytest

from tacex_gm.scenario import (
    ScenarioValidator,
    YamlLoadError,
    load_enemies,
    load_narration_templates,
    load_scenario,
    load_weapons,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SCENARIO_DIR = Path(__file__).resolve().parents[2] / "scenarios"


class TestLoaders:
    def test_load_weapons(self) -> None:
        weapons = load_weapons(DATA_DIR / "weapons.yaml")
        assert "kogatana" in weapons
        assert weapons["kogatana"].name == "小刀"

    def test_load_enemies(self) -> None:
        enemies = load_enemies(DATA_DIR / "enemies.yaml")
        assert "ukkoku_ageha" in enemies
        assert enemies["ukkoku_ageha"]["name"] == "鬱黒揚羽"

    def test_load_narration_templates(self) -> None:
        templates = load_narration_templates(DATA_DIR / "narration_templates.yaml")
        assert "attack_hit_melee" in templates
        assert "template" in templates["attack_hit_melee"]

    def test_load_scenario(self) -> None:
        scenario = load_scenario(SCENARIO_DIR / "first_mission.yaml")
        assert scenario.scenario_id == "first_mission"
        assert scenario.title == "最初の任務"
        assert scenario.map_size == (20, 20)
        assert any(c.template == "ukkoku_ageha" for c in scenario.characters)

    def test_invalid_yaml_includes_line(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.yaml"
        path.write_text("scenario_id: 'oops\n", encoding="utf-8")
        with pytest.raises(YamlLoadError) as excinfo:
            load_scenario(path)
        assert excinfo.value.path == path
        assert excinfo.value.line is not None

    def test_load_scenario_passes_validator(self) -> None:
        scenario = load_scenario(SCENARIO_DIR / "first_mission.yaml")
        enemies = load_enemies(DATA_DIR / "enemies.yaml")
        validator = ScenarioValidator(enemy_templates=enemies)
        report = validator.validate(scenario)
        assert report.ok, [str(i) for i in report.issues]
