"""V026: timeline dock - open/close, rows, scrub, retime by dragging, undo, delete, add key by double-click, easing, add track, hidden on phones."""
import json
from harness import *
async def xy(t,id,i): return json.loads(await t.ev(f"JSON.stringify(tlKeyXY('{id}',{i}))"))
async def run(br,site,fx):
    t=await open_page(br,site,"dock",w=1100,h=700); ok=t.ok
    await t.new_project(); await t.add_ply(fx["tilt"]); await t.ev("closeTool()")
    await t.ev("addCamera()"); await t.ev("leaveThru()"); cid=await t.ev("SEL.id"); P=f"o:{cid}:pos"
    await t.ev(f"tlKey('{P}',0,[0,0,0]);tlKey('{P}',2,[2,0,0]);tlKey('s:exp',1,[0.5])")
    ok("dock is closed by default",not await t.pg.is_visible("#tld"))
    await t.pg.click("#tlBtn"); await t.wait(500)
    ok("timeline button opens the dock",await t.pg.is_visible("#tld") and (await t.ev("tlRows().length"))==2)
    bb=await t.pg.locator("#tlc").bounding_box(); ok("dock canvas has a size",bb["width"]>500 and bb["height"]>80,bb)
    # scrub on the ruler
    x1=await t.ev("tlT2X(1)"); await t.pg.mouse.click(bb["x"]+x1,bb["y"]+10); await t.wait(200)
    ok("clicking the ruler moves the playhead",abs(await t.ev("TL.t")-1)<0.04,await t.ev("TL.t"))
    ok("moving the playhead moves the camera",abs(json.loads(await t.ev("JSON.stringify(SEL.pos)"))[0]-1.0)<0.05)
    # drag the key at 2s to 3s
    k=await xy(t,P,1); dx=await t.ev("tlT2X(3)-tlT2X(2)")
    await t.pg.mouse.move(bb["x"]+k["x"],bb["y"]+k["y"]); await t.pg.mouse.down(); await t.pg.mouse.move(bb["x"]+k["x"]+dx/2,bb["y"]+k["y"],steps=5); await t.pg.mouse.move(bb["x"]+k["x"]+dx,bb["y"]+k["y"],steps=5); await t.pg.mouse.up(); await t.wait(200)
    t2=await t.ev(f"TL.tracks['{P}'].k[1].t"); ok("dragging a diamond retimes the key",abs(t2-3)<0.04,t2)
    await t.pg.keyboard.press("Control+z"); await t.wait(200)
    ok("Ctrl+Z puts the key back",abs(await t.ev(f"TL.tracks['{P}'].k[1].t")-2)<0.04)
    # select + ease
    k=await xy(t,P,0); await t.pg.mouse.click(bb["x"]+k["x"],bb["y"]+k["y"]); await t.wait(150)
    ok("clicking a key selects it",(await t.ev("TLU.sel.length"))==1)
    await t.pg.click("[data-tla=ease][data-e=linear]"); await t.wait(150)
    ok("Linear button sets the key's easing",(await t.ev(f"TL.tracks['{P}'].k[0].e"))=="linear")
    # delete selected key; the camera object must stay
    n=await t.ev("OBJS.length"); await t.pg.locator("#tlc").focus(); await t.pg.keyboard.press("Delete"); await t.wait(200)
    ok("Delete removes the selected key",(await t.ev(f"TL.tracks['{P}'].k.length"))==1)
    ok("Delete does not remove the object",(await t.ev("OBJS.length"))==n)
    # double-click an empty spot on a row adds a key
    k=await xy(t,P,0); x4=await t.ev("tlT2X(4)")
    await t.pg.mouse.dblclick(bb["x"]+x4,bb["y"]+k["y"]); await t.wait(200)
    ok("double-click on a row adds a key",(await t.ev(f"TL.tracks['{P}'].k.length"))==2)
    # add a track from the list
    await t.pg.select_option("#tlAdd","s:con"); await t.pg.click("[data-tla=add]"); await t.wait(200)
    ok("Add a track keys that property at the playhead",await t.ev("!!TL.tracks['s:con']") and (await t.ev("tlRows().length"))==3)
    # zoom + fit
    await t.pg.mouse.move(bb["x"]+400,bb["y"]+60); await t.pg.keyboard.down("Control"); await t.pg.mouse.wheel(0,-300); await t.pg.keyboard.up("Control"); await t.wait(150)
    ok("Ctrl+wheel zooms the time axis",(await t.ev("TLU.v1-TLU.v0"))<5.9)
    await t.pg.click("[data-tla=fit]"); ok("Fit shows the whole length",abs(await t.ev("TLU.v1-TLU.v0")-6)<1e-6)
    # play moves the playhead
    await t.pg.click("#tlPlay"); await t.wait(900); ok("Play from the dock runs the timeline",(await t.ev("TL.t"))>0.3 and (await t.ev("!!anim&&anim.tl"))==True,await t.ev("TL.t"))
    await t.pg.click("#tlPlay"); await t.wait(200)
    await t.pg.click("[data-tla=close]"); await t.wait(200); ok("Close hides the dock",not await t.pg.is_visible("#tld"))
    ok("keys saved in the project",(await t.ev("Object.keys(cur.timeline.tracks).length"))==3)
    ctx2=t.ctx
    # phones are view and play only
    t2=await open_page(br,site,"dock-phone",w=420,h=800); await t2.new_project()
    ok("the timeline button is hidden on phones",not await t2.pg.is_visible("#tlBtn")); r2=t2.finish()
    return t.finish()+[(n,c,d) for n,c,d in r2 if n!="no console or page errors"]
