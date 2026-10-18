'use strict';

const OFFLINE_HTML = `<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#08111f"><title>JJRVIS offline</title><style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#08111f;color:#e7eff7;font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.card{max-width:32rem;margin:1.2rem;padding:2rem;border:1px solid #375069;border-radius:16px;background:#101d2e}h1{margin-top:0;color:#edf2f7}button{padding:.8rem 1rem;border:1px solid #77bdf0;border-radius:9px;background:#17609c;color:white;font:inherit}</style><main class="card"><h1>JJRVIS is offline</h1><p>The private command centre cannot reach its broker. Your device has not cached mail, messages, files or private answers.</p><button onclick="location.reload()">Try again</button></main>`;

self.addEventListener('install', event => event.waitUntil(self.skipWaiting()));
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET' || event.request.mode !== 'navigate') return;
  event.respondWith(fetch(event.request, {cache: 'no-store'}).catch(() => new Response(OFFLINE_HTML, {
    status: 503,
    headers: {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'}
  })));
});
