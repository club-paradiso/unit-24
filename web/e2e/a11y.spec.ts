import AxeBuilder from "@axe-core/playwright";
import { expect } from "@playwright/test";
import { content, test } from "./helpers";

const ROUTES = ["/", "/chp", "/review", `/chp/lessons/${content.lessons[0]!.id}`, "/chp/practice", "/chp/flashcards", "/chp/reference", `/chp/items/${content.items[0]!.id}`, "/progress", "/settings", "/about"];

for (const route of ROUTES) {
  test(`no serious accessibility violations on ${route}`, async ({ page }) => {
    await page.goto(route);
    await expect(page.locator("h1")).toBeVisible();
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
  });
}

test("a practice question with feedback has no serious violations, in dark mode too", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/chp/practice");
  await page.getByRole("button", { name: /Codes only/ }).click();
  await page.locator(".option").first().click();
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => v.id)).toEqual([]);
});

test("every route renders under the production security headers without console errors", async ({ page }) => {
  const problems: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error") problems.push(`${page.url()}: ${m.text()}`);
  });
  page.on("pageerror", (e) => problems.push(`${page.url()}: ${e.message}`));
  for (const route of ROUTES) {
    const response = await page.goto(route);
    expect(response?.status(), route).toBe(200);
    await expect(page.locator("h1")).toBeVisible();
  }
  const csp = (await page.request.get("/")).headers()["content-security-policy"];
  expect(csp).toContain("script-src 'self'");
  expect(problems).toEqual([]);
});
