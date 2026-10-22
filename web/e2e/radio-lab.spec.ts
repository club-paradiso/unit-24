import { expect } from "@playwright/test";
import { test } from "./helpers";
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
