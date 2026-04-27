"""YAML loaders for scenario, enemies, weapons and narration templates."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import yaml

from tacex_gm.models import Scenario, Weapon


class YamlLoadError(ValueError):
    """Raised when a YAML payload cannot be parsed or is structurally invalid."""

    def __init__(self, path: Path, message: str, line: int | None = None) -> None:
        location = f"{path}" if line is None else f"{path}:{line}"
        super().__init__(f"{location}: {message}")
        self.path = path
        self.line = line


def _load_yaml(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise YamlLoadError(path, f"failed to read file: {exc}") from exc
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        line = getattr(getattr(exc, "problem_mark", None), "line", None)
        raise YamlLoadError(
            path,
            f"YAML parse error: {exc}",
            line=line + 1 if line is not None else None,
        ) from exc


def load_scenario(path: Path) -> Scenario:
    payload = _load_yaml(path)
    if not isinstance(payload, Mapping):
        raise YamlLoadError(path, "scenario root must be a mapping")
    try:
        return Scenario.model_validate(payload)
    except Exception as exc:
        raise YamlLoadError(path, f"scenario schema error: {exc}") from exc


def load_weapons(path: Path) -> dict[str, Weapon]:
    payload = _load_yaml(path)
    if not isinstance(payload, Mapping) or "weapons" not in payload:
        raise YamlLoadError(path, "weapons file must define a top-level 'weapons' list")
    weapons: list[Mapping[str, Any]] = payload["weapons"]
    if not isinstance(weapons, list):
        raise YamlLoadError(path, "'weapons' must be a list")
    out: dict[str, Weapon] = {}
    for raw in weapons:
        if not isinstance(raw, Mapping):
            raise YamlLoadError(path, f"weapon entry must be a mapping: {raw!r}")
        try:
            weapon = Weapon.model_validate(dict(raw))
        except Exception as exc:
            raise YamlLoadError(path, f"weapon schema error: {exc}") from exc
        if weapon.id in out:
            raise YamlLoadError(path, f"duplicate weapon id: {weapon.id}")
        out[weapon.id] = weapon
    return out


def load_enemies(path: Path) -> dict[str, dict[str, Any]]:
    """Return raw enemy template dictionaries keyed by id.

    Enemy templates are not bound to a single Pydantic model — at scenario
    materialisation time they are merged with per-character overrides before
    becoming :class:`Character` instances.
    """

    payload = _load_yaml(path)
    if not isinstance(payload, Mapping) or "enemies" not in payload:
        raise YamlLoadError(path, "enemies file must define a top-level 'enemies' list")
    enemies: list[Mapping[str, Any]] = payload["enemies"]
    if not isinstance(enemies, list):
        raise YamlLoadError(path, "'enemies' must be a list")
    out: dict[str, dict[str, Any]] = {}
    for raw in enemies:
        if not isinstance(raw, Mapping):
            raise YamlLoadError(path, f"enemy entry must be a mapping: {raw!r}")
        if "id" not in raw:
            raise YamlLoadError(path, "enemy entry missing 'id'")
        enemy = dict(raw)
        enemy_id = cast(str, enemy["id"])
        if enemy_id in out:
            raise YamlLoadError(path, f"duplicate enemy id: {enemy_id}")
        out[enemy_id] = enemy
    return out


def load_narration_templates(path: Path) -> dict[str, dict[str, Any]]:
    payload = _load_yaml(path)
    if not isinstance(payload, Mapping) or "templates" not in payload:
        raise YamlLoadError(path, "narration file must define 'templates' mapping")
    templates = payload["templates"]
    if not isinstance(templates, Mapping):
        raise YamlLoadError(path, "'templates' must be a mapping")
    out: dict[str, dict[str, Any]] = {}
    for name, body in templates.items():
        if not isinstance(body, Mapping) or "template" not in body:
            raise YamlLoadError(path, f"template '{name}' missing 'template' field")
        out[str(name)] = dict(body)
    return out
