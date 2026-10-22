import { expect } from "@playwright/test";
import { test } from "./helpers";
import { test as base } from "@playwright/test";

test("Traffic Stop beta branches through repeat / clarification and finishes without altering RADIO progress", async ({ page }) => {
  await page.goto("/encounters");
  await page.locator('details[data-scenario="traffic-stop"] summary').click();
  await page.getByRole("link", { name: "Try language practice" }).click();
  await expect(page).toHaveURL(/\/encounters\/traffic-stop$/);
  await expect(page.getByRole("heading", { level: 1, name: /Traffic Stop/ })).toBeVisible();
  await expect(page.getByText(/not legal advice or a response guide/)).toBeVisible();
  await expect(page.getByText(/Do you know why I pulled you over/)).toBeVisible();

  await page.getByRole("button", { name: "Sorry, could you repeat that?" }).click();
  await expect(page.getByText("A polite way to ask for repetition when you did not hear the question.")).toBeVisible();
  await page.getByRole("button", { name: "Continue conversation" }).click();
  await expect(page.getByText("I asked whether you know why I stopped your car.")).toBeVisible();
  await page.getByRole("button", { name: "Thanks for repeating that. I'm not sure." }).click();
  await page.getByRole("button", { name: "Continue conversation" }).click();
  await expect(page.getByText("One of your brake lights appears to be out.")).toBeVisible();
  await page.getByRole("button", { name: "Could you clarify which brake light you mean?" }).click();
  await page.getByRole("button", { name: "Continue conversation" }).click();
  await expect(page.getByText("The left brake light, at the back of the car.")).toBeVisible();
  await page.getByRole("button", { name: "Got it. Thank you." }).click();
  await page.getByRole("button", { name: "Finish practice" }).click();
  await expect(page.getByRole("heading", { name: "Dialogue complete" })).toBeVisible();

  const radioProgress = await page.evaluate(() => window.localStorage.getItem("unit24.progress"));
  expect(radioProgress).toBeNull();
  await page.getByRole("button", { name: "Practice again" }).click();
  await expect(page.getByText(/Do you know why I pulled you over/)).toBeVisible();
});

base("Korean language pilot feedback stays explicitly educational", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("unit24.lang", "ko"));
  await page.goto("/encounters/traffic-stop");
  await expect(page.getByText("실제 경찰 대응 지침이 아닙니다")).toBeVisible();
  await page.getByRole("button", { name: "I guess I was speeding." }).click();
  await expect(page.getByText("다른 표현도 연습해 보세요")).toBeVisible();
  await expect(page.getByText(/확인하지 않은 사실을 추측/)).toBeVisible();
  await page.getByRole("button", { name: "다음 대화" }).click();
  await expect(page.getByText("브레이크등 중 하나가 작동하지 않는 것 같습니다.")).toBeVisible();
});

test("non-pilot scenarios cannot be accessed as interactive dialogue", async ({ page }) => {
  await page.goto("/encounters/id-request");
  await expect(page.getByRole("heading", { name: "Scenario not ready" })).toBeVisible();
  await expect(page.getByRole("link", { name: "All scenarios" })).toBeVisible();
});
