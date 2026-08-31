"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

type Theme = "dark" | "light";

const ThemeContext = createContext<{
  theme: Theme;
  toggle: () => void;
}>({ theme: "light", toggle: () => {} });

export function useTheme() {
  return useContext(ThemeContext);
}

function readInitial(): Theme {
  if (typeof window === "undefined") return "light";
  try {
    const stored = window.localStorage.getItem("pathfinder-theme");
    if (stored === "dark" || stored === "light") return stored;
  } catch {
    /* storage unavailable */
  }
  return "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>("light");
  const firstRun = useRef(true);

  useEffect(() => {
    setTheme(readInitial());
  }, []);

  useEffect(() => {
    // Skip the mount run: the inline <head> script already applied the correct
    // theme, and writing the default "dark" state here would clobber a light
    // system preference in localStorage before readInitial() takes effect.
    if (firstRun.current) {
      firstRun.current = false;
      return;
    }
    const root = document.documentElement;
    root.classList.add("theme-animating");
    root.dataset.theme = theme;
    try {
      window.localStorage.setItem("pathfinder-theme", theme);
    } catch {
      /* storage unavailable */
    }
    const timer = window.setTimeout(() => root.classList.remove("theme-animating"), 280);
    return () => window.clearTimeout(timer);
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }, []);

  return <ThemeContext.Provider value={{ theme, toggle }}>{children}</ThemeContext.Provider>;
}
