from __future__ import annotations

import pytest

from tacex_gm.engine.combat import (
    CombatResolutionError,
    apply_damage,
    build_incoming_attacks,
    compute_damage,
    melee_attack_difficulty,
    ranged_attack_difficulty,
    resolve_attack,
    resolve_evasion,
)
from tacex_gm.engine.dice import PythonDiceEngine
from tacex_gm.models.character import Character
from tacex_gm.models.constants import RangeClass
from tacex_gm.models.damage import AbilityBonus, DamageFormula, DamageSpec
from tacex_gm.models.weapon import Weapon


def make_character(
    cid: str,
    *,
    faction: str = "pc",
    position: tuple[int, int] = (0, 0),
    hp: int = 20,
    armor: int = 0,
    evasion: int = 3,
    tai: int = 4,
    rei: int = 4,
    kou: int = 4,
) -> Character:
    return Character(
        id=cid,
        name=cid,
        player_id="p1" if faction == "pc" else None,
        faction=faction,  # type: ignore[arg-type]
        tai=tai,
        rei=rei,
        kou=kou,
        jutsu=0,
        max_hp=hp,
        max_mp=0,
        hp=hp,
        mp=0,
        evasion_dice=evasion,
        max_evasion_dice=evasion,
        position=position,
        armor_value=armor,
    )


def melee_weapon() -> Weapon:
    return Weapon(
        id="kogatana",
        name="kogatana",
        category="melee",
        base_dice=4,
        damage=DamageSpec(base_formula=DamageFormula(raw="1d6+1")),
    )


def ranged_weapon() -> Weapon:
    return Weapon(
        id="ofuda",
        name="ofuda",
        category="ranged",
        range_class=RangeClass.SMALL_RANGED,
        base_dice=3,
        damage=DamageSpec(
            base_formula=DamageFormula(raw="1d6"),
            ability_bonus=AbilityBonus(ability="霊", multiplier=1.0),
            damage_type="spiritual",
        ),
    )


class TestDifficultyHelpers:
    def test_melee_normal(self) -> None:
        assert melee_attack_difficulty() == 4
        assert melee_attack_difficulty(style_modifier=-1) == 3
        assert melee_attack_difficulty(style_modifier=-10) == 2  # clamp KIDS

    def test_ranged_in_band(self) -> None:
        assert ranged_attack_difficulty(RangeClass.SMALL_RANGED, 2) == 4
        assert ranged_attack_difficulty(RangeClass.SMALL_RANGED, 5) == 5
        assert ranged_attack_difficulty(RangeClass.SMALL_RANGED, 10) == 6

    def test_ranged_out_of_band_returns_none(self) -> None:
        assert ranged_attack_difficulty(RangeClass.SMALL_RANGED, 999) is None


class TestResolveAttack:
    @pytest.mark.asyncio
    async def test_melee_in_range_rolls_pool(self) -> None:
        engine = PythonDiceEngine(seed=42)
        attacker = make_character("a", position=(0, 0))
        defender = make_character("b", faction="enemy", position=(1, 0))
        weapon = melee_weapon()

        outcomes = await resolve_attack(
            attacker=attacker,
            weapon=weapon,
            targets=[defender],
            dice_distribution=[4],
            dice_engine=engine,
        )
        assert len(outcomes) == 1
        outcome = outcomes[0]
        assert outcome.dice_used == 4
        assert outcome.difficulty == 4
        assert len(outcome.roll.rolls) == 4
        assert outcome.successes == sum(1 for r in outcome.roll.rolls if r >= 4)
        assert outcome.hit == (outcome.successes >= 1)
        assert not outcome.out_of_range
        assert not outcome.line_of_sight_blocked

    @pytest.mark.asyncio
    async def test_melee_out_of_range_short_circuits(self) -> None:
        engine = PythonDiceEngine(seed=1)
        attacker = make_character("a", position=(0, 0))
        defender = make_character("b", faction="enemy", position=(5, 5))
        outcome = (
            await resolve_attack(
                attacker=attacker,
                weapon=melee_weapon(),
                targets=[defender],
                dice_distribution=[4],
                dice_engine=engine,
            )
        )[0]
        assert outcome.out_of_range
        assert not outcome.hit
        assert outcome.roll.rolls == []

    @pytest.mark.asyncio
    async def test_ranged_los_blocked(self) -> None:
        engine = PythonDiceEngine(seed=1)
        attacker = make_character("a", position=(0, 0))
        defender = make_character("b", faction="enemy", position=(2, 0))
        outcomes = await resolve_attack(
            attacker=attacker,
            weapon=ranged_weapon(),
            targets=[defender],
            dice_distribution=[3],
            dice_engine=engine,
            obstacles=[(1, 0)],
        )
        assert outcomes[0].line_of_sight_blocked
        assert not outcomes[0].hit

    @pytest.mark.asyncio
    async def test_zero_dice_yields_miss(self) -> None:
        engine = PythonDiceEngine(seed=1)
        attacker = make_character("a")
        defender = make_character("b", faction="enemy", position=(1, 0))
        outcome = (
            await resolve_attack(
                attacker=attacker,
                weapon=melee_weapon(),
                targets=[defender],
                dice_distribution=[0],
                dice_engine=engine,
            )
        )[0]
        assert outcome.dice_used == 0
        assert not outcome.hit

    @pytest.mark.asyncio
    async def test_targets_dice_mismatch_raises(self) -> None:
        engine = PythonDiceEngine(seed=1)
        attacker = make_character("a")
        defender = make_character("b", faction="enemy", position=(1, 0))
        with pytest.raises(CombatResolutionError):
            await resolve_attack(
                attacker=attacker,
                weapon=melee_weapon(),
                targets=[defender],
                dice_distribution=[2, 2],
                dice_engine=engine,
            )

    @pytest.mark.asyncio
    async def test_ranged_without_range_class_raises(self) -> None:
        engine = PythonDiceEngine(seed=1)
        attacker = make_character("a")
        defender = make_character("b", faction="enemy", position=(2, 0))
        weapon = Weapon(
            id="bad",
            name="bad",
            category="ranged",
            range_class=None,
            base_dice=3,
            damage=DamageSpec(base_formula=DamageFormula(raw="1d6")),
        )
        with pytest.raises(CombatResolutionError):
            await resolve_attack(
                attacker=attacker,
                weapon=weapon,
                targets=[defender],
                dice_distribution=[3],
                dice_engine=engine,
            )


class TestEvasion:
    @pytest.mark.asyncio
    async def test_evasion_succeeds_on_one_success(self) -> None:
        engine = PythonDiceEngine(seed=42)
        target = make_character("d", evasion=3)
        outcome = await resolve_evasion(
            pending_id="p1",
            target=target,
            dice_used=3,
            dice_engine=engine,
        )
        assert outcome.dice_used == 3
        assert outcome.succeeded == (outcome.successes >= 1)

    @pytest.mark.asyncio
    async def test_evasion_zero_dice_fails(self) -> None:
        engine = PythonDiceEngine(seed=1)
        target = make_character("d", evasion=2)
        outcome = await resolve_evasion(
            pending_id="p1",
            target=target,
            dice_used=0,
            dice_engine=engine,
        )
        assert not outcome.succeeded
        assert outcome.roll.rolls == []

    @pytest.mark.asyncio
    async def test_evasion_overdraw_raises(self) -> None:
        engine = PythonDiceEngine(seed=1)
        target = make_character("d", evasion=1)
        with pytest.raises(CombatResolutionError):
            await resolve_evasion(
                pending_id="p1",
                target=target,
                dice_used=2,
                dice_engine=engine,
            )


class TestDamage:
    @pytest.mark.asyncio
    async def test_compute_damage_with_ability_bonus(self) -> None:
        engine = PythonDiceEngine(seed=42)
        attacker = make_character("a", rei=5)
        target = make_character("b", faction="enemy", hp=10, armor=0)
        breakdown = await compute_damage(
            attacker=attacker,
            target=target,
            weapon=ranged_weapon(),
            dice_engine=engine,
        )
        assert breakdown.ability_bonus == 5
        assert breakdown.raw_total == breakdown.base_damage + 5
        assert breakdown.armor_reduction == 0
        assert breakdown.final_damage == breakdown.raw_total
        assert breakdown.hp_after == max(0, target.hp - breakdown.final_damage)

    @pytest.mark.asyncio
    async def test_armor_reduces_damage(self) -> None:
        engine = PythonDiceEngine(seed=42)
        attacker = make_character("a", rei=2)
        target = make_character("b", faction="enemy", hp=10, armor=2)
        breakdown = await compute_damage(
            attacker=attacker,
            target=target,
            weapon=melee_weapon(),
            dice_engine=engine,
        )
        assert breakdown.armor_reduction == min(2, breakdown.raw_total)
        assert breakdown.final_damage == breakdown.raw_total - breakdown.armor_reduction

    @pytest.mark.asyncio
    async def test_armor_piercing_ignores_armor(self) -> None:
        engine = PythonDiceEngine(seed=42)
        attacker = make_character("a")
        target = make_character("b", faction="enemy", hp=10, armor=4)
        weapon = Weapon(
            id="ap",
            name="ap",
            category="melee",
            base_dice=4,
            damage=DamageSpec(
                base_formula=DamageFormula(raw="1d6"),
                armor_piercing=True,
            ),
        )
        breakdown = await compute_damage(
            attacker=attacker, target=target, weapon=weapon, dice_engine=engine
        )
        assert breakdown.armor_reduction == 0
        assert breakdown.final_damage == breakdown.raw_total

    @pytest.mark.asyncio
    async def test_apply_damage_returns_new_character(self) -> None:
        engine = PythonDiceEngine(seed=42)
        attacker = make_character("a")
        target = make_character("b", faction="enemy", hp=10)
        breakdown = await compute_damage(
            attacker=attacker, target=target, weapon=melee_weapon(), dice_engine=engine
        )
        updated = apply_damage(target, breakdown)
        assert updated.id == target.id
        assert updated.hp == breakdown.hp_after
        assert target.hp == 10  # original unchanged

    @pytest.mark.asyncio
    async def test_apply_damage_id_mismatch_raises(self) -> None:
        engine = PythonDiceEngine(seed=42)
        attacker = make_character("a")
        target = make_character("b", faction="enemy", hp=10)
        other = make_character("c", faction="enemy", hp=10)
        breakdown = await compute_damage(
            attacker=attacker, target=target, weapon=melee_weapon(), dice_engine=engine
        )
        with pytest.raises(CombatResolutionError):
            apply_damage(other, breakdown)

    @pytest.mark.asyncio
    async def test_constant_damage_formula_skips_dice(self) -> None:
        engine = PythonDiceEngine(seed=1)
        attacker = make_character("a")
        target = make_character("b", faction="enemy", hp=10)
        weapon = Weapon(
            id="thorn",
            name="thorn",
            category="melee",
            base_dice=2,
            damage=DamageSpec(base_formula=DamageFormula(raw="3")),
        )
        breakdown = await compute_damage(
            attacker=attacker, target=target, weapon=weapon, dice_engine=engine
        )
        assert breakdown.base_roll is None
        assert breakdown.base_damage == 3


class TestBuildIncomingAttacks:
    @pytest.mark.asyncio
    async def test_groups_landed_hits(self) -> None:
        engine = PythonDiceEngine(seed=42)
        attacker = make_character("a")
        defender = make_character("b", faction="enemy", position=(1, 0))
        weapon = melee_weapon()
        outcomes = await resolve_attack(
            attacker=attacker,
            weapon=weapon,
            targets=[defender, defender],
            dice_distribution=[4, 0],  # second has zero dice → never hits
            dice_engine=engine,
        )
        grouped = build_incoming_attacks(attacker=attacker, weapon=weapon, hit_outcomes=outcomes)
        if outcomes[0].hit:
            assert defender.id in grouped
            assert len(grouped[defender.id]) == 1
            ia = grouped[defender.id][0]
            assert ia.weapon_id == weapon.id
            assert ia.attacker_id == attacker.id
            assert ia.successes == outcomes[0].successes
        else:
            assert grouped == {}
