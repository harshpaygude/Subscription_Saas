"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import {
  applyTheme,
  DEFAULT_ACCENT,
  getStoredAccent,
  getStoredTheme,
  ThemeMode,
  THEME_KEY,
  ACCENT_KEY,
} from "@/lib/theme";

interface ThemeContextType {
  theme: ThemeMode;
  accent: string;
  isDark: boolean;
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;
  setAccent: (hex: string) => void;
}

const ThemeContext = createContext<ThemeContextType>({
  theme: "light",
  accent: DEFAULT_ACCENT,
  isDark: false,
  setTheme: () => {},
  toggleTheme: () => {},
  setAccent: () => {},
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>("light");
  const [accent, setAccentState] = useState<string>(DEFAULT_ACCENT);

  useEffect(() => {
    const initialTheme = getStoredTheme();
    const initialAccent = getStoredAccent();
    setThemeState(initialTheme);
    setAccentState(initialAccent);
    applyTheme(initialTheme, initialAccent);
  }, []);

  const setTheme = (next: ThemeMode) => {
    setThemeState(next);
    localStorage.setItem(THEME_KEY, next);
    applyTheme(next, accent);
  };

  const toggleTheme = () => {
    const next: ThemeMode = theme === "light" ? "dark" : "light";
    setTheme(next);
  };

  const setAccent = (nextHex: string) => {
    setAccentState(nextHex);
    localStorage.setItem(ACCENT_KEY, nextHex);
    localStorage.setItem("UniSora-button", nextHex);
    applyTheme(theme, nextHex);
  };

  return (
    <ThemeContext.Provider
      value={{
        theme,
        accent,
        isDark: theme === "dark",
        setTheme,
        toggleTheme,
        setAccent,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
