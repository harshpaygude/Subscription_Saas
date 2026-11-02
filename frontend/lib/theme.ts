export type ThemeMode = "light" | "dark";

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
    id: "emerald",
    name: "Emerald Green",
    hex: "#10b981",
    hover: "#059669",
    subtleLight: "#ecfdf5",
    subtleDark: "rgba(16, 185, 129, 0.15)",
  },
  {
    id: "purple",
    name: "Royal Purple",
    hex: "#7c3aed",
    hover: "#6d28d9",
    subtleLight: "#f5f3ff",
    subtleDark: "rgba(124, 58, 237, 0.15)",
  },
  {
    id: "blue",
    name: "Ocean Blue",
    hex: "#0284c7",
    hover: "#0369a1",
    subtleLight: "#f0f9ff",
    subtleDark: "rgba(2, 132, 199, 0.15)",
  },
  {
    id: "indigo",
    name: "Indigo",
    hex: "#4f46e5",
    hover: "#4338ca",
    subtleLight: "#eef2ff",
    subtleDark: "rgba(79, 70, 229, 0.15)",
  },
  {
    id: "teal",
    name: "Teal",
    hex: "#0d9488",
    hover: "#0f766e",
    subtleLight: "#f0fdfa",
    subtleDark: "rgba(13, 148, 136, 0.15)",
  },
];

export const DEFAULT_ACCENT = "#10b981";
export const THEME_KEY = "UniSora-theme";
export const ACCENT_KEY = "UniSora-accent";

const HEX_RE = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

export function normalizeAccent(value: string | null | undefined): string {
  const candidate = (value || "").trim();
  if (!HEX_RE.test(candidate)) return DEFAULT_ACCENT;
  if (candidate.length === 4) {
    return `#${candidate.slice(1).split("").map((p) => p + p).join("")}`.toUpperCase();
  }
  return candidate.toUpperCase();
}

function hexToRgb(hex: string) {
  const n = normalizeAccent(hex).slice(1);
  return {
    r: parseInt(n.slice(0, 2), 16),
    g: parseInt(n.slice(2, 4), 16),
    b: parseInt(n.slice(4, 6), 16),
  };
}

function rgbToHex({ r, g, b }: { r: number; g: number; b: number }) {
  return `#${[r, g, b]
    .map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0"))
    .join("")}`.toUpperCase();
}

function mix(from: string, to: string, amount: number) {
  const a = hexToRgb(from);
  const b = hexToRgb(to);
  return rgbToHex({
    r: a.r + (b.r - a.r) * amount,
    g: a.g + (b.g - a.g) * amount,
    b: a.b + (b.b - a.b) * amount,
  });
}

function contrastForeground(hex: string) {
  const { r, g, b } = hexToRgb(hex);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.62 ? "#0f172a" : "#ffffff";
}

export function applyTheme(mode: ThemeMode, accentInput?: string): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.dataset.theme = mode;

  const hex = normalizeAccent(accentInput || localStorage.getItem(ACCENT_KEY) || DEFAULT_ACCENT);
  const hover = mix(hex, mode === "dark" ? "#ffffff" : "#111827", 0.18);
  const active = mix(hex, mode === "dark" ? "#ffffff" : "#111827", 0.3);
  const foreground = contrastForeground(hex);
  const subtle = mode === "dark" ? mix(hex, "#000000", 0.75) : mix(hex, "#ffffff", 0.92);
  const ring = `rgba(${hexToRgb(hex).r}, ${hexToRgb(hex).g}, ${hexToRgb(hex).b}, 0.28)`;

  // Design Tokens
  root.style.setProperty("--color-accent", hex);
  root.style.setProperty("--color-accent-hover", hover);
  root.style.setProperty("--color-accent-active", active);
  root.style.setProperty("--color-accent-subtle", subtle);
  root.style.setProperty("--color-accent-text", foreground);
  root.style.setProperty("--color-accent-ring", ring);

  // Backward compatibility tokens
  root.style.setProperty("--accent-primary", hex);
  root.style.setProperty("--accent-hover", hover);
  root.style.setProperty("--accent-active", active);
  root.style.setProperty("--accent-subtle", subtle);
  root.style.setProperty("--accent-muted", mix(hex, "#ffffff", 0.7));
  root.style.setProperty("--accent-border", mix(hex, "#ffffff", 0.5));
  root.style.setProperty("--accent-ring", ring);
  root.style.setProperty("--accent-foreground", foreground);
  root.style.setProperty("--ui-button", hex);
  root.style.setProperty("--ui-button-hover", hover);
  root.style.setProperty("--ui-accent", hex);
  root.style.setProperty("--ui-accent-dark", hover);
  root.style.setProperty("--ui-accent-soft", subtle);
}

export function getStoredTheme(): ThemeMode {
  if (typeof window === "undefined") return "light";
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "dark" || saved === "light") return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function getStoredAccent(): string {
  if (typeof window === "undefined") return DEFAULT_ACCENT;
  return normalizeAccent(
    localStorage.getItem(ACCENT_KEY) ||
      localStorage.getItem("UniSora-button") ||
      DEFAULT_ACCENT
  );
}

/**
 * Script injected synchronously into <head> to prevent theme flicker on page load.
 */
export const THEME_INIT_SCRIPT = `
(function() {
  try {
    var theme = localStorage.getItem("${THEME_KEY}");
    if (!theme) {
      theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    document.documentElement.dataset.theme = theme;

    var accent = localStorage.getItem("${ACCENT_KEY}") || localStorage.getItem("UniSora-button") || "${DEFAULT_ACCENT}";
    document.documentElement.style.setProperty("--color-accent", accent);
    document.documentElement.style.setProperty("--accent-primary", accent);
    document.documentElement.style.setProperty("--ui-button", accent);
  } catch (e) {}
})();
`;
