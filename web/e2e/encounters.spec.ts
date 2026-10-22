import { expect } from "@playwright/test";
import { test } from "./helpers";
import { test as base } from "@playwright/test";

test("ENCOUNTER entry is reachable without touching radio lessons or learner progress", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => window.localStorage.clear());
  await page.goto("/");
  await page.getByRole("link", { name: /Explore ENCOUNTER/ }).click();
  await expect(page).toHaveURL(/\/encounters$/);
  await expect(page.getByRole("heading", { name: "English for police encounters" })).toBeVisible();
  await expect(page.locator(".encounter-card")).toHaveCount(6);
  const trafficCard = page.locator('details[data-scenario="traffic-stop"]');
  await expect(trafficCard).not.toHaveAttribute("open", "");
  await trafficCard.locator("summary").click();
  await expect(trafficCard).toHaveAttribute("open", "");
  await expect(trafficCard.getByText("Recognize common traffic-stop questions.")).toBeVisible();
  await expect(trafficCard.getByRole("link", { name: "Try language practice" })).toBeVisible();
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

base("switching the language in Settings translates the encounter screen and survives reload", async ({ page }) => {
  // This must use a clean context: the English fixture forcibly seeds localStorage
  // on EVERY navigation, masking the actual persisted locale.
  await page.goto("/settings");
  await page.getByRole("button", { name: "English" }).click();
  await page.goto("/encounters");
  await expect(page.getByRole("heading", { name: "English for police encounters" })).toBeVisible();
  await page.getByRole("link", { name: "Settings" }).click();
  await page.getByRole("button", { name: "한국어" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "ko");
  await page.goto("/encounters");
  await expect(page.getByRole("heading", { name: "경찰과 마주하는 순간의 영어" })).toBeVisible();
  await page.locator('details[data-scenario="traffic-stop"] summary').click();
  await expect(page.getByText("교통 단속 중 자주 들리는 질문 이해")).toBeVisible();
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "ko");
  await expect(page.getByRole("heading", { name: "경찰과 마주하는 순간의 영어" })).toBeVisible();

  await page.getByRole("link", { name: "설정" }).click();
  await page.getByRole("button", { name: "English" }).click();
  await page.goto("/encounters");
  await expect(page.getByRole("heading", { name: "English for police encounters" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
});

test("visiting ENCOUNTER preserves existing saved RADIO flashcard progress exactly", async ({ page }) => {
  await page.goto("/chp/flashcards");
  await page.getByRole("button", { name: "Show answer" }).click();
  await page.getByRole("button", { name: "I knew it" }).click();

  const before = await page.evaluate(() => localStorage.getItem("unit24.progress"));
  expect(before).not.toBeNull();
  await page.goto("/encounters");
  await page.locator('details[data-scenario="street-encounter"] summary').click();
  await expect(page.getByText("Understand common opening questions.")).toBeVisible();
  await page.getByRole("link", { name: "Return to radio English" }).click();
  await expect(page).toHaveURL(/\/chp$/);
  await page.goto("/progress");
  await page.reload();
  expect(await page.evaluate(() => localStorage.getItem("unit24.progress"))).toBe(before);
  await expect(page.getByRole("progressbar", { name: "New", exact: true })).toHaveAttribute("aria-valuenow", "49");
});

test("ENCOUNTER has no horizontal overflow at iPad portrait dimensions", async ({ page }) => {
  await page.setViewportSize({ width: 820, height: 1180 });
  await page.goto("/encounters");
  await expect(page.locator(".encounter-card")).toHaveCount(6);
  await page.locator('details[data-scenario="traffic-stop"] summary').click();
  await expect(page.locator('details[data-scenario="traffic-stop"]')).toHaveAttribute("open", "");
  const sizes = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
  }));
  expect(sizes.document).toBeLessThanOrEqual(sizes.viewport + 1);
});
