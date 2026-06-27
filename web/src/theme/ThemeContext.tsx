import {
  createContext,
  useContext,
  useLayoutEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type ThemeMode = "dark" | "light";

export interface ThemeColors {
  bgPage: string;
  bgPanel: string;
  bgPanel2: string;
  border: string;
  textPrimary: string;
  textMuted: string;
  accentBlue: string;
  accentOrange: string;
  kgCanvas: string;
  kgLabel: string;
  kgLabelBg: string;
  kgLabelStroke: string;
  kgEdge: string;
  kgEdgeHover: string;
  chartText: string;
  chartGrid: string;
  chartBg: string;
  selectBg: string;
}

const DARK: ThemeColors = {
  bgPage: "#0b1120",
  bgPanel: "#1e293b",
  bgPanel2: "#162032",
  border: "#334155",
  textPrimary: "#f1f5f9",
  textMuted: "#94a3b8",
  accentBlue: "#3b82f6",
  accentOrange: "#f97316",
  kgCanvas: "#0c1222",
  kgLabel: "#f8fafc",
  kgLabelBg: "rgba(15, 23, 42, 0.92)",
  kgLabelStroke: "#0f172a",
  kgEdge: "#64748b",
  kgEdgeHover: "#f8fafc",
  chartText: "#94a3b8",
  chartGrid: "#334155",
  chartBg: "#1e293b",
  selectBg: "#0f172a",
};

const LIGHT: ThemeColors = {
  bgPage: "#eef2f7",
  bgPanel: "#ffffff",
  bgPanel2: "#f1f5f9",
  border: "#cbd5e1",
  textPrimary: "#0f172a",
  textMuted: "#475569",
  accentBlue: "#2563eb",
  accentOrange: "#ea580c",
  kgCanvas: "#dbeafe",
  kgLabel: "#0f172a",
  kgLabelBg: "rgba(255, 255, 255, 0.95)",
  kgLabelStroke: "#ffffff",
  kgEdge: "#94a3b8",
  kgEdgeHover: "#ffffff",
  chartText: "#334155",
  chartGrid: "#e2e8f0",
  chartBg: "#ffffff",
  selectBg: "#ffffff",
};

function applyThemeClass(mode: ThemeMode) {
  const root = document.documentElement;
  root.classList.remove("light", "dark");
  root.classList.add(mode);
  localStorage.setItem("auditra-theme", mode);
}

interface ThemeContextValue {
  mode: ThemeMode;
  colors: ThemeColors;
  toggle: () => void;
  isDark: boolean;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem("auditra-theme");
    return saved === "light" ? "light" : "dark";
  });

  useLayoutEffect(() => {
    applyThemeClass(mode);
  }, [mode]);

  const value = useMemo(
    () => ({
      mode,
      colors: mode === "dark" ? DARK : LIGHT,
      toggle: () => setMode((m) => (m === "dark" ? "light" : "dark")),
      isDark: mode === "dark",
    }),
    [mode]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
