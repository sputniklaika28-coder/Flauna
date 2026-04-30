import { describe, it, expect, beforeEach, beforeAll } from "vitest";
import i18n from "../../src/i18n/index";
import ja from "../../src/i18n/ja";
import en from "../../src/i18n/en";
import { useUIStore } from "../../src/stores/uiStore";
import { ARTS, getArt } from "../../src/utils/arts";
import type { ArtName, CastArtPayload } from "../../src/types";

beforeAll(async () => {
  await i18n.changeLanguage("ja");
});

describe("Phase 5 web: art metadata", () => {
  it("ARTS contains the six canonical exorcism arts", () => {
    const names = ARTS.map((a) => a.name).sort();
    expect(names).toEqual(
      [
        "加護防壁",
        "反閃歩法",
        "霊力放出",
        "霊弾発射",
        "呪祝詛詞",
        "式神使役",
      ].sort(),
    );
  });

  it("each art has a positive MP cost and a non-empty description", () => {
    for (const a of ARTS) {
      expect(a.mp_cost).toBeGreaterThan(0);
      expect(a.description.length).toBeGreaterThan(0);
    }
  });

  it("getArt returns the matching definition", () => {
    expect(getArt("霊弾発射")?.target_type).toBe("single");
    expect(getArt("反閃歩法")?.target_type).toBe("self");
    expect(getArt("式神使役")?.target_type).toBe("none");
    expect(getArt("霊力放出")?.target_type).toBe("area");
  });
});

describe("Phase 5 web: i18n keys", () => {
  const required = [
    "room.contextMenu.castArt",
    "room.castArt.title",
    "room.castArt.button",
    "room.castArt.cast",
    "room.castArt.mp",
    "room.castArt.noneLearned",
    "room.castArt.pickTarget",
    "room.castArt.targetType.none",
    "room.castArt.targetType.single",
    "room.castArt.targetType.area",
    "room.castArt.targetType.self",
    "room.hud.mpLabel",
  ] as const;

  it("ja and en define every Phase 5 key", () => {
    for (const key of required) {
      expect(ja).toHaveProperty(key);
      expect(en).toHaveProperty(key);
    }
  });

  it("mpLabel interpolates {{current}}/{{max}}", async () => {
    expect(i18n.t("room.hud.mpLabel", { current: 4, max: 7 })).toContain("4");
    expect(i18n.t("room.hud.mpLabel", { current: 4, max: 7 })).toContain("7");
    await i18n.changeLanguage("en");
    expect(i18n.t("room.hud.mpLabel", { current: 1, max: 9 })).toContain("9");
    await i18n.changeLanguage("ja");
  });
});

describe("Phase 5 web: cast-art store wiring", () => {
  beforeEach(() => {
    useUIStore.setState({
      activeModal: null,
      castArtTargetId: null,
      castArtCutscene: null,
    });
  });

  it("openCastArt sets activeModal and pre-selected target", () => {
    useUIStore.getState().openCastArt("char-7");
    expect(useUIStore.getState().activeModal).toBe("cast_art");
    expect(useUIStore.getState().castArtTargetId).toBe("char-7");
  });

  it("openCastArt with null leaves target empty (caster picks)", () => {
    useUIStore.getState().openCastArt(null);
    expect(useUIStore.getState().activeModal).toBe("cast_art");
    expect(useUIStore.getState().castArtTargetId).toBeNull();
  });

  it("closeModal clears modal and pre-selected target", () => {
    useUIStore.getState().openCastArt("char-7");
    useUIStore.getState().closeModal();
    expect(useUIStore.getState().activeModal).toBeNull();
    expect(useUIStore.getState().castArtTargetId).toBeNull();
  });

  it("triggerCastArtCutscene / clearCastArtCutscene manage the cutscene slot", () => {
    useUIStore
      .getState()
      .triggerCastArtCutscene({ id: "x1", artName: "霊弾発射", casterName: "太郎" });
    expect(useUIStore.getState().castArtCutscene?.artName).toBe("霊弾発射");
    useUIStore.getState().clearCastArtCutscene();
    expect(useUIStore.getState().castArtCutscene).toBeNull();
  });
});

describe("Phase 5 web: CastArtPayload shape compiles", () => {
  it("accepts canonical art names and optional target/center", () => {
    const a: CastArtPayload = { art_name: "加護防壁", target: "char-1" };
    const b: CastArtPayload = { art_name: "反閃歩法" };
    const c: CastArtPayload = {
      art_name: "霊力放出",
      center_position: [3, 4],
    };
    const all: ArtName[] = [a.art_name, b.art_name, c.art_name];
    expect(all).toHaveLength(3);
  });
});
