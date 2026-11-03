const CACHE_NAME = 'jarvis-v1';
const ASSETS = [
  '/',
  '/static/styles.css',
  '/static/app.js',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/manifest.json'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.map((k) => k !== CACHE_NAME ? caches.delete(k) : null)
    ))
  );
  return self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  // Network-first strategy for dynamic API and websockets
  if (e.request.url.includes('/api/') || e.request.url.includes('/ws') || e.request.url.includes('/status')) {
    return;
  }
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
