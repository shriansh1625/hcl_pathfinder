import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "var(--bg-deep)",
          900: "var(--bg)",
          800: "var(--surface)",
          700: "var(--elevated)",
          600: "var(--focus)",
        },
        line: "var(--line)",
        mist: "var(--mist)",
        paper: "var(--paper)",
        accent: {
          DEFAULT: "var(--accent)",
          dim: "var(--accent-dim)",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 0 0 1px var(--line)",
        elevated: "0 0 0 1px var(--line-strong), 0 18px 40px -28px var(--shadow-focus)",
      },
    },
  },
  plugins: [],
};

export default config;
