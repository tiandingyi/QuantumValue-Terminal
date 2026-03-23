import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        abyss: "#05070c",
        ink: "#0f172a",
        cyan: {
          glow: "#5ff2ff",
          soft: "#7dd3fc",
        },
      },
      boxShadow: {
        panel: "0 18px 60px rgba(0, 0, 0, 0.35)",
        insetGlow:
          "inset 1px 1px 0 rgba(255,255,255,0.05), inset -1px -1px 0 rgba(95,242,255,0.06)",
      },
      backgroundImage: {
        "radial-terminal":
          "radial-gradient(circle at top, rgba(20, 35, 58, 0.92) 0%, rgba(3, 5, 10, 0.98) 42%, rgba(1, 2, 6, 1) 100%)",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "Inter", "Segoe UI", "sans-serif"],
        mono: ["Space Mono", "SFMono-Regular", "monospace"],
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(18px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseLine: {
          "0%, 100%": { opacity: "0.22" },
          "50%": { opacity: "0.5" },
        },
      },
      animation: {
        rise: "rise 700ms ease-out forwards",
        pulseLine: "pulseLine 3.5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
