import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "var(--text-primary)",
        muted: "var(--text-muted)",
        panel: "var(--surface-primary)",
        canvas: "var(--canvas)",
        primary: "var(--action)",
        surface: {
          primary: "var(--surface-primary)",
          secondary: "var(--surface-secondary)",
          raised: "var(--surface-raised)",
          disabled: "var(--surface-disabled)",
        },
        action: { DEFAULT: "var(--action)", hover: "var(--action-hover)", subtle: "var(--action-subtle)" },
        status: {
          neutral: "var(--status-neutral)",
          information: "var(--status-information)",
          warning: "var(--status-warning)",
          error: "var(--status-error)",
          success: "var(--status-success)",
          disabled: "var(--status-disabled)",
        },
      },
      boxShadow: {
        card: "0 1px 3px rgba(15, 23, 42, 0.05)",
        overlay: "var(--shadow-overlay)",
      },
      borderRadius: { control: "var(--radius-control)", panel: "var(--radius-panel)", dialog: "var(--radius-dialog)" },
      maxWidth: { content: "var(--width-content)", reading: "var(--width-reading)", gis: "var(--width-gis)" },
    },
  },
  plugins: [],
} satisfies Config;
