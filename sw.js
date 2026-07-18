const CACHE = 'tidelog-v2';
const SHELL = ['itinerary', 'expenses', 'manifest.json', 'icon-192.png', 'icon-512.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  const url = new URL(req.url);

  // Never cache API calls - always go to network for live Notion data
  if (url.pathname.startsWith('/api/')) return;

  // Pages (itinerary / expenses) -> network-first: 一有新版即刻見到，冇網先用 cache。
  const isDoc = req.mode === 'navigate' || req.destination === 'document';
  if (isDoc) {
    e.respondWith(
      fetch(req)
        .then((resp) => {
          const copy = resp.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          return resp;
        })
        .catch(() => caches.match(req).then((cached) => cached || caches.match('itinerary')))
    );
    return;
  }

  // Other static assets (icons, manifest) -> cache-first.
  e.respondWith(caches.match(req).then((cached) => cached || fetch(req)));
});
