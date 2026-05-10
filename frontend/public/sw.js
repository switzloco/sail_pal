/**
 * Vessel Ops AI — Service Worker
 *
 * Strategy:
 *   • App shell (HTML, JS, CSS, images) → Cache-first, network-fallback
 *   • API calls (/api/*)               → Network-first, cache-fallback
 *   • Everything else                   → Stale-while-revalidate
 *
 * This lets the PWA load instantly even when the hub laptop's Wi-Fi is spotty,
 * while always preferring fresh data for API responses.
 */

const CACHE_NAME = "vessel-ops-v1";

// Core shell assets to precache on install.
// Next.js hashes chunk filenames, so we cache them on first fetch instead.
const PRECACHE_URLS = [
  "/",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

// ─── Install: precache the shell ─────────────────────────────────────────────
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

// ─── Activate: clean old caches ──────────────────────────────────────────────
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

// ─── Fetch: route requests by strategy ───────────────────────────────────────
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests (POST to /api/ai/*, etc.)
  if (request.method !== "GET") return;

  // Skip chrome-extension and other non-http schemes
  if (!url.protocol.startsWith("http")) return;

  // API calls → network-first (try live, fall back to cached)
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Static assets (JS, CSS, images, fonts) → cache-first
  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // HTML pages → stale-while-revalidate (show cached, update in background)
  event.respondWith(staleWhileRevalidate(request));
});

// ─── Strategies ──────────────────────────────────────────────────────────────

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response("Offline", { status: 503 });
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    return cached || new Response(JSON.stringify({ error: "offline" }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    });
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);

  const fetchPromise = fetch(request)
    .then((response) => {
      if (response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => cached);

  return cached || fetchPromise;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function isStaticAsset(pathname) {
  return /\.(js|css|png|jpg|jpeg|svg|webp|gif|ico|woff2?|ttf|eot)(\?.*)?$/.test(
    pathname
  );
}
