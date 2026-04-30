import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import ja from "./ja";
import en from "./en";

export const SUPPORTED_LANGUAGES = ["ja", "en"] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

const STORAGE_KEY = "flauna.lang";

export function detectInitialLanguage(): SupportedLanguage {
  if (typeof window === "undefined") return "ja";
  try {
    const saved = window.localStorage?.getItem(STORAGE_KEY);
    if (saved && (SUPPORTED_LANGUAGES as readonly string[]).includes(saved)) {
      return saved as SupportedLanguage;
    }
  } catch {
    // ignore (private mode etc.)
  }
  const nav = window.navigator?.language ?? "";
  if (nav.toLowerCase().startsWith("en")) return "en";
  return "ja";
}

export async function setLanguage(lang: SupportedLanguage): Promise<void> {
  await i18n.changeLanguage(lang);
  try {
    window.localStorage?.setItem(STORAGE_KEY, lang);
  } catch {
    // ignore
  }
  if (typeof document !== "undefined") {
    document.documentElement.lang = lang;
  }
}

i18n.use(initReactI18next).init({
  resources: {
    ja: { translation: ja },
    en: { translation: en },
  },
  lng: detectInitialLanguage(),
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

if (typeof document !== "undefined") {
  document.documentElement.lang = i18n.language;
}

export default i18n;
