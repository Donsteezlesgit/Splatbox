"""The /beta/ copy must be fully separate: its own storage, a clear label, assets found."""
from harness import *
async def run(br,site,fx):
    t=await open_page(br,site,"beta-stable")
    await t.new_project(); name=await t.ev("cur.name"); await t.ev("saveNow()"); await t.wait(400)
    t.ok("stable is not beta",(await t.ev("BETA"))==False)
    b=await open_page(br,site,"beta",path="beta/")
    t.ok("beta page knows it is beta",(await b.ev("BETA"))==True and (await b.ev("ROOT"))=="../")
    t.ok("beta label is shown","BETA" in await b.pg.inner_text("#ver"),await b.pg.inner_text("#ver"))
    t.ok("beta badge is shown next to the logo",await b.pg.evaluate("getComputedStyle(document.querySelector('.hbar .word'),'::after').content")=='"BETA"')
    t.ok("beta starts with none of the real projects",await b.pg.locator("#grid .card:not(.new)").count()==0)
    await b.new_project(); await b.ev("saveNow()"); await b.wait(400)
    dbs=await b.pg.evaluate("indexedDB.databases().then(l=>l.map(x=>x.name))")
    t.ok("beta uses its own storage",sorted(dbs)==["splatbox","splatbox-beta"] or "splatbox-beta" in dbs,dbs)
    t.ok("beta can reach the shared lib/model files",await b.pg.evaluate("fetch('../lib/ort.wasm.min.js',{method:'HEAD'}).then(r=>r.ok)"))
    await t.pg.reload(); await t.wait(800)
    t.ok("stable list is untouched by beta",await t.pg.locator("#grid .card:not(.new)").count()==1)
    return t.finish()+b.finish()
