import { expect, test as base, type Page } from "@playwright/test";
import content from "../src/content/chp.json" with { type: "json" };

type Item = (typeof content.items)[number];
const byTerm = new Map<string, Item>(content.items.map((i) => [i.term, i]));
const byAnswer = new Map<string, Item>(content.items.map((i) => [i.answer, i]));

/** Reads the question on screen and answers it, correctly or not. Returns the expected answer. */
export async function answerQuestion(page: Page, correctly: boolean): Promise<string> {
  const type = (await page.locator(".question-meta .chip").innerText()).trim().toLowerCase();
  const subject = (await page.locator(".question-subject").innerText()).trim();
  if (type.includes("spell")) {
    const words = subject.split(/\s+/).map((l) => byTerm.get(l)!.answer);
    if (!correctly) words[0] = "Wrongword";
    await page.getByLabel(/your answer/i).fill(words.join(" "));
    await page.getByRole("button", { name: "Check" }).click();
    return words.join(" ");
  }
  const expected = type.includes("meaning → code") ? byAnswer.get(subject)!.term : byTerm.get(subject)!.answer;
  const options = page.locator(".options .option-text");
  const texts = await options.allInnerTexts();
  const pick = correctly ? expected : texts.find((t) => t !== expected)!;
  await page.locator(".options .option", { hasText: new RegExp(`^\\d?\\s*${escape(pick)}$`) }).first().click();
  return expected;
}

function escape(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export async function expectFeedback(page: Page, correct: boolean) {
  await expect(page.locator(".feedback-title")).toHaveText(correct ? /Correct/ : /Not quite/);
}

export { content };

/** Most journeys assert English text; Korean (the default) has its own spec. */
export const test = base.extend<{ english: void }>({
  english: [
    async ({ page }, use) => {
      await page.addInitScript(() => window.localStorage.setItem("unit24.lang", "en"));
      await use();
    },
    { auto: true },
  ],
});
