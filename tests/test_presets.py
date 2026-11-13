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
    await t.pg.click("#presetList [data-act=pDel]"); await t.wait(500)
    ok("delete removes it",await t.pg.locator("#presetList button:has-text('Night look')").count()==0)
    return t.finish()
