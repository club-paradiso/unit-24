/// <reference types="vitest/config" />
import { readFileSync } from "node:fs";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

interface VercelConfig {
  headers?: { source: string; headers: { key: string; value: string }[] }[];
}

/**
 * The security headers production sends (web/vercel.json), applied to `vite preview` so the
 * end-to-end suite runs under the same Content-Security-Policy. HSTS and the HTTPS upgrade are
 * dropped because preview is plain http on localhost.
 */
function productionHeaders(): Record<string, string> {
  const config = JSON.parse(readFileSync(new URL("./vercel.json", import.meta.url), "utf8")) as VercelConfig;
  const all = config.headers?.find((h) => h.source === "/(.*)")?.headers ?? [];
  return Object.fromEntries(
    all
      .filter((h) => h.key !== "Strict-Transport-Security")
      .map((h) => [h.key, h.key === "Content-Security-Policy" ? h.value.replace(/;\s*upgrade-insecure-requests/, "") : h.value]),
  );
}

export default defineConfig({
  plugins: [react()],
  build: { target: "es2022", sourcemap: true },
  preview: { headers: productionHeaders() },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
  },
});
