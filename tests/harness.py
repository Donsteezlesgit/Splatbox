"""Shared test plumbing: builds a throw-away copy of the site, serves it, drives it with headless Chromium."""
import os, sys, shutil, tempfile, subprocess, socket, time, json, math, asyncio, atexit, urllib.request
from playwright.async_api import async_playwright
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARGS=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader","--ignore-gpu-blocklist"]
SNAP="""(()=>{const c=document.getElementById('gl'),x=document.createElement('canvas');x.width=c.width>>1;x.height=c.height>>1;const g=x.getContext('2d');g.drawImage(c,0,0,x.width,x.height);return Array.from(g.getImageData(0,0,x.width,x.height).data)})()"""
def dif(a,b,thr=24):
    return sum(1 for i in range(0,len(a),4) if abs(a[i]-b[i])+abs(a[i+1]-b[i+1])+abs(a[i+2]-b[i+2])>thr)
def L(v): return math.sqrt(sum(x*x for x in v))
def sub(a,b): return [x-y for x,y in zip(a,b)]

class Site:
    """Serves app/index.html (with a test hook added) at / and again at /beta/."""
    def __init__(self,src=None):
        src=src or os.path.join(ROOT,"app")
        self.dir=tempfile.mkdtemp(prefix="splatbox-site-")
        for sub in ("","beta"):
            d=os.path.join(self.dir,sub); os.makedirs(d,exist_ok=True)
            html=open(os.path.join(src,"index.html"),encoding="utf-8").read()
            i=html.rindex("})();"); html=html[:i]+"window.__ev=function(c){return eval(c)};\n"+html[i:]
            open(os.path.join(d,"index.html"),"w",encoding="utf-8").write(html)
            shutil.copy(os.path.join(src,"sw.js"),d)
            for f in ("manifest.webmanifest","icon-192.png","icon-512.png"): shutil.copy(os.path.join(ROOT,f),d)
        for sub in ("lib","model"): os.symlink(os.path.join(ROOT,sub),os.path.join(self.dir,sub))
        s=socket.socket(); s.bind(("127.0.0.1",0)); self.port=s.getsockname()[1]; s.close()
        self.proc=subprocess.Popen([sys.executable,"-m","http.server",str(self.port),"--bind","127.0.0.1"],cwd=self.dir,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        atexit.register(self.stop)
        for _ in range(50):
            try: urllib.request.urlopen(f"http://127.0.0.1:{self.port}/index.html",timeout=1); break
            except Exception: time.sleep(0.1)
        self.url=f"http://127.0.0.1:{self.port}/"
    def stop(self):
        try: self.proc.kill()
        except Exception: pass
        shutil.rmtree(self.dir,ignore_errors=True)

class T:
    """One test page: collects console/page errors and PASS/FAIL results."""
    def __init__(self,pg,name): self.pg=pg; self.name=name; self.errs=[]; self.results=[]
    async def ev(self,code): return await self.pg.evaluate(f"window.__ev({code!r})")
    def ok(self,name,cond,detail=""): self.results.append((name,bool(cond),"" if detail=="" else str(detail)))
    async def wait(self,ms): await self.pg.wait_for_timeout(ms)
    async def new_project(self):
        await self.pg.click("#grid .card.new >> nth=0"); await self.wait(900)
    async def add_ply(self,path,ms=1600):
        await self.pg.set_input_files("#objPly",path); await self.wait(ms)
    async def add_mesh(self,path,ms=1200):
        await self.pg.set_input_files("#objMesh",path); await self.wait(ms)
    def finish(self):
        self.ok("no console or page errors",not self.errs,self.errs[:3])
        return self.results

async def open_page(br,site,name,path="",w=900,h=560):
    ctx=await br.new_context(viewport={"width":w,"height":h},screen={"width":w,"height":h},accept_downloads=True); pg=await ctx.new_page()
    t=T(pg,name); t.ctx=ctx
    pg.on("pageerror",lambda e:t.errs.append("PAGEERR "+str(e)))
    pg.on("console",lambda m: t.errs.append(m.text) if m.type=="error" else None)
    await pg.goto(site.url+path+"index.html"); await pg.wait_for_timeout(800)
    return t

async def run_all(tests,only=None):
    from fixtures import make
    site=Site(); fx=make(); allres=[]
    async with async_playwright() as p:
        br=await p.chromium.launch(args=ARGS)
        for name,fn in tests:
            if only and only not in name: continue
            t0=time.time()
            try: res=await fn(br,site,fx)
            except Exception as e: res=[(name+": crashed",False,repr(e)[:300])]
            print(f"\n== {name} ({time.time()-t0:.0f}s)")
            for n,ok,d in res: print(("  PASS " if ok else "  FAIL ")+n+(("  -> "+d) if (d and not ok) or (d and len(d)<80) else ""))
            allres+=res
        await br.close()
    bad=[r for r in allres if not r[1]]
    print(f"\n{len(allres)-len(bad)} passed, {len(bad)} failed")
    return 1 if bad else 0
