import { describe, it, expect, beforeAll } from "vitest";
import i18n from "../../src/i18n/index";
import ja from "../../src/i18n/ja";
import en from "../../src/i18n/en";
import type { Barrier, GameState, MapObject, Pillar, Wire } from "../../src/types";

beforeAll(async () => {
  await i18n.changeLanguage("ja");
});

describe("Phase 4 web: i18n keys", () => {
  const requiredKeys = [
    "room.hud.katashiro",
    "room.hud.katashiroLabel",
    "room.map.pillar",
    "room.map.barrier",
    "room.map.barrier.barrier_wall",
    "room.map.barrier.armor_dissolve",
    "room.map.barrier.evasion_block",
    "room.map.barrier.attack_opportunity",
  ] as const;

  it("ja and en define every Phase 4 HUD/map key", () => {
    for (const key of requiredKeys) {
      expect(ja).toHaveProperty(key);
      expect(en).toHaveProperty(key);
    }
  });

  it("katashiro label interpolates {{n}}", async () => {
    expect(i18n.t("room.hud.katashiroLabel", { n: 7 })).toContain("7");
    await i18n.changeLanguage("en");
    expect(i18n.t("room.hud.katashiroLabel", { n: 3 })).toContain("3");
    await i18n.changeLanguage("ja");
  });
});

describe("Phase 4 web: GameState types accept Phase 4/5 entities", () => {
  it("GameState compiles with pillars/wires/barriers/objects", () => {
    const pillar: Pillar = {
      id: "pl-1",
      owner_id: "char-1",
      position: [3, 4],
      is_active: true,
    };
    const wire: Wire = {
      id: "w-1",
      pillar_a_id: "pl-1",
      pillar_b_id: "pl-2",
    };
    const barrier: Barrier = {
      id: "b-1",
      wire_id: "w-1",
      effect: "barrier_wall",
      owner_id: "char-1",
      is_active: true,
    };
    const obj: MapObject = {
      id: "o-1",
      position: [1, 2],
      strength: 3,
      armor: 1,
      label: "祠",
    };

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
      pillars: [pillar],
      wires: [wire],
      barriers: [barrier],
      objects: [obj],
      current_turn_summary: null,
      pending_actions: [],
    };

    expect(state.pillars).toHaveLength(1);
    expect(state.wires?.[0]?.pillar_a_id).toBe("pl-1");
    expect(state.barriers?.[0]?.effect).toBe("barrier_wall");
    expect(state.objects?.[0]?.strength).toBe(3);
  });
});
