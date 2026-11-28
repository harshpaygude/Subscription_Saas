export type ThemeMode = "light" | "dark";

export const UNISORA_ACCENT = "#B8F23A";
export const UNISORA_ACCENT_INK_LIGHT = "#4B7A00";
export const UNISORA_ACCENT_TEXT = "#030407";

export const DEFAULT_ACCENT = UNISORA_ACCENT;
export const THEME_KEY = "UniSora-theme";
export const ACCENT_KEY = "UniSora-accent";

export interface AccentPreset {
  id: string;
  name: string;
  hex: string;
  hover: string;
  subtleLight: string;
  subtleDark: string;
}

export const ACCENT_PRESETS: AccentPreset[] = [
  {
    id: "electric-lime",
    name: "Electric Lime",
    hex: UNISORA_ACCENT,
    hover: "#A5DF26",
    subtleLight: "rgba(184, 242, 58, 0.18)",
    subtleDark: "rgba(184, 242, 58, 0.14)",
  },
];

export function normalizeAccent(_value?: string | null): string {
  return UNISORA_ACCENT;
}

export function applyTheme(mode: ThemeMode, _accentInput?: string): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.dataset.theme = mode;
  root.dataset.appearance = "glass";

  // Clear any legacy per-user accent overrides so the unified UniSora palette always applies
  try {
    localStorage.removeItem(ACCENT_KEY);
    localStorage.removeItem("UniSora-button");
    localStorage.removeItem("UniSora-appearance");
  } catch {
    // Ignore storage access restrictions
  }
}

export function getStoredTheme(): ThemeMode {
  if (typeof window === "undefined") return "dark";
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "dark" || saved === "light") return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function getStoredAccent(): string {
  return UNISORA_ACCENT;
}

/**
 * Script injected synchronously into <head> to prevent theme flicker on page load.
 */
export const THEME_INIT_SCRIPT = `
(function() {
  try {
    var theme = localStorage.getItem("${THEME_KEY}");
    if (theme !== "light" && theme !== "dark") {
      theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.appearance = "glass";
  } catch (e) {}
})();
`;
