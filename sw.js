/* Splatbox service worker. App shell is versioned; the AI runtime and model live in their own cache so updates don't re-download 40 MB. */
const VERSION='Version 038';
const BETA=/\/beta\//.test(self.registration.scope);
const CACHE=(BETA?'splatbox-beta-':'splatbox-')+VERSION;
const AI='splatbox-ai';
const SHELL=['./','index.html','manifest.webmanifest','icon-192.png','icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith(BETA?'splatbox-beta-':'splatbox-Version')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  const u=new URL(e.request.url);
  if(u.origin!==location.origin)return;
  if(!BETA&&u.pathname.includes('/beta/'))return;
  const heavy=/\/(lib|model)\//.test(u.pathname);
  e.respondWith(caches.open(heavy?AI:CACHE).then(async c=>{
    const hit=await c.match(e.request);
    if(hit)return hit;
    const r=await fetch(e.request);
    if(r.ok)c.put(e.request,r.clone());
    return r;
  }));
});
