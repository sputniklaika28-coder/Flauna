"""ScenarioValidator (GM spec §14-3).

Validates the in-memory ``Scenario`` against:
- enemy template availability,
- coordinate ranges (positions and zones inside ``map_size``),
- duplicate ids,
- compound-trigger nesting depth (Phase 7 forward; we still enforce a depth
  limit so future phases inherit the check),
- trigger consistency (e.g. ``character_dies`` references a known character).

Errors are accumulated and returned together so designers see the full picture.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from tacex_gm.models import Scenario


@dataclass
class ValidationIssue:
    code: str
    message: str
    location: str | None = None
    line: int | None = None

    def __str__(self) -> str:
        prefix = "" if self.location is None else f"[{self.location}] "
        return f"{prefix}{self.code}: {self.message}"


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def merged(self, other: ValidationReport) -> ValidationReport:
        return ValidationReport(issues=[*self.issues, *other.issues])

    def raise_if_failed(self) -> None:
        if not self.ok:
            raise ScenarioValidationError(self)


class ScenarioValidationError(ValueError):
    def __init__(self, report: ValidationReport) -> None:
        rendered = "; ".join(str(i) for i in report.issues)
        super().__init__(f"scenario validation failed: {rendered}")
        self.report = report


_MAX_COMPOUND_DEPTH = 3


def _coord_in_bounds(point: tuple[int, int], map_size: tuple[int, int]) -> bool:
    width, height = map_size
    x, y = point
    return 0 <= x < width and 0 <= y < height


class ScenarioValidator:
    """Validate a scenario against the loaded template and weapon catalogues."""

    def __init__(
        self,
        *,
        enemy_templates: Mapping[str, Mapping[str, object]],
        weapons: Mapping[str, object] | None = None,
    ) -> None:
        self._enemy_templates = enemy_templates
        self._weapons = weapons or {}

    def validate(self, scenario: Scenario) -> ValidationReport:
        report = ValidationReport()
        self._check_duplicate_ids(scenario, report)
        self._check_characters(scenario, report)
        self._check_obstacles(scenario, report)
        self._check_events(scenario, report)
        return report

    # -- individual checks -------------------------------------------------

    def _check_duplicate_ids(
        self, scenario: Scenario, report: ValidationReport
    ) -> None:
        seen: dict[str, int] = {}
        for character in scenario.characters:
            seen[character.id] = seen.get(character.id, 0) + 1
        for cid, count in seen.items():
            if count > 1:
                report.issues.append(
                    ValidationIssue(
                        code="DUPLICATE_CHARACTER_ID",
                        message=f"character id '{cid}' appears {count} times",
                        location=f"characters[{cid}]",
                    )
                )

        seen_events: dict[str, int] = {}
        for event in scenario.events:
            seen_events[event.id] = seen_events.get(event.id, 0) + 1
        for eid, count in seen_events.items():
            if count > 1:
                report.issues.append(
                    ValidationIssue(
                        code="DUPLICATE_EVENT_ID",
                        message=f"event id '{eid}' appears {count} times",
                        location=f"events[{eid}]",
                    )
                )

    def _check_characters(
        self, scenario: Scenario, report: ValidationReport
    ) -> None:
        for character in scenario.characters:
            location = f"characters[{character.id}]"
            if character.template and character.template not in self._enemy_templates:
                report.issues.append(
                    ValidationIssue(
                        code="UNKNOWN_TEMPLATE",
                        message=f"unknown enemy template '{character.template}'",
                        location=location,
                    )
                )
            if not _coord_in_bounds(character.position, scenario.map_size):
                report.issues.append(
                    ValidationIssue(
                        code="OUT_OF_BOUNDS",
                        message=(
                            f"position {character.position} is outside the "
                            f"map {scenario.map_size}"
                        ),
                        location=location,
                    )
                )

    def _check_obstacles(
        self, scenario: Scenario, report: ValidationReport
    ) -> None:
        for index, obstacle in enumerate(scenario.obstacles):
            if not _coord_in_bounds(obstacle, scenario.map_size):
                report.issues.append(
                    ValidationIssue(
                        code="OUT_OF_BOUNDS",
                        message=f"obstacle {obstacle} is outside the map",
                        location=f"obstacles[{index}]",
                    )
                )

    def _check_events(self, scenario: Scenario, report: ValidationReport) -> None:
        character_ids = {c.id for c in scenario.characters}
        for event in scenario.events:
            location = f"events[{event.id}]"
            self._check_trigger(event.trigger, scenario, character_ids, report, location, depth=1)
            for action_index, action in enumerate(event.actions):
                action_location = f"{location}.actions[{action_index}]"
                if getattr(action, "type", None) == "spawn_enemy":
                    template = getattr(action, "template", None)
                    if template and template not in self._enemy_templates:
                        report.issues.append(
                            ValidationIssue(
                                code="UNKNOWN_TEMPLATE",
                                message=f"unknown enemy template '{template}'",
                                location=action_location,
                            )
                        )
                    positions: Iterable[tuple[int, int]] = getattr(action, "positions", []) or []
                    for pos_index, pos in enumerate(positions):
                        if not _coord_in_bounds(pos, scenario.map_size):
                            report.issues.append(
                                ValidationIssue(
                                    code="OUT_OF_BOUNDS",
                                    message=(
                                        f"spawn position {pos} is outside "
                                        f"the map {scenario.map_size}"
                                    ),
                                    location=f"{action_location}.positions[{pos_index}]",
                                )
                            )

    def _check_trigger(
        self,
        trigger: object,
        scenario: Scenario,
        character_ids: set[str],
        report: ValidationReport,
        location: str,
        *,
        depth: int,
    ) -> None:
        if depth > _MAX_COMPOUND_DEPTH:
            report.issues.append(
                ValidationIssue(
                    code="COMPOUND_TOO_DEEP",
                    message=f"compound trigger depth {depth} exceeds max {_MAX_COMPOUND_DEPTH}",
                    location=location,
                )
            )
            return

        ttype = getattr(trigger, "type", None)
        if ttype == "enter_zone":
            zone = getattr(trigger, "zone", None)
            if zone is not None:
                a, b = zone
                if not _coord_in_bounds(a, scenario.map_size) or not _coord_in_bounds(
                    b, scenario.map_size
                ):
                    report.issues.append(
                        ValidationIssue(
                            code="OUT_OF_BOUNDS",
                            message=f"zone {zone} extends outside map {scenario.map_size}",
                            location=f"{location}.trigger",
                        )
                    )
        elif ttype == "character_dies":
            cid = getattr(trigger, "character_id", None)
            if cid and cid not in character_ids:
                report.issues.append(
                    ValidationIssue(
                        code="UNKNOWN_CHARACTER",
                        message=f"trigger references unknown character '{cid}'",
                        location=f"{location}.trigger",
                    )
                )
        # Future compound trigger expansion will recurse with depth+1.
