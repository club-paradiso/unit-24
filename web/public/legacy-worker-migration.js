/* The previous release precached registerSW.js but has no waiting-worker UI.
 * Activate this recovery worker for that legacy cache only. Do not reload a
 * learner's open page or touch progress storage. A normal reload can then load
 * the recovered shell. Later releases use the explicit update prompt.
 */
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (!name.startsWith('workbox-precache-')) continue;
      const cache = await caches.open(name);
      const legacy = (await cache.keys()).some(request => new URL(request.url).pathname === '/registerSW.js');
      if (legacy) { await self.skipWaiting(); return; }
    }
  })());
});
