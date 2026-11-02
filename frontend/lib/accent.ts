import {
  DEFAULT_ACCENT,
  normalizeAccent,
  applyTheme,
  getStoredAccent as getThemeStoredAccent,
} from "./theme";

export { DEFAULT_ACCENT, normalizeAccent };

export function applyAccent(value: string | null | undefined): string {
  const normalized = normalizeAccent(value);
  const theme = typeof document !== "undefined" && document.documentElement.dataset.theme === "dark" ? "dark" : "light";
  applyTheme(theme, normalized);
  return normalized;
}

export function getStoredAccent(): string {
  return getThemeStoredAccent();
}
