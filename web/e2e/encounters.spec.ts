import { expect, test } from "./helpers";
import { test as base } from "@playwright/test";

test("ENCOUNTER entry is reachable without touching radio lessons or learner progress", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => window.localStorage.clear());
  await page.goto("/");
  await page.getByRole("link", { name: /Explore ENCOUNTER/ }).click();
  await expect(page).toHaveURL(/\/encounters$/);
  await expect(page.getByRole("heading", { name: "English for police encounters" })).toBeVisible();
  await expect(page.locator(".encounter-card")).toHaveCount(6);
  await expect(page.getByText(/These are scenario previews, not playable lessons/).first()).toBeHidden();
  await page.locator('details[data-scenario="traffic-stop"] summary').click();
  await expect(page.getByText(/These are scenario previews, not playable lessons/).first()).toBeVisible();
  expect(await page.evaluate(() => window.localStorage.getItem("unit24.progress"))).toBeNull();
  await page.getByRole("link", { name: /Return to radio English/ }).click();
  await expect(page).toHaveURL(/\/chp$/);
});

base("ENCOUNTER copy is localized for the default Korean interface", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("unit24.lang", "ko"));
  await page.goto("/encounters");
  await expect(page.getByRole("heading", { name: "경찰과 마주하는 순간의 영어" })).toBeVisible();
  await expect(page.locator(".encounter-card")).toHaveCount(6);
  await page.locator('details[data-scenario="id-request"] summary').click();
  await expect(page.getByText("요청과 지시를 구분해 듣기")).toBeVisible();
});
