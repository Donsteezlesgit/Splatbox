"""Presets: save every setting + LUT in one project, apply in another."""
import json
from harness import *
from test_roundtrip import PERTURB, LUT
async def run(br,site,fx):
    t=await open_page(br,site,"presets"); ok=t.ok
    await t.new_project()
    await t.ev("Object.assign(S,"+json.dumps({k:v for k,v in PERTURB.items() if k!="ctrlV"})+");cur.lut="+json.dumps(LUT)+";cur.lutName='Test LUT';PF.lutKey='';applyLook();dirty=true")
    want=json.loads(await t.ev("JSON.stringify(S)"))
    await t.ev("openTool('file')")
    await t.pg.click("#presetName"); await t.pg.keyboard.type("Night look")
    await t.pg.click("[data-act=pSave]"); await t.wait(600)
    ok("preset appears in the list",await t.pg.locator("#presetList button:has-text('Night look')").count()==1)
    await t.ev("closeTool()")
    await t.ev("goHome()"); await t.wait(900); await t.new_project()
    ok("a fresh project starts with default settings",(await t.ev("S.vig"))==0 and not await t.ev("!!cur.lut"))
    await t.ev("openTool('file')"); await t.wait(500)
    ok("preset is available in the other project",await t.pg.locator("#presetList button:has-text('Night look')").count()==1)
    await t.pg.click("#presetList button:has-text('Night look')"); await t.wait(700)
    got=json.loads(await t.ev("JSON.stringify(S)"))
    bad=[k for k in want if k!="ctrlV" and got.get(k)!=want[k]]
    ok("every setting came across",not bad,bad)
    ok("the imported LUT came across",(await t.ev("cur.lut"))==LUT and (await t.ev("cur.lutName"))=="Test LUT")
    ok("applying kept the file format marker",(await t.ev("S.ctrlV"))==16)
    await t.ev("goHome()"); await t.wait(900)
    await t.pg.reload(); await t.wait(1000); await t.new_project(); await t.ev("openTool('file')"); await t.wait(400)
    ok("presets survive a page reload",await t.pg.locator("#presetList button:has-text('Night look')").count()==1)
    # V032: presets travel in backup files
    r=json.loads(await t.ev("""presetRecs().then(function(recs){window.__pb=packProjects(recs.concat([{id:'x',name:'Project X',v:FORMAT,settings:{},objs:[]}]));return JSON.stringify({n:recs.length,kind:recs[0]&&recs[0].kind,name:recs[0]&&recs[0].name})})"""))
    ok("backup records include the preset, marked as one",r["n"]==1 and r["kind"]=="preset" and r["name"]=="Night look",r)
    await t.ev("deletePreset(window.__pb&&(presetList().then(function(l){return l[0].id})))")
    await t.ev("presetList().then(function(l){return Promise.all(l.map(function(p){return deletePreset(p.id)}))})"); await t.wait(400)
    ok("presets are gone before import",(await t.ev("presetList().then(function(l){return l.length})"))==0)
    await t.ev("importFiles([new File([window.__pb],'b.splatbox')])"); await t.wait(1200)
    ok("importing the file brings the preset back",(await t.ev("presetList().then(function(l){return l.length+':'+l[0].name})"))=="1:Night look")
    ok("and its settings and LUT with it",(await t.ev("presetList().then(function(l){return l[0].settings.vig>0&&JSON.stringify(l[0].lut)===JSON.stringify("+json.dumps(LUT)+")})")) is True)
    await t.ev("importFiles([new File([window.__pb],'b.splatbox')])"); await t.wait(1000)
    ok("importing twice doesn't duplicate the preset",(await t.ev("presetList().then(function(l){return l.length})"))==1)
    ok("export presets button is in the panel",await t.pg.locator("[data-act=pExport]").count()==1 and await t.pg.locator("[data-act=pImport]").count()==1)
    await t.pg.click("#presetList [data-act=pDel]"); await t.wait(500)
    ok("delete removes it",await t.pg.locator("#presetList button:has-text('Night look')").count()==0)
    return t.finish()
