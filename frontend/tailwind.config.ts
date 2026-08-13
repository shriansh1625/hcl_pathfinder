import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#090b0e",
          900: "#0d1014",
          800: "#12161c",
          700: "#181d25",
          600: "#222933",
        },
        line: "#2a3340",
        mist: "#9aa3b2",
        paper: "#f4f1ea",
        accent: {
          DEFAULT: "#5eead4",
          dim: "#2dd4bf",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 0 0 1px rgba(255,255,255,0.04), 0 24px 48px -24px rgba(0,0,0,0.55)",
      },
    },
  },
  plugins: [],
};

export default config;
