// sw.js — Plateau Transit Service Worker
// ─────────────────────────────────────────────────────────────────────
// RELEASE DISCIPLINE:
//   Every deploy → update CACHE_VERSION to match CHANGELOG.md entry.
//   The install event deletes ALL caches that don't match this string.
//   Stale caches are the single most common invisible production bug.
// ─────────────────────────────────────────────────────────────────────
const CACHE_VERSION = 'pt-v2026.03.22-1';   // ← BUMP THIS EVERY RELEASE

const SHELL_CACHE  = `${CACHE_VERSION}-shell`;
const DATA_CACHE   = `${CACHE_VERSION}-data`;
const ERROR_QUEUE  = `${CACHE_VERSION}-errors`;   // background-sync queue name

// App shell — cache on install (core files needed to render offline)
const SHELL_URLS = [
  '/',
  '/plateau-transit-v21.html',
  'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css',
  'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js',
  'https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=Space+Mono:wght@400;700&display=swap',
];

// API routes to cache with network-first strategy (fresh when online, stale offline)
const NETWORK_FIRST = [
  '/api/routes',
  '/api/stops',
  '/api/arrivals',
  '/api/vehicles',
];

// ─── Install — cache shell, skip waiting ──────────────────────────────
self.addEventListener('install', event => {
  console.log(`[SW] Installing ${CACHE_VERSION}`);
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then(cache => cache.addAll(SHELL_URLS).catch(err => {
        // Non-fatal: fonts may fail in offline environments
        console.warn('[SW] Shell cache partial failure:', err.message);
      }))
      .then(() => self.skipWaiting())   // Activate immediately, don't wait for tabs to close
  );
});

// ─── Activate — delete ALL old cache versions ─────────────────────────
self.addEventListener('activate', event => {
  console.log(`[SW] Activating ${CACHE_VERSION} — clearing old caches`);
  event.waitUntil(
    caches.keys().then(keys => {
      const toDelete = keys.filter(k =>
        // Delete any cache that doesn't start with our current version
        !k.startsWith(CACHE_VERSION)
      );
      if (toDelete.length) {
        console.log(`[SW] Deleting stale caches:`, toDelete);
      }
      return Promise.all(toDelete.map(k => caches.delete(k)));
    })
    .then(() => self.clients.claim())   // Take control of all open tabs immediately
  );
});

// ─── Fetch — routing strategy ─────────────────────────────────────────
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Skip non-GET, chrome-extension, devtools
  if (event.request.method !== 'GET') return;
  if (url.protocol === 'chrome-extension:') return;

  // API data: Network-first, fall back to cache
  if (NETWORK_FIRST.some(path => url.pathname.startsWith(path))) {
    event.respondWith(networkFirst(event.request, DATA_CACHE));
    return;
  }

  // External CDN resources (Leaflet, fonts): Cache-first
  if (url.origin !== location.origin) {
    event.respondWith(cacheFirst(event.request, SHELL_CACHE));
    return;
  }

  // App shell: Cache-first → network fallback → offline page
  event.respondWith(cacheFirst(event.request, SHELL_CACHE));
});

// ─── Strategies ──────────────────────────────────────────────────────
async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request.clone());
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return offlineFallback(request);
  }
}

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request.clone());
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return offlineFallback(request);
  }
}

function offlineFallback(request) {
  // For navigation requests, serve the cached app shell
  if (request.mode === 'navigate') {
    return caches.match('/plateau-transit-v21.html')
      .then(r => r || new Response('<h1>Offline</h1><p>Plateau Transit requires a connection to load for the first time.</p>', {
        headers: { 'Content-Type': 'text/html' }
      }));
  }
  // For API requests, return a structured offline response
  if (request.url.includes('/api/')) {
    return new Response(JSON.stringify({
      error: 'offline',
      message: 'No connection — showing cached data',
      cached: true,
    }), { headers: { 'Content-Type': 'application/json' } });
  }
  return new Response('', { status: 503 });
}

// ─── Background Sync — flush error queue when online ─────────────────
self.addEventListener('sync', event => {
  if (event.tag === 'flush-errors') {
    event.waitUntil(flushErrorQueue());
  }
});

async function flushErrorQueue() {
  // Read queued errors from clients via postMessage
  // Errors are flushed to the API when connection restores
  const clients = await self.clients.matchAll();
  clients.forEach(client => client.postMessage({ type: 'SW_FLUSH_ERRORS' }));
}

// ─── Message handler — version check ─────────────────────────────────
self.addEventListener('message', event => {
  if (event.data?.type === 'GET_VERSION') {
    event.ports[0]?.postMessage({ version: CACHE_VERSION });
  }
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
