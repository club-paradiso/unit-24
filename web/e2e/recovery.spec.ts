import { expect } from '@playwright/test';
import { test, answerQuestion, expectFeedback } from './helpers';

test('lesson study, check feedback and completion survive reload without duplicate credit', async ({ page }) => {
  await page.goto('/chp/lessons/radio-traffic');
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await page.reload();
  await expect(page.getByText('Card 2 of 9')).toBeVisible();
  await page.getByRole('button', { name: 'Skip to check' }).click();
  await answerQuestion(page, true);
  const subject = await page.locator('.question-subject').innerText();
  await page.reload();
  await expect(page.locator('.question-subject')).toHaveText(subject);
  await expectFeedback(page, true);
  for (let i = 1; i < 5; i++) {
    await page.getByRole('button', { name: 'Next question' }).click();
    await answerQuestion(page, true);
  }
  await page.getByRole('button', { name: 'See result' }).click();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Lesson complete' })).toBeVisible();
  const state = await page.evaluate(() => JSON.parse(localStorage.getItem('unit24.progress')!));
  expect(state.lessons['radio-traffic'].attempts).toBe(1);
  expect(Object.values(state.activity).reduce((a: number, b) => a + Number(b), 0)).toBe(5);
});

test('invalid nested import is rejected, valid export is restored with a recovery backup', async ({ page }) => {
  await page.goto('/chp/flashcards');
  await page.getByRole('button', { name: 'Show answer' }).click();
  await page.getByRole('button', { name: 'I knew it' }).click();
  await page.goto('/settings');
  const before = await page.evaluate(() => localStorage.getItem('unit24.progress'));
  const broken = { ...JSON.parse(before!), activeSession: { id: 'bad', mode: 'codes', startedAt: 1, cursor: 0, questions: [null], answers: [] } };
  await page.locator('input[type=file]').setInputFiles({ name: 'corrupt.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(broken)) });
  await expect(page.getByRole('status').filter({ hasText: /invalid|inconsistent/i })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('unit24.progress'))).toBe(before);
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download backup' }).click();
  const download = await downloadPromise;
  const path = await download.path();
  expect(path).toBeTruthy();
  await page.locator('input[type=file]').setInputFiles(path!);
  await expect(page.getByRole('status').filter({ hasText: /restored/i })).toBeVisible();
  expect(JSON.parse((await page.evaluate(() => localStorage.getItem('unit24.progress.before-import')))! )).toEqual(JSON.parse(before!));
});

test('two open tabs retain both flashcard answers', async ({ page, context }) => {
  await page.goto('/chp/flashcards');
  const second = await context.newPage();
  await second.addInitScript(() => localStorage.setItem('unit24.lang', 'en'));
  await second.goto('/chp/flashcards');
  await page.getByRole('button', { name: 'Codes', exact: true }).click();
  await second.getByRole('button', { name: 'Card alphabet', exact: true }).click();
  for (const p of [page, second]) {
    await p.getByRole('button', { name: 'Show answer' }).click();
    await p.getByRole('button', { name: 'I knew it' }).click();
  }
  await page.goto('/progress');
  await expect(page.getByRole('progressbar', { name: 'New', exact: true })).toHaveAttribute('aria-valuenow', '48');
  await second.close();
});

test('all practice modes handle fresh, due and mistake states and history navigation', async ({ page }) => {
  await page.goto('/chp/practice');
  await expect(page.getByRole('button', { name: /Due for review/ })).toBeDisabled();
  await expect(page.getByRole('button', { name: /Review mistakes/ })).toBeDisabled();
  for (const name of [/Codes only/, /Card alphabet/, /Mixed practice/]) {
    await page.goto('/chp/practice');
    await page.getByRole('button', { name }).click();
    await answerQuestion(page, false); await expectFeedback(page, false);
    await page.reload(); await expectFeedback(page, false);
  }
  for (const name of [/Due for review/, /Review mistakes/]) {
    await page.goto('/chp/practice');
    await page.getByRole('button', { name }).click();
    await answerQuestion(page, true); await expectFeedback(page, true);
  }
  await page.goto('/chp/reference?q=crash');
  await page.getByRole('link', { name: /11-82/ }).click();
  await page.goBack();
  await expect(page.getByLabel('Search codes, meanings or letters')).toHaveValue('crash');
});

test('critical pages fit the viewport and contain no runtime errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  for (const path of ['/', '/chp', '/chp/lessons/radio-traffic', '/chp/reference', '/progress', '/settings', '/review']) {
    await page.goto(path);
    await expect(page.locator('main h1')).toBeVisible();
    const dimensions = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth, overflowing: [...document.querySelectorAll('main *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).map(e => ({ tag: e.tagName, class: e.className, text: e.textContent?.slice(0, 80) })) }));
    expect(dimensions.scroll, `${path}: ${JSON.stringify(dimensions)}`).toBeLessThanOrEqual(dimensions.width + 1);
  }
  expect(errors).toEqual([]);
});
