/// <reference types="vitest/config" />
import { readFileSync } from "node:fs";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

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
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      // An external registerSW.js, so the strict CSP (script-src 'self', no inline script) still holds.
      injectRegister: "script-defer",
      includeAssets: ["favicon.svg", "apple-touch-icon.png", "robots.txt"],
      manifest: {
        name: "Unit-24 — 무전 용어 학습",
        short_name: "Unit-24",
        description: "CHP 무전 코드와 카드 알파벳을, 출처와 검증 상태까지 확인하며 배웁니다.",
        lang: "ko",
        start_url: "/",
        scope: "/",
        display: "standalone",
        orientation: "portrait",
        theme_color: "#0f3d5e",
        background_color: "#f6f7f9",
        icons: [
          { src: "/pwa-192.png", sizes: "192x192", type: "image/png" },
          { src: "/pwa-512.png", sizes: "512x512", type: "image/png" },
          { src: "/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        // The whole app, including the content bundle, is precached, so it works offline after the first visit.
        globPatterns: ["**/*.{js,css,html,svg,png,webmanifest,txt}"],
        // Only learners who sign in download Firebase; it is cached at runtime instead.
        globIgnores: ["**/firebase-sdk*.js"],
        runtimeCaching: [{ urlPattern: /\/assets\/firebase-sdk.*\.js$/, handler: "CacheFirst", options: { cacheName: "firebase-sdk" } }],
        navigateFallback: "/index.html",
        // Firebase's auth handler pages must always come from the network.
        navigateFallbackDenylist: [/^\/__\//],
        cleanupOutdatedCaches: true,
      },
    }),
  ],
  build: {
    target: "es2022",
    sourcemap: true,
    rollupOptions: {
      output: {
        // Keep the Firebase SDK in named chunks so the service worker can leave them out of the precache.
        manualChunks: (id: string) => (/node_modules\/(@firebase|firebase)\//.test(id) ? "firebase-sdk" : undefined),
      },
    },
  },
  preview: { headers: productionHeaders() },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
  },
});
