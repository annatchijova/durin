import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Durin palette: a neutral "ink" scale carries almost everything, so
        // the four semantic states read instantly against it. Brand (PayPal
        // blue) is reserved for the primary action and the logo -- never for
        // a state, the same discipline /vertice documents for its own accent.
        canvas: "#F6F8FB",
        surface: "#FFFFFF",
        ink: {
          900: "#0B1220",
          700: "#1E2A44",
          500: "#5B6B84",
          400: "#8494A8",
        },
        brand: {
          light: "#009CDE",
          DEFAULT: "#0070E0",
          deep: "#003087",
        },
        state: {
          ready: "#17653A",
          readyBg: "#E7F3EB",
          exception: "#B42318",
          exceptionBg: "#FBEAE8",
          review: "#735C12",
          reviewBg: "#F5F0DC",
          pending: "#5B6B84",
          pendingBg: "#EEF1F5",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(11,18,32,0.04), 0 8px 24px rgba(11,18,32,0.06)",
        lift: "0 2px 6px rgba(11,18,32,0.05), 0 18px 40px rgba(11,18,32,0.10)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.4s ease-out both",
      },
    },
  },
  plugins: [],
};
export default config;
