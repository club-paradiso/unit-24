import { createServer } from 'node:http';
import { readFileSync, existsSync } from 'node:fs';
import { resolve, extname } from 'node:path';
import { expect } from '@playwright/test';
import { test, answerQuestion, expectFeedback } from './helpers';

// Controlled worker lifecycle fixture. The app is the real built application;
// the previous worker is synthetic, so this is not a claim about physical Safari.
for (const legacy of [false, true]) test(`${legacy ? 'legacy shell can recover on normal reload' : 'current shell activates only on request'} and retains quiz feedback offline`, async ({ page, context }) => {
  test.skip(!!process.env.E2E_BASE_URL, 'Requires a loopback worker-version fixture; deployed offline journeys run separately.');
  let upgraded = false;
  const root = resolve('dist');
  const previous = `self.addEventListener('install', e => e.waitUntil(self.skipWaiting()));
    self.addEventListener('activate', e => e.waitUntil((async () => {
      ${legacy ? `const c = await caches.open('workbox-precache-v2-' + self.registration.scope); await c.put('/registerSW.js', new Response('legacy registration'));` : ''}
      await self.clients.claim();
    })()));`;
  const mime: Record<string, string> = { '.js': 'text/javascript', '.html': 'text/html', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.webmanifest': 'application/manifest+json' };
  const server = createServer((req, res) => {
    const pathname = new URL(req.url!, 'http://localhost').pathname;
    res.setHeader('Cache-Control', 'no-store');
    if (pathname === '/sw.js' && !upgraded) {
      res.setHeader('Content-Type', 'text/javascript'); res.end(previous); return;
    }
    const file = resolve(root, '.' + pathname);
    if (!file.startsWith(root + '/') && file !== root) { res.writeHead(400); res.end(); return; }
    const actual = existsSync(file) && extname(file) ? file : resolve(root, 'index.html');
    res.setHeader('Content-Type', mime[extname(actual)] ?? 'application/octet-stream');
    res.end(readFileSync(actual));
  });
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('No fixture port');
  const origin = `http://127.0.0.1:${address.port}`;
  try {
    await page.goto(origin + '/chp/practice');
    await page.evaluate(async () => { await navigator.serviceWorker.ready; });
    await page.reload();
    await expect.poll(() => page.evaluate(() => navigator.serviceWorker.controller !== null)).toBe(true);
    await expect(page.getByRole('button', { name: 'Update and reload' })).toHaveCount(0);
    await page.getByRole('button', { name: /Codes only/ }).click();
    await answerQuestion(page, false); await expectFeedback(page, false);
    const subject = await page.locator('.question-subject').innerText();
    const before = await page.evaluate(() => localStorage.getItem('unit24.progress'));
    upgraded = true;
    await page.evaluate(async () => { const r = await navigator.serviceWorker.getRegistration(); await r!.update(); });
    if (legacy) {
      await expect.poll(() => page.evaluate(async () => !(await caches.match('/registerSW.js')))).toBe(true);
      // Legacy clients have no prompt: activation permits an ordinary reload.
      // It must not force that reload or modify the in-progress answer.
      await expectFeedback(page, false);
      expect(await page.evaluate(() => localStorage.getItem('unit24.progress'))).toBe(before);
      await page.reload();
    } else {
      await expect(page.getByRole('button', { name: 'Update and reload' })).toBeVisible();
      await expect(page.locator('.question-subject')).toHaveText(subject);
      await expectFeedback(page, false);
      expect(await page.evaluate(() => localStorage.getItem('unit24.progress'))).toBe(before);
      await Promise.all([page.waitForEvent('load'), page.getByRole('button', { name: 'Update and reload' }).click()]);
    }
    await expect(page.locator('.question-subject')).toHaveText(subject);
    await expectFeedback(page, false);
    expect(await page.evaluate(() => localStorage.getItem('unit24.progress'))).toBe(before);
    await expect(page.getByRole('button', { name: 'Update and reload' })).toHaveCount(0);
    await context.setOffline(true);
    await page.reload();
    await expectFeedback(page, false);
    await page.goto(origin + '/chp/reference');
    await expect(page.locator('.ref-list li')).toHaveCount(50);
    await context.setOffline(false);
  } finally {
    await context.setOffline(false);
    server.closeAllConnections();
    await new Promise<void>(resolve => server.close(() => resolve()));
  }
});
