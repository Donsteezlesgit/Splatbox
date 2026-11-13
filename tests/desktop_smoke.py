"""Desktop wrapper smoke test (not in run.py: needs Electron installed in desktop/). Run: (cd desktop && npm i && node prepare.js) && python3 tests/desktop_smoke.py"""
import subprocess, time, sys, os, json
from playwright.sync_api import sync_playwright
D="/home/claude/donsteezlesgit/splatbox/desktop"
p=subprocess.Popen(["xvfb-run","-a",D+"/node_modules/.bin/electron",D,"--no-sandbox","--use-angle=swiftshader","--enable-unsafe-swiftshader","--ignore-gpu-blocklist","--remote-debugging-port=9333"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
try:
    with sync_playwright() as pw:
        b=None
        for i in range(40):
            try: b=pw.chromium.connect_over_cdp("http://127.0.0.1:9333"); break
            except Exception: time.sleep(0.5)
        assert b, "no electron"
        pg=None
        for i in range(40):
            for c in b.contexts:
                for x in c.pages:
                    if x.url.startswith("app://"): pg=x
            if pg: break
            time.sleep(0.5)
        assert pg, "no app page"
        pg.wait_for_timeout(2500)
        r=pg.evaluate("""async()=>{
          const o={url:location.href,title:document.title,ver:(typeof VERSION!=='undefined'?VERSION:null)};
          o.canvas=!!document.querySelector('canvas');
          o.desk=!!window.splatboxDesktop;
          const c=document.createElement('canvas');o.gl2=!!c.getContext('webgl2');
          const w=await fetch('model/dav2s.1.wasm',{method:'HEAD'});o.wasm=[w.status,w.headers.get('content-type')];
          const s=await fetch('sw.js');o.sw=s.status;
          const m=await import('./lib/splatjs/index.js');o.splatjs=Object.keys(m).length>0;
          const t=await fetch('../../etc/passwd');o.trav=t.status;
          o.idb=await new Promise(res=>{const q=indexedDB.open('t');q.onsuccess=()=>res(true);q.onerror=()=>res(false)});
          o.fsa=typeof showDirectoryPicker;
          return o}""")
        print(json.dumps(r))
finally:
    p.terminate()
