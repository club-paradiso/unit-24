import { expect, test } from "@playwright/test";

test("the interface is Korean by default, the content stays English, and the language can be switched", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "ko");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("무전 용어, 출처까지 확인하며 배우세요");
  await page.getByRole("link", { name: "첫 레슨 시작하기" }).click();
  await expect(page.getByText("카드 1/9")).toBeVisible();
  await expect(page.locator(".study-answer")).toHaveText("Reception poor");

  await page.getByRole("link", { name: "설정" }).click();
  await page.getByRole("button", { name: "English" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Settings");
  await page.reload();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Settings");
});

test("flashcards flip on tap and grade on swipe", async ({ page }) => {
  await page.goto("/chp/flashcards");
  const card = page.locator("article.flashcard");
  const term = await card.locator(".study-term").innerText();
  await card.click();
  await expect(card.locator(".study-answer")).toBeVisible();
  const box = (await card.boundingBox())!;
  const y = box.y + box.height / 2;
  await page.mouse.move(box.x + box.width / 2, y);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 160, y, { steps: 8 });
  await page.mouse.up();
  await expect(page.getByText(/알아요 1/)).toBeVisible();
  await expect(card.locator(".study-term")).not.toHaveText(term);
});
