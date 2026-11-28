"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import {
  applyTheme,
  UNISORA_ACCENT,
  getStoredTheme,
  ThemeMode,
  THEME_KEY,
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
  theme: "dark",
  accent: UNISORA_ACCENT,
  isDark: true,
  setTheme: () => {},
  toggleTheme: () => {},
  setAccent: () => {},
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>("dark");

  useEffect(() => {
    const initialTheme = getStoredTheme();
    setThemeState(initialTheme);
    applyTheme(initialTheme);
  }, []);

  const setTheme = (next: ThemeMode) => {
    setThemeState(next);
    localStorage.setItem(THEME_KEY, next);
    applyTheme(next);
  };

  const toggleTheme = () => {
    const next: ThemeMode = theme === "light" ? "dark" : "light";
    setTheme(next);
  };

  const setAccent = () => {
    applyTheme(theme);
  };

  return (
    <ThemeContext.Provider
      value={{
        theme,
        accent: UNISORA_ACCENT,
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
