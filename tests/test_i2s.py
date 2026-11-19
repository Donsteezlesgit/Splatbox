"""V057 image to splat: the desktop side under node (desktop/i2s.js, stand-in model) and the app side with a stand-in desktop shell."""
import json, os, subprocess, base64
from harness import *
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUB="""(function(){
window.__i2={calls:[],st:{installed:false,busy:'',stage:'',logPath:'C:\\\\x\\\\image-to-splat.log'},mode:'ok',logOpened:0,cb:null,cancelled:0};
var I=window.__i2;
window.splatboxDesktop={i2s:{
 status:function(){return Promise.resolve(JSON.parse(JSON.stringify(I.st)))},
 setup:function(){I.calls.push('setup');if(I.cb)I.cb({stage:'venv',text:'Making a private Python environment',i:2,n:5});
   return new Promise(function(res){setTimeout(function(){
     if(I.mode==='nopython')res({error:{code:'nopython',message:'Python 3.10 or newer was not found.'}});
     else{I.st.installed=true;res({status:JSON.parse(JSON.stringify(I.st))})}},300)})},
 generate:function(o){I.calls.push({gen:o.name,n:o.bytes.length,count:o.count,steps:o.steps});
   if(I.cb)I.cb({stage:'running',text:'Making the splat',i:3,n:20});
   return new Promise(function(res){I.res=res;if(I.mode==='hold')return;setTimeout(function(){I.finish()},250)})},
 cancel:function(){I.cancelled++;if(I.res)I.res({error:{code:'cancelled',message:'Cancelled.'}});return Promise.resolve(true)},
 tail:function(){return Promise.resolve('log')},
 openLog:function(){I.logOpened++;return Promise.resolve({ok:true})},
 onProgress:function(cb){I.cb=cb}
}};
I.finish=function(){
 if(I.mode==='oom'){I.res({error:{code:'oom',message:'The graphics card ran out of memory.'}});return}
 if(I.mode==='boom'){I.res({error:{code:'failed',message:'RuntimeError: shape mismatch'}});return}
 I.res({ply:Uint8Array.from(atob(I.plyB64),function(c){return c.charCodeAt(0)}),count:64,seconds:1.5,gpu:'Fake'});
};
})();"""
JPG=base64.b64decode("/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=")

async def desk(br,site,fx,mode="ok"):
    ctx=await br.new_context(viewport={"width":1440,"height":900},screen={"width":1440,"height":900}); await ctx.add_init_script(STUB)
    pg=await ctx.new_page(); t=T(pg,"i2s"); t.ctx=ctx
    pg.on("pageerror",lambda e:t.errs.append("PAGEERR "+str(e)))
    pg.on("console",lambda m: t.errs.append(m.text) if m.type=="error" else None)
    await pg.goto(site.url+"index.html"); await pg.wait_for_timeout(800)
    # a real-format splat (the same 17 properties TripoSplat writes), made by the fixtures
    import numpy as np, fixtures
    arr=fixtures.rows(np.random.default_rng(3).normal(size=(64,3)),[0.8,0.4,0.2])
    await pg.evaluate("(a)=>{window.__i2.plyB64=a;window.__i2.mode=%s}"%json.dumps(mode),base64.b64encode(fixtures.ply(arr)).decode())
    return t

async def file_in(t,name="mug.jpg"):
    await t.pg.set_input_files("#i2sIn",files=[{"name":name,"mimeType":"image/jpeg","buffer":JPG}])

async def run(br,site,fx):
    results=[]
    # ---- the desktop side under node
    r=subprocess.run(["node",os.path.join(ROOT,"tests","i2s_node.js")],capture_output=True,text=True,timeout=120)
    results.append(("desktop module: stand-in model, set up, errors, cancel, log",r.returncode==0 and "OK" in r.stdout,(r.stdout+r.stderr)[-300:]))

    # ---- plain browser (web / phone): nothing about it shows
    t=await open_page(br,site,"i2sweb",w=1440,h=900); ok=t.ok
    await t.new_project(); await t.ev("openTool('add')"); await t.wait(200)
    ok("web: no image-to-splat controls",(await t.ev("!$('i2sGo')&&!$('i2sNote')")))
    ok("web: the old Add buttons are still there",(await t.ev("$('popB').innerText.indexOf('Photos to splat')>=0")))
    results+=t.finish(); await t.ctx.close()

    # ---- desktop, not set up yet
    t=await desk(br,site,fx); ok=t.ok
    await t.new_project(); await t.ev("openTool('add')"); await t.wait(300)
    ok("desktop: the Set up button shows, Photo to splat is hidden",(await t.ev("!$('i2sSetup').hidden&&$('i2sGo').hidden")))
    note=await t.ev("$('i2sNote').textContent")
    ok("the note says what set up needs (Python, NVIDIA, about 8 GB)",all(w in note for w in ("Python","NVIDIA","8 GB")),note)
    ok("a log button is always there",(await t.ev("!$('i2sLogB').hidden")))
    await t.pg.click("#i2sLogB"); await t.wait(100)
    ok("Open error log asks the desktop shell to open the log",(await t.ev("window.__i2.logOpened"))==1)
    ok("hover tips exist for the new buttons",(await t.ev("TIPS.i2sGo&&TIPS.i2sSetup&&TIPS.i2sLog&&TIPS.i2sCancel"))and True)
    # set up: progress text while it runs, buttons locked, then Photo to splat appears
    await t.pg.click("#i2sSetup"); await t.wait(120)
    ok("while setting up: progress is shown and the buttons are locked",(await t.ev("$('i2sNote').textContent.indexOf('step 2 of 5')>=0&&$('i2sSetup').disabled")))
    await t.wait(500)
    ok("after set up: Photo to splat shows and Set up is gone",(await t.ev("!$('i2sGo').hidden&&$('i2sSetup').hidden")))
    # make one
    await file_in(t); await t.wait(900)
    c=await t.ev("JSON.stringify(window.__i2.calls.filter(function(x){return x.gen}))")
    ok("the photo bytes, the detail choice and 20 steps went to the shell",json.loads(c)==[{"gen":"mug.jpg","n":len(JPG),"count":131072,"steps":20}],c)
    names=await t.ev("OBJS.map(function(o){return o.kind+':'+o.name}).join()")
    ok("the result is a new splat object named after the photo",names=="splat:AI mug",names)
    ok("the AI note is shown",(await t.ev("($('toast').textContent+$('toastH').textContent).indexOf('invented')>=0")))
    await t.ev("openTool('add')"); await t.wait(250)
    ok("not left locked afterwards (the page opens the new splat; Add shows the button again)",(await t.ev("!$('i2sGo').disabled&&!I2ST.busy&&!$('i2sGo').hidden")))
    # detail choice is passed
    await t.ev("$('i2sCount').value='32768'"); await file_in(t,"b.png"); await t.wait(700)
    c=await t.ev("JSON.stringify(window.__i2.calls.filter(function(x){return x.gen}).map(function(x){return x.count}))")
    ok("the detail dropdown value is used",json.loads(c)==[131072,32768],c)
    results+=t.finish(); await t.ctx.close()

    # ---- failures: out of memory, a crash, no Python
    for mode,want in (("oom","ran out of memory"),("boom","shape mismatch")):
        t=await desk(br,site,fx,mode); ok=t.ok
        await t.new_project(); await t.ev("window.__i2.st.installed=true;openTool('add')"); await t.wait(300)
        await file_in(t); await t.wait(700)
        ok(f"{mode}: the message says what went wrong",(await t.ev("$('toast').textContent+$('toastH').textContent")).find(want)>=0)
        ok(f"{mode}: the pane points at the error log and shows it as an error",(await t.ev("$('i2sNote').textContent.indexOf('error log')>=0&&$('i2sNote').classList.contains('bad')")))
        ok(f"{mode}: no object was added, and it is not stuck locked",(await t.ev("OBJS.length===0&&!I2ST.busy&&!$('i2sGo').disabled")))
        await t.pg.click(".tact"); await t.wait(150)
        ok(f"{mode}: the toast's Open error log button opens the log",(await t.ev("window.__i2.logOpened"))==1)
        await t.ev("window.__i2.mode='ok'"); await file_in(t,"again.jpg"); await t.wait(700)
        ok(f"{mode}: trying again works and clears the error",(await t.ev("OBJS.length===1&&!I2ST.bad&&!I2ST.busy")))
        results+=t.finish(); await t.ctx.close()
    t=await desk(br,site,fx,"nopython"); ok=t.ok
    await t.new_project(); await t.ev("openTool('add')"); await t.wait(300)
    await t.pg.click("#i2sSetup"); await t.wait(700)
    ok("set up failing leaves Set up available and says why",(await t.ev("!$('i2sSetup').hidden&&!$('i2sSetup').disabled&&$('i2sNote').textContent.indexOf('Python 3.10')>=0")))
    results+=t.finish(); await t.ctx.close()

    # ---- cancel
    t=await desk(br,site,fx,"hold"); ok=t.ok
    await t.new_project(); await t.ev("window.__i2.st.installed=true;openTool('add')"); await t.wait(300)
    await file_in(t); await t.wait(300)
    ok("while it runs: Cancel shows, Photo to splat is locked",(await t.ev("!$('i2sCancel').hidden&&$('i2sGo').disabled")))
    ok("progress shows the step count",(await t.ev("$('i2sNote').textContent.indexOf('3 of 20')>=0")))
    await t.pg.click("#i2sCancel"); await t.wait(400)
    ok("Cancel stops it, says cancelled, and unlocks",(await t.ev("window.__i2.cancelled===1&&$('i2sNote').textContent==='Cancelled.'&&!$('i2sGo').disabled&&$('i2sCancel').hidden&&OBJS.length===0")))
    results+=t.finish(); await t.ctx.close()
    return results
