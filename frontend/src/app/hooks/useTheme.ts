import { useContext } from "react";
import { ThemeContext } from "@/app/providers/ThemeProvider";

/**
 * Returns theme mode, resolved theme, and setter from the nearest ThemeProvider.
 * Throws if used outside of a ThemeProvider.
 */
export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === null) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}
