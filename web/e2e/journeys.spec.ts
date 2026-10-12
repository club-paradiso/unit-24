import { expect, test } from "@playwright/test";
import { answerQuestion, content, expectFeedback } from "./helpers";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => window.localStorage.clear());
});

test("choose CHP, study and pass lesson 1; completion survives a reload", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /California Highway Patrol/ }).click();
  await expect(page.getByRole("heading", { level: 1, name: "California Highway Patrol" })).toBeVisible();
  await expect(page.getByText("No human has verified them yet.")).toBeVisible();

  await page.getByRole("link", { name: /Radio reception & message handling/ }).click();
  await expect(page.getByText("Card 1 of 9")).toBeVisible();
  await expect(page.locator(".study-term")).toHaveText("10-1");
  await expect(page.locator(".excerpt mark")).toHaveText("10-1 Reception poor");
  for (let i = 0; i < 8; i++) await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Start the check" }).click();

  for (let i = 0; i < 5; i++) {
    await answerQuestion(page, true);
    await expectFeedback(page, true);
    await page.getByRole("button", { name: i === 4 ? "See result" : "Next question" }).click();
  }
  await expect(page.getByRole("heading", { name: "Lesson complete" })).toBeVisible();
  await expect(page.getByText("5 / 5 correct")).toBeVisible();

  await page.reload();
  await page.goto("/chp");
  await expect(page.getByRole("link", { name: /Radio reception & message handling/ })).toContainText("Complete");
  await expect(page.getByRole("progressbar", { name: "Lessons complete" })).toHaveAttribute("aria-valuenow", "1");
});

test("a wrong answer shows the right one, the summary lists it, and mistakes can be reviewed", async ({ page }) => {
  await page.goto("/chp/practice");
  await page.getByRole("button", { name: /Codes only/ }).click();
  const expected = await answerQuestion(page, false);
  await expectFeedback(page, false);
  await expect(page.locator(".feedback")).toContainText(`The card gives ${expected}`);
  await expect(page.locator(".feedback")).toContainText("not human-verified");
  await page.getByRole("button", { name: "Next question" }).click();
  for (let i = 1; i < 10; i++) {
    await answerQuestion(page, true);
    await page.getByRole("button", { name: i === 9 ? "Finish session" : "Next question" }).click();
  }
  await expect(page.getByRole("heading", { name: "Session summary" })).toBeVisible();
  await expect(page.getByText("90%")).toBeVisible();
  await expect(page.locator(".review-list li")).toHaveCount(1);

  await page.getByRole("button", { name: "Practise these 1 again" }).click();
  await expect(page.getByText("Question 1 of 1")).toBeVisible();
  await answerQuestion(page, true);
  await page.getByRole("button", { name: "Finish session" }).click();
  await expect(page.getByText("100%")).toBeVisible();

  await page.goto("/progress");
  await expect(page.getByRole("heading", { name: /Recent sessions/ })).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(2);
});

test("leaving mid-session and coming back resumes at the same question", async ({ page }) => {
  await page.goto("/chp/practice");
  await page.getByRole("button", { name: /Mixed practice/ }).click();
  for (let i = 0; i < 3; i++) {
    await answerQuestion(page, true);
    await page.getByRole("button", { name: "Next question" }).click();
  }
  await answerQuestion(page, true);
  const subject = await page.locator(".question-subject").innerText();

  await page.goto("/");
  await expect(page.getByText("4 of 10 questions answered")).toBeVisible();
  await page.getByRole("link", { name: "Resume session" }).click();
  await expect(page.getByText("Question 4 of 10")).toBeVisible();
  await expect(page.locator(".question-subject")).toHaveText(subject);
  await expect(page.locator(".feedback-title")).toBeVisible();
  await page.getByRole("button", { name: "Next question" }).click();
  await expect(page.getByText("Question 5 of 10")).toBeVisible();
});

test("reference search leads to the full source and verification record", async ({ page }) => {
  await page.goto("/chp/reference");
  await page.getByLabel("Search codes, meanings or letters").fill("crash");
  await expect(page.locator(".ref-list li")).toHaveCount(2);
  await expect(page).toHaveURL(/q=crash/);
  await page.getByRole("link", { name: /11-82/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Traffic crash - no injury");
  await expect(page.getByText("Not human-verified")).toBeVisible();
  await expect(page.getByText(`sha256:${content.source.sha256}`)).toBeVisible();
  await expect(page.getByText(/Page 1 \(PDF physical page/)).toBeVisible();
  await expect(page.locator(".excerpt mark")).toHaveText("11-82 Traffic crash - no injury");
  await expect(page.getByText("RESEARCH_ONLY")).toBeVisible();

  await page.goto("/chp/reference?type=CHP_CARD_ALPHABET");
  await expect(page.locator(".ref-list li")).toHaveCount(26);
  await page.getByRole("button", { name: /Show the 35 entries/ }).click();
  await expect(page.locator("#excluded-list li")).toHaveCount(35);
  // Rejected meanings are never shown, only their reason.
  await expect(page.locator("#excluded-list")).not.toContainText("Officer requires help, emergency 211 PC Robbery");
});

test("flashcards record recall and feed the review queue", async ({ page }) => {
  await page.goto("/chp/flashcards");
  await page.getByRole("button", { name: "Card alphabet" }).click();
  const term = await page.locator(".study-term").innerText();
  await page.getByRole("button", { name: "Show answer" }).click();
  await expect(page.locator(".study-answer")).toHaveText(content.items.find((i) => i.term === term)!.answer);
  await page.getByRole("button", { name: "Again" }).click();
  await expect(page.getByText(/again 1/)).toBeVisible();

  await page.goto("/progress");
  await expect(page.getByRole("heading", { name: "Needs review (1)" })).toBeVisible();
  await expect(page.locator(".review-list")).toContainText(term);
  await page.goto("/chp/practice");
  await expect(page.getByRole("button", { name: /Review mistakes/ })).toContainText("1 item available");
});

test("unreadable saved progress is replaced and the learner is told", async ({ page }) => {
  await page.evaluate(() => window.localStorage.setItem("unit24.progress", "{broken"));
  await page.goto("/chp");
  await expect(page.getByRole("status").filter({ hasText: "could not be read" })).toBeVisible();
  await page.getByRole("button", { name: "Dismiss" }).click();
  await expect(page.getByText("could not be read")).toHaveCount(0);
  expect(await page.evaluate(() => window.localStorage.getItem("unit24.progress.corrupt-backup"))).toBe("{broken");
});

test("progress can be reset after confirmation", async ({ page }) => {
  await page.goto("/chp/flashcards");
  await page.getByRole("button", { name: "Show answer" }).click();
  await page.getByRole("button", { name: "I knew it" }).click();
  await page.goto("/progress");
  await expect(page.getByRole("progressbar", { name: "Not started" })).toHaveAttribute("aria-valuenow", "49");
  await page.getByRole("button", { name: "Reset progress…" }).click();
  await page.getByRole("button", { name: "Yes, erase everything" }).click();
  await expect(page.getByRole("progressbar", { name: "Not started" })).toHaveAttribute("aria-valuenow", "50");
});

test("unknown pages and items show a helpful not-found page", async ({ page }) => {
  await page.goto("/chp/items/fct_missing");
  await expect(page.getByRole("heading", { name: "That entry does not exist" })).toBeVisible();
  await page.goto("/nowhere");
  await expect(page.getByRole("heading", { name: "That page does not exist" })).toBeVisible();
});
