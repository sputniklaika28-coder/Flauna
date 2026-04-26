import { describe, it, expect, beforeAll } from "vitest";
import i18n from "../../src/i18n/index";

beforeAll(async () => {
  await i18n.changeLanguage("ja");
});

describe("i18n", () => {
  it("returns Japanese app name in ja locale", () => {
    expect(i18n.t("app.name")).toBe("タクティカル祓魔師TRPG");
  });

  it("returns English app name in en locale", async () => {
    await i18n.changeLanguage("en");
    expect(i18n.t("app.name")).toBe("Tactical Exorcist TRPG");
    await i18n.changeLanguage("ja");
  });

  it("ja and en app names are different", async () => {
    const ja = i18n.t("app.name");
    await i18n.changeLanguage("en");
    const en = i18n.t("app.name");
    expect(ja).not.toBe(en);
    await i18n.changeLanguage("ja");
  });
});
