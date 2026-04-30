import { describe, it, expect, beforeAll } from "vitest";
import i18n from "../../src/i18n/index";
import ja from "../../src/i18n/ja";
import en from "../../src/i18n/en";
import type { CombatPressure, GameState, PressureLevel } from "../../src/types";

beforeAll(async () => {
  await i18n.changeLanguage("ja");
});

describe("Phase 6 web: i18n keys", () => {
  const required = [
    "room.hardMode.title",
    "room.hardMode.level.normal",
    "room.hardMode.level.hard",
    "room.hardMode.level.ultra_hard",
    "room.hardMode.zeroRounds",
    "room.hardMode.escalated",
  ] as const;

  it("ja and en define every Phase 6 hard-mode key", () => {
    for (const key of required) {
      expect(ja).toHaveProperty(key);
      expect(en).toHaveProperty(key);
    }
  });

  it("zeroRounds interpolates {{n}}", async () => {
    expect(i18n.t("room.hardMode.zeroRounds", { n: 1 })).toContain("1");
    await i18n.changeLanguage("en");
    expect(i18n.t("room.hardMode.zeroRounds", { n: 2 })).toContain("2");
    await i18n.changeLanguage("ja");
  });

  it("escalated interpolates {{level}}", async () => {
    const localized = i18n.t("room.hardMode.level.hard");
    const msg = i18n.t("room.hardMode.escalated", { level: localized });
    expect(msg).toContain(localized);
  });
});

describe("Phase 6 web: CombatPressure type", () => {
  it("PressureLevel covers normal/hard/ultra_hard", () => {
    const levels: PressureLevel[] = ["normal", "hard", "ultra_hard"];
    expect(levels).toHaveLength(3);
  });

  it("GameState compiles with optional combat_pressure", () => {
    const pressure: CombatPressure = {
      level: "hard",
      zero_damage_rounds: 1,
      pc_to_boss_damage: 0,
      boss_to_pc_damage: 0,
    };

    const state: GameState = {
      room_id: "r",
      version: 1,
      seed: 1,
      phase: "combat",
      machine_state: "IDLE",
      turn_order: [],
      current_turn_index: 0,
      round_number: 4,
      characters: [],
      map_size: [10, 10],
      obstacles: [],
      combat_pressure: pressure,
      current_turn_summary: null,
      pending_actions: [],
    };

    expect(state.combat_pressure?.level).toBe("hard");
    expect(state.combat_pressure?.zero_damage_rounds).toBe(1);
  });

  it("GameState also compiles without combat_pressure (back-compat)", () => {
    const state: GameState = {
      room_id: "r",
      version: 1,
      seed: 1,
      phase: "combat",
      machine_state: "IDLE",
      turn_order: [],
      current_turn_index: 0,
      round_number: 1,
      characters: [],
      map_size: [10, 10],
      obstacles: [],
      current_turn_summary: null,
      pending_actions: [],
    };
    expect(state.combat_pressure).toBeUndefined();
  });
});
