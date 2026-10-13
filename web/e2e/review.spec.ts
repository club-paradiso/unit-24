import AxeBuilder from "@axe-core/playwright";
import { expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { content, test } from "./helpers";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => window.localStorage.clear());
});

test("a reviewer records decisions, keeps them across a reload and downloads a valid file", async ({ page }) => {
  await page.goto("/about");
  await page.getByRole("link", { name: "review page" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Review CHP entries against the card" })).toBeVisible();
  await expect(page.getByText(content.source.sha256).first()).toBeVisible();
  await expect(page.getByText("0 of 85 decided")).toBeVisible();

  const download = page.getByRole("button", { name: "Download reviews (.jsonl)" });
  await expect(download).toBeDisabled();
  await page.getByLabel(/your name or handle/i).fill("E2E Reviewer");

  const card = (term: string) => page.locator("article.review-card", { has: page.getByRole("heading", { name: term, exact: true }) });
  await card("10-1").getByLabel(/^Accept/).check();
  await card("10-2").getByLabel(/^Reject/).check();
  await expect(card("10-2").getByText(/Needs attention: Say why/)).toBeVisible();
  await expect(download).toBeDisabled();
  await card("10-2").getByLabel(/notes/i).fill("Not what the card says");

  await page.getByRole("button", { name: "Not taught" }).click();
  const tenFour = card("10-4");
  await expect(tenFour.getByText(/extracted meaning was wrong and is withheld/)).toBeVisible();
  await expect(tenFour.getByLabel(/^Accept/)).toHaveCount(0);
  await tenFour.getByLabel(/^Correct/).check();
  await tenFour.getByLabel("Meaning as printed on the card").fill("Message received");
  await expect(page.getByText("3 of 85 decided")).toBeVisible();

  await page.reload();
  await expect(page.getByText("3 of 85 decided")).toBeVisible();
  await expect(page.getByLabel(/your name or handle/i)).toHaveValue("E2E Reviewer");

  const [file] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Download reviews (.jsonl)" }).click()]);
  const lines = readFileSync((await file.path())!, "utf8").trim().split("\n").map((l) => JSON.parse(l));
  expect(lines).toHaveLength(3);
  const byFact = new Map(lines.map((l) => [l.fact_id, l]));
  const item = (term: string) => content.items.find((i) => i.term === term)!;
  const ex = content.excluded.find((e) => e.term === "10-4")!;
  expect(byFact.get(item("10-1").id)).toMatchObject({ decision: "ACCEPT", meaning_as_printed: null, reviewer: "E2E Reviewer", document_sha256: content.source.sha256 });
  expect(byFact.get(item("10-2").id)).toMatchObject({ decision: "REJECT", notes: "Not what the card says" });
  expect(byFact.get(ex.fact_id)).toMatchObject({ decision: "CORRECT", meaning_as_printed: "Message received", page: 1 });
  for (const l of lines) expect(Object.keys(l).sort()).toEqual(["decision", "document_sha256", "fact_id", "meaning_as_printed", "notes", "page", "reviewed_at", "reviewer", "schema"]);
});

test("the review page has no serious accessibility violations", async ({ page }) => {
  await page.goto("/review");
  await page.getByLabel(/your name or handle/i).fill("A11y");
  await page.locator("article.review-card").first().getByLabel(/^Reject/).check();
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
});
