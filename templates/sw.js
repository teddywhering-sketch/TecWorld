const CACHE_NAME = 'tecworld-pwa-cache-v1';

self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(clients.claim());
});

self.addEventListener('fetch', event => {
  // We just let the network handle everything. This is a minimal SW to enable PWA install prompt.
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
