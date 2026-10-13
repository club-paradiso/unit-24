import { defineConfig } from "vitest/config";

/** Firestore security rules tests; run against the emulator with `npm run test:rules`. */
export default defineConfig({
  test: { environment: "node", include: ["rules/**/*.test.ts"], testTimeout: 20_000 },
});
