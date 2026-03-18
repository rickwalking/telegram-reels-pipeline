import {
  createContext,
  useCallback,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";

type ThemeMode = "light" | "dark" | "system";

interface ThemeContextValue {
  readonly themeMode: ThemeMode;
  readonly resolvedTheme: "light" | "dark";
  readonly setThemeMode: (mode: ThemeMode) => void;
}

const THEME_STORAGE_KEY = "pipeline-theme";
const DARK_MEDIA_QUERY = "(prefers-color-scheme: dark)";

function getStoredTheme(): ThemeMode {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") {
      return stored;
    }
  } catch {
    /* localStorage unavailable */
  }
  return "system";
}

function getSystemPrefersDark(): boolean {
  return window.matchMedia(DARK_MEDIA_QUERY).matches;
}

function subscribeToSystemTheme(onStoreChange: () => void): () => void {
  const mediaQuery = window.matchMedia(DARK_MEDIA_QUERY);
  mediaQuery.addEventListener("change", onStoreChange);
  return () => mediaQuery.removeEventListener("change", onStoreChange);
}

function applyThemeClass(isDark: boolean): void {
  document.documentElement.classList.toggle("dark", isDark);
}

export const ThemeContext = createContext<ThemeContextValue | null>(null);

interface ThemeProviderProps {
  readonly children: ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(getStoredTheme);

  const systemPrefersDark = useSyncExternalStore(
    subscribeToSystemTheme,
    getSystemPrefersDark,
    () => false,
  );

  const resolvedTheme = useMemo((): "light" | "dark" => {
    if (themeMode === "system") {
      return systemPrefersDark ? "dark" : "light";
    }
    return themeMode;
  }, [themeMode, systemPrefersDark]);

  applyThemeClass(resolvedTheme === "dark");

  const setThemeMode = useCallback((mode: ThemeMode): void => {
    setThemeModeState(mode);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, mode);
    } catch {
      /* localStorage unavailable */
    }
  }, []);

  const contextValue = useMemo<ThemeContextValue>(
    () => ({ themeMode, resolvedTheme, setThemeMode }),
    [themeMode, resolvedTheme, setThemeMode],
  );

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
}
