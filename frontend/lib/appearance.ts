export type Appearance = "glass";

export const APPEARANCE_KEY = "UniSora-appearance";

export function getStoredAppearance(): Appearance {
  return "glass";
}

export function applyAppearance(_value?: Appearance): Appearance {
  if (typeof document !== "undefined") {
    document.documentElement.dataset.appearance = "glass";
  }
  return "glass";
}
