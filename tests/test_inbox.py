"""V039 inbox: the queue logic (desktop/inbox.js, run under node) and the app-side job runner with a stand-in trainer."""
import json, os, subprocess, base64, io, tempfile
import numpy as np
from PIL import Image
from harness import *
STUB="""(function(){
window.__ibCalls=[];window.__ibFiles={};window.__ibCbs={};window.__ibHello=[];
var st={config:{dir:'',enabled:false,quality:'',startWithWindows:false},jobs:[],pause:'',problem:'',running:null,ready:false};
window.__ibSt=st;
window.splatboxDesktop={inbox:{
 state:function(){return Promise.resolve(st)},
 config:function(p){Object.assign(st.config,p);return Promise.resolve(st)},
 scan:function(){return Promise.resolve(st)},
 pick:function(){return Promise.resolve('C:\\\\Dropbox\\\\Splatbox Inbox')},
 hello:function(i){window.__ibHello.push(i);return Promise.resolve(st)},
 read:function(n,f){var b=window.__ibFiles[n+'/'+f];return b?Promise.resolve(b):Promise.reject(new Error('missing'))},
 report:function(m){window.__ibCalls.push(m);return Promise.resolve({ok:true})},
 onJob:function(cb){window.__ibCbs.job=cb},onAbort:function(cb){window.__ibCbs.abort=cb},onState:function(cb){window.__ibCbs.state=cb}
}};})();"""
FAKE="""ibLoadTrainer=function(){return Promise.resolve({createSession:function(cfg){
 var ev={};var s={recon:{cams:[]},training:false,
  on:function(k,f){ev[k]=f},
  load:function(srcs){s.recon.cams=srcs.map(function(_,i){return {imgIdx:i,R:[0,0,0,0,0,0,0,0,1]}});return Promise.resolve()},
  solve:function(){if(window.__ibSolve!=null)s.recon.cams=s.recon.cams.slice(0,window.__ibSolve);return Promise.resolve()},
  seed:function(){return Promise.resolve()},
  start:function(){s.training=true;setTimeout(function(){if(ev.stage)ev.stage({stage:'train'});if(ev.metrics)ev.metrics({iter:100});if(!window.__ibHang&&ev.event)ev.event({kind:'train-complete'})},60)},
  finish:function(){s.training=false;return Promise.resolve()},
  exportPlyBlob:function(){return Promise.resolve(window.__ibPly)},
  _camerasUp:function(){return [0,1,0]},dispose:function(){window.__ibDisposed=(window.__ibDisposed||0)+1}};
 return s}})};"""
def jpg(i,junk=False):
    if junk: return b"this is not a picture at all"
    rng=np.random.default_rng(i); a=(rng.random((60,80,3))*255).astype("uint8")
    b=io.BytesIO(); Image.fromarray(a).resize((640,480),Image.NEAREST).save(b,"JPEG",quality=90); return b.getvalue()
def put(t,job,n,junk=()):
    return t.pg.evaluate("(a)=>{a.forEach(function(x){window.__ibFiles[x[0]]=Uint8Array.from(atob(x[1]),function(c){return c.charCodeAt(0)})})}",
        [[job+"/IMG_%03d.jpg"%i,base64.b64encode(jpg(i,i in junk)).decode()] for i in range(n)])
def jobj(name,n,project=None,key=None,quality=""):
    return json.dumps({"name":name,"project":project or name,"quality":quality,"dir":"x","photos":["IMG_%03d.jpg"%i for i in range(n)],"key":key or name+"|sig","attempt":1})
async def last(t,kind=None,since=0):
    for _ in range(200):
        cs=json.loads(await t.pg.evaluate("JSON.stringify(window.__ibCalls)"))[since:]
        if any(c["kind"] in ("done","failed","blocked") for c in cs): return cs
        await t.wait(100)
    return json.loads(await t.pg.evaluate("JSON.stringify(window.__ibCalls)"))[since:]
async def ncalls(t): return len(json.loads(await t.pg.evaluate("JSON.stringify(window.__ibCalls)")))
async def run(br,site,fx):
    results=[]
    # ---- queue logic under node
    r=subprocess.run(["node",os.path.join(ROOT,"tests","inbox_queue.js")],capture_output=True,text=True,timeout=300)
    for line in r.stdout.splitlines():
        if line.startswith("PASS "): results.append(("queue: "+line[5:],True,""))
        elif line.startswith("FAIL "): results.append(("queue: "+line[5:].split("  ->")[0],False,line))
    if not any(x[0].startswith("queue:") for x in results) or r.returncode not in (0,1): results.append(("queue tests ran",False,(r.stdout+r.stderr)[-300:]))
    # ---- app side
    ctx=await br.new_context(viewport={"width":1000,"height":640},screen={"width":1000,"height":640}); await ctx.add_init_script(STUB)
    pg=await ctx.new_page(); t=T(pg,"inbox"); t.ctx=ctx; ok=t.ok
    pg.on("pageerror",lambda e:t.errs.append("PAGEERR "+str(e))); pg.on("console",lambda m: t.errs.append(m.text) if m.type=="error" else None)
    await pg.goto(site.url+"index.html"); await t.wait(1500)
    ok("the app tells the desktop shell it is starting up (fresh)",await pg.evaluate("window.__ibHello.length>0 && window.__ibHello[0].fresh===true"))
    ok("it says it is not ready until a project folder is connected",await pg.evaluate("window.__ibHello[0].ready===false && /project folder/.test(window.__ibHello[0].reason)"))
    ok("the home screen offers to set the inbox up",("Set up inbox" in await pg.inner_text("#ibar")))
    await pg.click("#ibar button[data-a=set]"); await t.wait(500)
    ok("choosing a folder turns the inbox on",await pg.evaluate("window.__ibSt.config.enabled && /Splatbox Inbox/.test(window.__ibSt.config.dir)"))
    if "[high]" not in await pg.inner_text("#ibar"): await pg.click("#ibar button[data-a=toggle]"); await t.wait(300)
    txt=await pg.inner_text("#ibar"); ok("the details explain folder names, quality and how to run a folder again",all(w in txt for w in ("[high]","STATUS.txt","never changed")),txt[:200])
    await pg.evaluate("window.__ev(%r)"%FAKE)
    ply=open(fx["blob"],"rb").read(); await pg.evaluate("(b)=>{window.__ibPly=new Blob([Uint8Array.from(atob(b),function(c){return c.charCodeAt(0)})])}",base64.b64encode(ply).decode())
    # --- blocked while no project folder
    await put(t,"statue",6); n0=await ncalls(t); await pg.evaluate("window.__ev('ibRun(%s)')"%jobj("statue",6).replace("'","\\'"))
    cs=await last(t,since=n0); ok("with no project folder the job is handed back as blocked, not failed",cs and cs[-1]["kind"]=="blocked" and "project folder" in cs[-1]["reason"],cs)
    # --- connect a project folder
    await t.ev("navigator.storage.getDirectory().then(function(r){return r.getDirectoryHandle('proj'+Date.now(),{create:true})}).then(function(h){return fsUse(h,false)}).then(function(){return 1})")
    await t.wait(9000)
    ok("when the folder is connected it reports ready",await pg.evaluate("window.__ibHello[window.__ibHello.length-1].ready===true"),await pg.evaluate("JSON.stringify(window.__ibHello)"))
    # --- a full job through the stand-in trainer, started the way the shell starts it
    n0=await ncalls(t); await pg.evaluate("window.__ibCbs.job(%s)"%jobj("statue",6)); cs=await last(t,since=n0)
    ok("a job ends with done and names the project",cs and cs[-1]["kind"]=="done" and cs[-1]["project"]=="statue",cs[-3:])
    ok("progress was reported along the way",any(c["kind"]=="progress" and "Reading photos" in c["text"] for c in cs) and any(c["kind"]=="progress" and "Training" in c["text"] for c in cs),[c.get("text") for c in cs])
    ok("the trainer was shut down",await pg.evaluate("window.__ibDisposed>=1"))
    LS="""(async function(){var out={};async function walk(d,p){for await(var [n,h] of d.entries()){if(h.kind==='directory')await walk(h,p+n+'/');else{var f=await h.getFile();out[p+n]=f.size}}}await walk(FOLD.h,'');return JSON.stringify(out)})()"""
    f=json.loads(await t.ev(LS)); names=sorted(f)
    ok("the project is in the project folder with its splat and thumbnail",any(n=="statue/project.json" for n in names) and any(n.startswith("statue/assets/") and n.endswith(".ply") for n in names) and "statue/thumb.jpg" in names,names)
    ok("no photos were copied into the project",not any(n.lower().endswith((".jpg",".jpeg",".png",".webp")) and "thumb" not in n for n in names),names)
    pj=json.loads(await t.ev("fsGetFile(FOLD.dirs&&FOLD.h,'x')")) if False else None
    src=json.loads(await t.ev("(async function(){var dh=await FOLD.h.getDirectoryHandle('statue');var f=await fsGetFile(dh,'project.json');return await f.text()})()"))
    ok("the project remembers which inbox folder it came from",src.get("source",{}).get("inbox")=="statue" and src["source"]["photos"]==6,src.get("source"))
    ok("the project holds one splat object",len(src["objs"])==1 and src["objs"][0]["kind"]=="splat",src["objs"])
    # --- same set again (app closed just before it reported back): no second copy
    n0=await ncalls(t); await pg.evaluate("window.__ev('ibRun(%s)')"%jobj("statue",6).replace("'","\\'")); cs=await last(t,since=n0)
    f2=json.loads(await t.ev(LS)); ok("running the same set twice does not make a second project",cs[-1]["kind"]=="done" and sorted(n.split('/')[0] for n in f2 if n.endswith("project.json"))==["statue"],sorted(f2))
    # --- same name, different set: numbered, never overwritten
    await put(t,"statue [high]",6); n0=await ncalls(t); await pg.evaluate("window.__ev('ibRun(%s)')"%jobj("statue [high]",6,project="statue",key="b|sig",quality="high").replace("'","\\'")); cs=await last(t,since=n0)
    ok("a second set with the same name becomes 'statue 2'",cs[-1]["kind"]=="done" and cs[-1]["project"]=="statue 2",cs[-1])
    f3=json.loads(await t.ev(LS)); ok("both projects are in the folder",sum(n.endswith("project.json") for n in f3)==2,sorted(f3))
    # --- it opens like any project
    await t.ev("goHome()"); await t.wait(1500); txt=await pg.inner_text("#grid"); ok("both appear on the home screen",txt.count("statue")>=2,txt)
    await pg.locator("#grid .card:not(.new) >> text=statue 2").first.click(); await t.wait(4500)
    ok("the project opens with the splat in it",await t.ev("OBJS.filter(function(o){return o.kind==='splat'&&o.gs&&o.gs.n>1000}).length")==1)
    await t.ev("goHome()"); await t.wait(800)
    # --- corrupt photos
    await put(t,"dmg",6,junk=(1,3)); n0=await ncalls(t); await pg.evaluate("window.__ev('ibRun(%s)')"%jobj("dmg",6).replace("'","\\'")); cs=await last(t,since=n0)
    ok("unreadable photos are skipped and noted, the rest still make a project",cs[-1]["kind"]=="done" and any("Couldn't read 2" in x for x in cs[-1]["notes"]),cs[-1])
    await put(t,"allbad",5,junk=(0,1,2)); n0=await ncalls(t); await pg.evaluate("window.__ev('ibRun(%s)')"%jobj("allbad",5).replace("'","\\'")); cs=await last(t,since=n0)
    ok("fewer than 3 readable photos fails with a clear reason",cs[-1]["kind"]=="failed" and "Only 2 of 5" in cs[-1]["error"],cs[-1])
    # --- cameras can't be solved
    await put(t,"flat",8); await pg.evaluate("window.__ibSolve=2"); n0=await ncalls(t); await pg.evaluate("window.__ev('ibRun(%s)')"%jobj("flat",8).replace("'","\\'")); cs=await last(t,since=n0)
    ok("if fewer than 3 photos can be placed it fails and says what to do",cs[-1]["kind"]=="failed" and "overlap" in cs[-1]["error"],cs[-1])
    f4=json.loads(await t.ev(LS)); ok("a failed set leaves no half-made project behind",not any(n.startswith("flat/") for n in f4),sorted(f4))
    await pg.evaluate("window.__ibSolve=3"); await put(t,"rough",8); n0=await ncalls(t); await pg.evaluate("window.__ev('ibRun(%s)')"%jobj("rough",8).replace("'","\\'")); cs=await last(t,since=n0)
    ok("a poor solve still saves, with a warning",cs[-1]["kind"]=="done" and any("may be rough" in x for x in cs[-1]["notes"]),cs[-1])
    await pg.evaluate("window.__ibSolve=null")
    # --- the save hits a short folder blip: it retries and finishes, no failure
    await pg.evaluate("window.__ibSaveWaits=[0,300,300,300,300]")
    await put(t,"blip",6)
    await t.ev("window.__realGet=FOLD.h.getDirectoryHandle.bind(FOLD.h);var _bn=0;FOLD.h.getDirectoryHandle=function(){return (_bn++<4)?Promise.reject(new Error('blip')):window.__realGet.apply(null,arguments)};0")
    n0=await ncalls(t); await pg.evaluate("window.__ev('ibRun(%s)')"%jobj("blip",6).replace("'","\\'")); cs=await last(t,since=n0)
    ok("a short folder blip during the save is retried and the job still finishes",cs[-1]["kind"]=="done" and cs[-1]["project"]=="blip",cs[-1])
    await t.ev("FOLD.h.getDirectoryHandle=window.__realGet;0")
    # --- the folder stays unreachable: the finished scan is kept, the job is blocked (not failed), then finishes without training again
    await put(t,"lapse",6)
    await t.ev("FOLD.h.getDirectoryHandle=function(){var e=new Error('disk gone');e.name='NotFoundError';return Promise.reject(e)};0")
    n0=await ncalls(t); await pg.evaluate("window.__ev('ibRun(%s)')"%jobj("lapse",6).replace("'","\\'")); cs=await last(t,since=n0)
    ok("if the folder stays gone the job is blocked, not failed",cs[-1]["kind"]=="blocked" and "project folder" in cs[-1]["reason"],cs[-1])
    ok("the finished scan is kept in memory",await t.ev("!!IBHOLD&&IBHOLD.job==='lapse'"))
    await t.ev("FOLD.h.getDirectoryHandle=window.__realGet;0"); await pg.evaluate("window.__ibSaveWaits=[0,300,300]")
    n1=await pg.evaluate("window.__ibTrains||0")
    n0=await ncalls(t); await pg.evaluate("window.__ev('ibRun(%s)')"%jobj("lapse",6).replace("'","\\'")); cs=await last(t,since=n0)
    ok("when the folder is back the held scan is saved",cs[-1]["kind"]=="done" and cs[-1]["project"]=="lapse",cs[-1])
    ok("the hold is cleared",await t.ev("IBHOLD===null"))
    await pg.evaluate("window.__ibSaveWaits=null")
    # --- a folder that was lost less than a minute ago doesn't pause the inbox
    await t.ev("FOLD.ok=false;FOLD.lapsed=true;FOLD.lapsedAt=Date.now()-5000;0")
    ok("a folder lost a few seconds ago doesn't pause the inbox yet",await t.ev("ibStatus().ready")==True)
    await t.ev("FOLD.lapsedAt=Date.now()-120000;0")
    ok("a folder lost for over a minute does pause it",await t.ev("ibStatus().ready")==False)
    await t.ev("FOLD.ok=true;FOLD.lapsed=false;FOLD.lapsedAt=0;0")
    # --- hand-started scan in progress
    await t.ev("TR={p:{},started:true}"); st=await t.ev("JSON.stringify(ibStatus())"); ok("a scan started by hand pauses the inbox",json.loads(st)["ready"]==False and "by hand" in json.loads(st)["reason"],st)
    await t.ev("TR=null")
    # --- stopped from outside (the shell's watchdog)
    await put(t,"stopme",6); await pg.evaluate("window.__ibHang=true"); await pg.evaluate("window.__ibCbs.job(%s)"%jobj("stopme",6)); await t.wait(1500)
    ok("(a job is in progress, waiting on the trainer)",await t.ev("IBRUN!==null"))
    n1=await ncalls(t); d0=await pg.evaluate("window.__ibDisposed"); await pg.evaluate("window.__ibCbs.abort('stopme')"); await t.wait(800)
    ok("a stop request frees the app straight away",await t.ev("IBRUN===null"))
    ok("and shuts the trainer down",await pg.evaluate("window.__ibDisposed")>d0)
    ok("a stopped job says nothing more (the shell has already moved on)",await ncalls(t)==n1,json.loads(await pg.evaluate("JSON.stringify(window.__ibCalls)"))[n1:])
    await pg.evaluate("window.__ibHang=false"); await put(t,"after",6); await pg.evaluate("window.__ibCbs.job(%s)"%jobj("after",6)); cs=await last(t,since=n1)
    ok("the next job runs normally after a stop",cs and cs[-1]["kind"]=="done" and cs[-1]["project"]=="after",cs[-2:])
    return results+t.finish()
