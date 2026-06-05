import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        muted: "#64748b",
        panel: "#ffffff",
        canvas: "#f7f5f0",
        primary: "#0f3d5e",
      },
      boxShadow: {
        card: "0 1px 3px rgba(15, 23, 42, 0.05)",
      },
    },
  },
  plugins: [],
} satisfies Config;
