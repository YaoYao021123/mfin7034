const CACHE_NAME = "lecture-portal-v10";
const INDEX_FALLBACK = new URL("./index.html", self.registration.scope).toString();
const CORE_ASSETS = [
  "./index.html",
  "./app-shell.css?v=10",
  "./app-shell.js?v=10",
  "./lecture-enhancements.js?v=4",
  "./manifest.webmanifest",
  "./icon.svg"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const requestUrl = new URL(request.url);
  const isShellAsset = ["/html/app-shell.css", "/html/app-shell.js", "/html/lecture-enhancements.js"]
    .some((suffix) => requestUrl.pathname.endsWith(suffix));
  const accept = request.headers.get("accept") || "";
  const isHtml = request.mode === "navigate" || accept.includes("text/html");

  if (isHtml || isShellAsset) {
    event.respondWith(
      fetch(request)
        .then((resp) => {
          if (resp && resp.status === 200) {
            const clone = resp.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return resp;
        })
        .catch(() => caches.match(request).then((cached) => cached || caches.match(INDEX_FALLBACK)))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request)
        .then((resp) => {
          if (!resp || resp.status !== 200) return resp;
          const clone = resp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          return resp;
        })
        .catch(() => caches.match(INDEX_FALLBACK));
    })
  );
});
