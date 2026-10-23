import { expect } from "@playwright/test";
import { test } from "./helpers";

test("serverless assessment endpoint is gated and never emits fabricated scores", async ({ request }) => {
  // The local Vite preview server has no Vercel Functions runtime; test only real deployed previews.
  test.skip(!process.env.E2E_BASE_URL, "Requires Vercel Functions on an immutable Preview");
  const r = await request.get("/api/speech-assess");
  expect(r.status()).toBe(200);
  expect(r.headers()["content-type"]).toContain("application/json");
  const data: { enabled: boolean; provider: string } = await r.json();
  expect(data.enabled).toBe(false);
  expect(data.provider).toBe("azure-pronunciation-assessment");
  const denied = await request.post("/api/speech-assess", {
    headers: { "origin": process.env.E2E_BASE_URL!, "content-type": "audio/wav" },
    data: Buffer.from("not a valid audio"),
  });
  expect(denied.status()).toBe(503);
  expect((await denied.json()).error).toBe("ASSESSMENT_UNAVAILABLE");
});

test("existing listening and speaking lab remain available without AI assessment", async ({ page }) => {
  await page.goto("/chp/speak");
  await expect(page.getByRole("heading", { name: /Don't just read radio codes/ })).toBeVisible();
  await expect(page.locator(".speech-coach").getByRole("button", { name: /Hear pronunciation/ })).toBeVisible();
  await expect(page.locator(".speech-coach").getByRole("button", { name: /Hear slowly/ })).toBeVisible();
  await expect(page.getByText("ten one", { exact: true }).first()).toBeVisible();
});
