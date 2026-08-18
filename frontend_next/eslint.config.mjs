import nextPlugin from "@next/eslint-plugin-next";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";

export default [
  {
    ignores: ["e2e/**", "playwright-report/**", "test-results/**", ".next/**", "node_modules/**"],
  },
  {
    files: ["**/*.ts", "**/*.tsx"],
    plugins: {
      "@next/next": nextPlugin,
      "@typescript-eslint": tsPlugin,
    },
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
      },
    },
    rules: {
      ...nextPlugin.configs.recommended.rules,
      ...nextPlugin.configs["core-web-vitals"].rules,
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    },
  },
  {
    // Error boundary files and full-page-reload navigation links cannot use <Link>
    // because they either render outside the router context or intentionally trigger
    // a full page load to reset client state.
    files: ["app/error.tsx", "app/global-error.tsx", "app/not-found.tsx", "components/property-case-command-center.tsx"],
    rules: {
      "@next/next/no-html-link-for-pages": "off",
    },
  },
];
