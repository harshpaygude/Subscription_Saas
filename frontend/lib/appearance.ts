export type Appearance = "solid" | "glass";

export const APPEARANCE_KEY = "UniSora-appearance";

export function getStoredAppearance(): Appearance {
  if (typeof window === "undefined") return "solid";
  return localStorage.getItem(APPEARANCE_KEY) === "glass" ? "glass" : "solid";
}

export function applyAppearance(value: Appearance): Appearance {
  const appearance: Appearance = value === "glass" ? "glass" : "solid";
  document.documentElement.dataset.appearance = appearance;
  return appearance;
}
