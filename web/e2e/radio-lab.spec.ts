import { expect } from "@playwright/test";
import { answerQuestion, content, test } from "./helpers";
import { test as base } from "@playwright/test";

test("radio lab introduces pronunciation and speaking before code recall", async ({ page }) => {
  await page.goto("/chp");
  await page.getByRole("link", { name: /Speaking Lab|말하기 연습/ }).click();
  await expect(page).toHaveURL(/\/chp\/speak$/);
  await expect(page.getByRole("heading", { name: /Don't just read radio codes/ })).toBeVisible();
  await expect(page.getByText("ten one", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: /Hear pronunciation/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Hear slowly/ })).toBeVisible();
  await page.getByRole("button", { name: "Next phrase" }).click();
  await expect(page.getByText("ten two", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Spelling alphabet" }).click();
  await expect(page.getByText("A as in Adam", { exact: true }).first()).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("unit24.progress"))).toBeNull();
});

base("Korean radio lab gives pronunciation first, even without mic permission", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("unit24.lang", "ko"));
  await page.goto("/chp/speak");
  await expect(page.getByRole("heading", { name: /코드를 읽기만 하지 말고/ })).toBeVisible();
  await expect(page.locator(".speech-coach").getByRole("button", { name: /발음 듣기/ })).toBeVisible();
  await expect(page.getByText("수신 상태 불량")).toBeVisible();
  await expect(page.getByText(/녹음은 이 기기에서만 재생/)).toBeVisible();
});

test("first-time home prioritizes the lesson journey over optional speaking", async ({ page }) => {
  await page.goto("/");
  const primary = await page.locator(".today").boundingBox();
  const optional = await page.locator(".voice-home-callout").boundingBox();
  expect(primary && optional && primary.y < optional.y).toBe(true);
  await expect(page.getByRole("link", { name: "Start the first lesson" })).toBeVisible();
});

test("code audio and its meaning are distinct, and the single-item check saves progress", async ({ page }) => {
  await page.addInitScript(() => {
    const calls: string[] = [];
    (window as Window & { __unit24Spoken?: string[] }).__unit24Spoken = calls;
    Object.defineProperty(window, "SpeechSynthesisUtterance", {
      configurable: true,
      value: class {
        text: string;
        lang = "";
        rate = 1;
        voice: null = null;
        constructor(text: string) { this.text = text; }
      },
    });
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: { cancel() {}, getVoices() { return []; }, speak(utterance: { text: string }) { calls.push(utterance.text); } },
    });
  });
  await page.goto("/chp/speak");
  await expect(page.getByRole("button", { name: "Hear the code" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Hear the English meaning" })).toBeVisible();
  await page.getByRole("button", { name: "Hear the code" }).click();
  await page.getByRole("button", { name: "Hear the English meaning" }).click();
  expect(await page.evaluate(() => (window as Window & { __unit24Spoken?: string[] }).__unit24Spoken)).toEqual(["ten one", "Reception poor"]);
  await expect(page.locator(".radio-source-summary")).toContainText("Unverified");
  await expect(page.locator(".radio-source-summary")).toContainText("Current use unknown");
  expect(await page.evaluate(() => localStorage.getItem("unit24.progress"))).toBeNull();
  await page.getByRole("button", { name: "Check this item · 1 question" }).click();
  await expect(page.getByText("Question 1 of 1")).toBeVisible();
  await answerQuestion(page, true);
  await page.getByRole("button", { name: "Finish session" }).click();
  await expect(page.getByRole("heading", { name: "Session summary" })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("unit24.progress"))).toContain(content.items[0]!.id);
});

test("speaking practice resumes an existing quiz without overwriting it", async ({ page }) => {
  await page.goto("/chp/practice");
  await page.getByRole("button", { name: /Mixed practice/ }).click();
  await expect(page.getByText("Question 1 of 10")).toBeVisible();
  const original = await page.evaluate(() => localStorage.getItem("unit24.progress"));
  await page.goto("/chp/speak");
  await expect(page.getByRole("link", { name: "Resume unfinished practice" })).toBeVisible();
  await page.getByRole("link", { name: "Resume unfinished practice" }).click();
  await expect(page.getByText("Question 1 of 10")).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("unit24.progress"))).toBe(original);
});

test("speaking controls and source state remain usable at 320px", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await page.goto("/chp/speak");
  const controls = page.locator(".radio-audio-actions");
  await expect(controls.getByRole("button", { name: "Hear the code" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Check this item · 1 question" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
});
