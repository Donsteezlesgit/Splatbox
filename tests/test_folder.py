"""Project folders (V021): save to a real folder, open from it, folder beats the browser mirror, pruning, bad files, lapse."""
import json
from harness import *
LS="""(async function(){var out={};async function walk(d,p){for await(var [n,h] of d.entries()){if(h.kind==='directory')await walk(h,p+n+'/');else{var f=await h.getFile();out[p+n]=[f.size,f.lastModified]}}}await walk(FOLD.h,'');return JSON.stringify(out)})()"""
async def files(t): return json.loads(await t.ev(LS))
async def run(br,site,fx):
    t=await open_page(br,site,"folder"); ok=t.ok
    ok("folder feature is available in this browser",await t.ev("CAN_FS"))
    await t.ev("navigator.storage.getDirectory().then(function(r){return r.getDirectoryHandle('proj'+Date.now(),{create:true})}).then(function(h){return fsUse(h,false)}).then(function(){return 1})")
    ok("folder connected",await t.ev("FOLD.ok"))
    await t.new_project(); await t.add_ply(fx["tilt"]); await t.add_mesh(fx["cube"]); await t.ev("closeTool()")
    await t.ev("S.vig=0.37;dirty=true")
    await t.pg.click("#saveBtn"); await t.wait(2000)
    f=await files(t); names=sorted(f)
    ok("project.json written",any(n.endswith("/project.json") for n in names),names)
    ok("splat and model saved as separate asset files",sum("/assets/" in n for n in names)>=2,names)
    ok("thumbnail saved",any(n.endswith("/thumb.jpg") for n in names),names)
    ok("a lock note is written",any(n.endswith("/.lock") for n in names),names)
    snapA=await t.ev("snapshotState()"); pid=await t.ev("cur.id"); d0=await t.ev("cur.dir")
    # second save leaves unchanged assets alone
    await t.wait(1100); await t.pg.click("#saveBtn"); await t.wait(1500)
    f2=await files(t); ass=[n for n in f if "/assets/" in n]
    ok("unchanged assets are not rewritten",all(f2[n]==f[n] for n in ass),[n for n in ass if f2.get(n)!=f[n]])
    # folder beats the mirror
    await t.ev("goHome()"); await t.wait(1500)
    await t.ev("idbPut(Object.assign({},{v:FORMAT,id:'"+pid+"',name:'MIRROR COPY',kind:'space',created:1,updated:Date.now()+99999,settings:{},objs:[]}))"); await t.wait(300)
    await t.ev("renderHome()"); await t.wait(1200)
    txt=await t.pg.inner_text("#grid")
    ok("home lists the folder's version, not the browser mirror's",("MIRROR COPY" not in txt) and "Untitled space" in txt,txt[:120])
    # open straight from the folder and compare
    await t.pg.locator("#grid .card:not(.new)").first.click(); await t.wait(4000)
    ok("project opened from the folder is identical",json.loads(await t.ev("snapshotState()"))==json.loads(snapA))
    # deleting an object prunes its asset
    await t.ev("OBJS.pop();persistObjs();saveNow()"); await t.wait(1800)
    f3=await files(t)
    ok("a deleted object's asset file is removed",sum("/assets/" in n for n in f3)<len(ass),[n for n in f3])
    # renaming renames the folder
    await t.ev("cur.name='Renamed One';saveNow()"); await t.wait(2500)
    f4=await files(t); top=sorted({n.split('/')[0] for n in f4})
    ok("renaming the project renames its folder",'Renamed_One' in top and 'Untitled_space' not in top,top)
    ok("nothing was lost in the move",any(n=='Renamed_One/project.json' for n in f4) and sum(n.startswith('Renamed_One/assets/') for n in f4)>=1,sorted(f4))
    ok("the open project still reads its files after the move",(await t.ev("packProjects([cur]).arrayBuffer().then(function(b){return b.byteLength})"))>1000)
    snapR=json.loads(await t.ev("snapshotState()"))
    await t.wait(1100); await t.ev("saveNow()"); await t.wait(1500)
    f5=await files(t); ass2=[n for n in f4 if '/assets/' in n]
    ok("saving again after a rename doesn't rewrite assets",all(f5.get(n)==f4[n] for n in ass2),[n for n in ass2 if f5.get(n)!=f4[n]])
    # duplicate gets its own folder
    await t.ev("goHome()"); await t.wait(1500)
    await t.pg.locator("#grid .card:not(.new) .more").first.click(); await t.pg.click(".menu >> text=Duplicate"); await t.wait(1800)
    dirs=await t.ev("Object.keys(FOLD.dirs).length")
    ok("a duplicate is its own folder",dirs==2,dirs)
    # bad and half-synced projects
    await t.ev("FOLD.h.getDirectoryHandle('Broken',{create:true}).then(function(d){return fsWriteFile(d,'project.json',new Blob(['{not json']))})"); await t.wait(300)
    await t.ev("renderHome()"); await t.wait(1200)
    ok("an unreadable project shows a clear card",await t.pg.locator("#grid .card:has-text('Couldn')").count()==1)
    await t.pg.locator("#grid .card:has-text('Couldn')").click(); await t.wait(500)
    ok("opening it is refused politely",("read this" in await t.pg.inner_text("#toast")) and await t.pg.locator("#editor").is_hidden(),await t.pg.inner_text("#toast"))
    # a passing hiccup (one failed write) must NOT lock the folder
    await t.ev("window._ogd=FOLD.h.getDirectoryHandle;var _n=0;FOLD.h.getDirectoryHandle=function(){if(_n++<2)return Promise.reject(new Error('blip'));return window._ogd.apply(FOLD.h,arguments)};0")
    await t.ev("dbPut(Object.assign({},{v:FORMAT,id:'zz0',name:'Blip',kind:'space',created:1,updated:Date.now(),settings:{},objs:[]}))"); await t.wait(6000)
    ok("a short folder blip is retried and the folder stays connected",(await t.ev("FOLD.ok"))==True and (await t.ev("FOLD.lapsed"))==False)
    ok("the blipped project reached the folder",(await t.ev("folderAll().then(function(l){return l.some(function(r){return r.id==='zz0'})})")))
    await t.ev("FOLD.h.getDirectoryHandle=window._ogd;0")
    # folder genuinely lost mid-session: mirror keeps the work, no crash
    await t.ev("FOLD.h.queryPermission=function(){return Promise.resolve('prompt')};FOLD.h.requestPermission=function(){return Promise.resolve('denied')};FOLD.h.getDirectoryHandle=function(){return Promise.reject(new Error('gone'))};FOLD.h.values=function(){throw new Error('gone')};0")
    await t.ev("dbPut(Object.assign({},{v:FORMAT,id:'zz1',name:'After loss',kind:'space',created:1,updated:Date.now(),settings:{},objs:[]}))"); await t.wait(7000)
    ok("a genuinely lost folder drops back to the mirror",(await t.ev("FOLD.ok"))==False and (await t.ev("FOLD.lapsed"))==True)
    ok("the mirror still has the work",(await t.ev("idbAll().then(function(l){return l.some(function(r){return r.id==='zz1'})})")))
    # it reconnects by itself once the permission is back
    await t.ev("delete FOLD.h.queryPermission;delete FOLD.h.requestPermission;FOLD.h.getDirectoryHandle=window._ogd;delete FOLD.h.values;0")
    await t.wait(9000)
    ok("the folder reconnects by itself when it's reachable again",(await t.ev("FOLD.ok"))==True and (await t.ev("FOLD.lapsed"))==False)
    t.errs=[e for e in t.errs if "gone" in e or "Failed" in e or "blip" in e]
    return t.finish()
