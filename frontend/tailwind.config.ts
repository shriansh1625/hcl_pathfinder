import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0c0e12",
          900: "#14171e",
          800: "#1a1f28",
          700: "#222833",
          600: "#2a3240",
        },
        line: "rgba(232, 226, 212, 0.10)",
        mist: "#8b93a0",
        paper: "#e8e2d4",
        accent: {
          DEFAULT: "#8fba9c",
          dim: "#7d9a8a",
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
