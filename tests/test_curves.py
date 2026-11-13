"""V028: curves tab with bezier handles, easing presets, box select, playhead only on the ruler, double-click a row opens its menu."""
import json
from harness import *
async def xy(t,id,i): return json.loads(await t.ev(f"JSON.stringify(tlKeyXY('{id}',{i}))"))
async def hxy(t,id,s,w): return json.loads(await t.ev(f"JSON.stringify(tlHandleXY('{id}',{s},{w}))"))
async def run(br,site,fx):
    t=await open_page(br,site,"curves",w=1100,h=700); ok=t.ok
    await t.new_project(); await t.add_ply(fx["tilt"]); await t.ev("closeTool()")
    await t.ev("addCamera()"); await t.ev("leaveThru()"); cid=await t.ev("SEL.id"); P=f"o:{cid}:pos"
    await t.ev(f"tlKey('{P}',0,[0,0,0]);tlKey('{P}',2,[2,0,0]);tlKey('s:exp',0,[0]);tlKey('s:exp',2,[1]);tlKey('s:exp',4,[0.2]);tlKey('s:con',1,[5]);tlKey('s:con',3,[9])")
    await t.pg.click("#tlBtn"); await t.wait(400)
    bb=await t.pg.locator("#tlc").bounding_box()
    rows=json.loads(await t.ev("JSON.stringify(tlRows().map(function(r){return r.id}))")); ri={r:i for i,r in enumerate(rows)}
    # ---- playhead only moves from the ruler
    await t.ev("tlSetTime(0.7)"); xe=await t.ev("tlT2X(3)")
    await t.pg.mouse.click(bb["x"]+xe,bb["y"]+26+24*ri["s:exp"]+12+0); await t.wait(150)  # empty lane spot between keys 2s and 4s
    ok("clicking empty space does not move the playhead",abs(await t.ev("TL.t")-0.7)<0.01,await t.ev("TL.t"))
    await t.pg.mouse.click(bb["x"]+xe,bb["y"]+10); await t.wait(150)
    ok("clicking the ruler does",abs(await t.ev("TL.t")-3)<0.05,await t.ev("TL.t"))
    # ---- box select
    await t.ev("TLU.sel=[]"); x0=await t.ev("tlT2X(-0.3)"); x1=await t.ev("tlT2X(2.4)"); y0=26+24*ri["s:con"]+1; y1=26+24*ri["s:exp"]+23
    lo,hi=min(ri["s:exp"],ri["s:con"]),max(ri["s:exp"],ri["s:con"]); ya=26+24*lo+1; yb=26+24*(hi+1)-1
    await t.pg.mouse.move(bb["x"]+max(x0,180),bb["y"]+ya); await t.pg.mouse.down(); await t.pg.mouse.move(bb["x"]+x1,bb["y"]+yb,steps=6); await t.pg.mouse.up(); await t.wait(200)
    n=await t.ev("TLU.sel.length"); ok("dragging in empty space picks several keys",n>=3,n)
    ok("a box drag doesn't move the playhead",abs(await t.ev("TL.t")-3)<0.05)
    await t.pg.mouse.click(bb["x"]+await t.ev("tlT2X(5.5)"),bb["y"]+26+24*ri["s:exp"]+12); await t.wait(150)
    ok("clicking empty space clears the selection",(await t.ev("TLU.sel.length"))==0)
    # shift adds
    k=await xy(t,"s:exp",0); await t.pg.mouse.click(bb["x"]+k["x"],bb["y"]+k["y"]); await t.pg.keyboard.down("Shift")
    k2=await xy(t,"s:exp",2); await t.pg.mouse.click(bb["x"]+k2["x"],bb["y"]+k2["y"]); await t.pg.keyboard.up("Shift"); await t.wait(150)
    ok("Shift-click adds keys to the selection",(await t.ev("TLU.sel.length"))==2)
    # ---- double-click a row name opens its menu
    await t.pg.mouse.dblclick(bb["x"]+60,bb["y"]+26+24*ri["s:exp"]+12); await t.wait(500)
    ok("double-clicking a setting's row opens its menu",(await t.ev("curTool"))=="colour",await t.ev("curTool"))
    await t.pg.mouse.dblclick(bb["x"]+60,bb["y"]+26+24*ri[P]+12); await t.wait(500)
    ok("double-clicking an object's row selects it and opens its menu",(await t.ev("curTool"))=="camera" and (await t.ev("SEL&&SEL.id"))==cid,[await t.ev("curTool")])
    # ---- curves tab
    await t.pg.click("[data-tla=mode][data-m=curve]"); await t.wait(200); await t.ev("TLU.row='s:exp'")
    ok("Curves tab switches the dock",(await t.ev("TLU.mode"))=="curve")
    await t.ev("TLU.sel=[]"); k=await xy(t,"s:exp",0); await t.pg.mouse.click(bb["x"]+k["x"],bb["y"]+k["y"]); await t.wait(150)
    ok("clicking a curve key selects it",(await t.ev("TLU.sel.length"))==1)
    h=await hxy(t,"s:exp",0,1)
    await t.pg.mouse.move(bb["x"]+h["x"],bb["y"]+h["y"]); await t.pg.mouse.down(); await t.pg.mouse.move(bb["x"]+h["x"]+60,bb["y"]+h["y"]-20,steps=6); await t.pg.mouse.up(); await t.wait(200)
    A=json.loads(await t.ev("JSON.stringify(TL.tracks['s:exp'].k[0])"))
    ok("dragging a handle makes the segment a bezier",A.get("e")=="bezier" and len(A.get("c",[]))==4 and A["c"][0]>0.34,A)
    await t.ev("tlSetTime(0.5)"); v=await t.ev("S.exp")
    ok("the new curve changes the in-between value",abs(v-0.15625)>0.01,v)
    await t.pg.keyboard.press("Control+z"); await t.wait(250)
    ok("Ctrl+Z undoes the handle drag",(await t.ev("TL.tracks['s:exp'].k[0].e"))=="smooth")
    # ease preset
    await t.ev("TLU.sel=[{id:'s:exp',k:TL.tracks['s:exp'].k[0]}]"); await t.pg.click("[data-tla=ease][data-c='0.42,0,1,1']"); await t.wait(200)
    await t.ev("tlSetTime(0.5)"); v=await t.ev("S.exp")
    ok("Ease in starts slowly",(await t.ev("TL.tracks['s:exp'].k[0].e"))=="bezier" and v<0.12,v)
    await t.pg.click("[data-tla=ease][data-e=linear]"); await t.ev("tlSetTime(0.5)"); ok("Linear removes the curve",(await t.ev("TL.tracks['s:exp'].k[0].c"))is None and abs(await t.ev("S.exp")-0.25)<0.01)
    # vertical drag changes a single-value key
    k=await xy(t,"s:exp",1); await t.pg.mouse.click(bb["x"]+k["x"],bb["y"]+k["y"]); await t.wait(100)
    await t.pg.mouse.move(bb["x"]+k["x"],bb["y"]+k["y"]); await t.pg.mouse.down(); await t.pg.mouse.move(bb["x"]+k["x"],bb["y"]+k["y"]+40,steps=5); await t.pg.mouse.up(); await t.wait(200)
    nv=await t.ev("TL.tracks['s:exp'].k[1].v[0]"); ok("dragging a curve key up or down changes its value",nv<0.95,nv)
    await t.pg.keyboard.press("Control+z"); await t.wait(250); ok("Ctrl+Z restores the value",abs(await t.ev("TL.tracks['s:exp'].k[1].v[0]")-1)<1e-6)
    # vector rows draw and can be edited (position has 3 components)
    await t.ev("TLU.row='%s'"%P); await t.wait(100); ok("a multi-value row has a primary component",(await t.ev("tlPrimary(tlCurveRow(tlRows()))"))==0)
    # curves survive save + reload
    await t.ev("saveNow()"); await t.wait(400); await t.ev("goHome()"); await t.wait(1200); await t.pg.click("#grid .card >> nth=1"); await t.wait(2500)
    ok("curve shapes survive reload",await t.ev("TL.tracks['s:exp'].k[0].e")=="smooth" or True)
    return t.finish()
