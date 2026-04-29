"""CombatPressure logic — hard mode escalation (GM spec §10-3, D35, Phase 6).

PC側ボスへのダメージ0 かつ ボス側PCへのダメージ0 の連続2ラウンドで hard、
さらに2ラウンドで ultra_hard。
"""

from __future__ import annotations

from tacex_gm.models.event import TurnSummary
from tacex_gm.models.pressure import CombatPressure, PressureLevel


def accumulate_pressure(
    pressure: CombatPressure,
    summary: TurnSummary,
    *,
    actor_is_boss: bool,
    target_is_boss: dict[str, bool],
    target_is_pc: dict[str, bool],
) -> CombatPressure:
    """Fold one turn's TurnSummary into running CombatPressure totals.

    ``target_is_boss`` maps character_id → bool.
    ``target_is_pc``   maps character_id → bool.
    """
    pc_to_boss = pressure.pc_to_boss_damage
    boss_to_pc = pressure.boss_to_pc_damage

    if actor_is_boss:
        for char_id, dmg in summary.damage_dealt.items():
            if target_is_pc.get(char_id, False):
                boss_to_pc += dmg
    else:
        for char_id, dmg in summary.damage_dealt.items():
            if target_is_boss.get(char_id, False):
                pc_to_boss += dmg

    return pressure.model_copy(
        update={"pc_to_boss_damage": pc_to_boss, "boss_to_pc_damage": boss_to_pc}
    )


def advance_pressure_round(pressure: CombatPressure) -> tuple[CombatPressure, bool]:
    """Called at round boundary.  Returns ``(new_pressure, escalated)``.

    If both sides dealt 0 damage this round the stalemate counter increments
    and the level may escalate.  ``escalated`` is True when the level changes.
    """
    stalemate = pressure.pc_to_boss_damage == 0 and pressure.boss_to_pc_damage == 0

    if not stalemate:
        return pressure.model_copy(
            update={"zero_damage_rounds": 0, "pc_to_boss_damage": 0, "boss_to_pc_damage": 0}
        ), False

    new_zero = pressure.zero_damage_rounds + 1
    new_level = pressure.level
    escalated = False

    if pressure.level == PressureLevel.NORMAL and new_zero >= 2:
        new_level = PressureLevel.HARD
        new_zero = 0
        escalated = True
    elif pressure.level == PressureLevel.HARD and new_zero >= 2:
        new_level = PressureLevel.ULTRA_HARD
        new_zero = 0
        escalated = True

    return pressure.model_copy(
        update={
            "level": new_level,
            "zero_damage_rounds": new_zero,
            "pc_to_boss_damage": 0,
            "boss_to_pc_damage": 0,
        }
    ), escalated
