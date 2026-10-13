import { expect, test } from "@playwright/test";

test("installable: a manifest with icons is linked", async ({ page, request }) => {
  await page.goto("/");
  const href = await page.locator('link[rel="manifest"]').getAttribute("href");
  expect(href).toBeTruthy();
  const manifest = await (await request.get(href!)).json();
  expect(manifest).toMatchObject({ short_name: "Unit-24", display: "standalone", start_url: "/" });
  expect(manifest.icons.map((i: { sizes: string }) => i.sizes)).toEqual(expect.arrayContaining(["192x192", "512x512"]));
  for (const icon of manifest.icons) expect((await request.get(icon.src)).status()).toBe(200);
});

test("works offline after the first visit, including deep links", async ({ page, context }) => {
  await page.goto("/");
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  // The page is controlled once the service worker has claimed it.
  await page.reload();
  await expect.poll(() => page.evaluate(() => navigator.serviceWorker.controller !== null)).toBe(true);
  await context.setOffline(true);
  await page.goto("/chp/reference");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("찾아보기");
  await expect(page.locator(".ref-list li")).toHaveCount(50);
  await context.setOffline(false);
});
