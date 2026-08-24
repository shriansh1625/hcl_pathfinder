import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#08090b",
          900: "#0c0d10",
          800: "#101216",
          700: "#161a20",
          600: "#1e242c",
        },
        line: "rgba(244, 241, 234, 0.08)",
        mist: "#8e97a6",
        paper: "#f3efe6",
        accent: {
          DEFAULT: "#c5d4cb",
          dim: "#9bb0a3",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 0 0 1px rgba(255,255,255,0.05)",
        elevated: "0 0 0 1px rgba(255,255,255,0.07), 0 18px 40px -28px rgba(0,0,0,0.7)",
      },
    },
  },
  plugins: [],
};

export default config;
