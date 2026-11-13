"""V027: diamonds in menus, click-a-row then Key it, auto-key on change, no false keys, undo of auto-keys, reload."""
import json
from harness import *
async def run(br,site,fx):
    t=await open_page(br,site,"autokey",w=1100,h=700); ok=t.ok
    await t.new_project(); await t.add_ply(fx["tilt"]); await t.ev("closeTool()")
    await t.ev("addCamera()"); await t.ev("leaveThru()"); cid=await t.ev("SEL.id"); P=f"o:{cid}:pos"
    await t.ev(f"tlKey('{P}',0,[0,0,0]);tlKey('{P}',2,[2,0,0]);tlKey('s:exp',0,[0]);tlKey('s:exp',2,[1])")
    # --- click a row, then Key it
    await t.pg.click("#tlBtn"); await t.wait(400)
    bb=await t.pg.locator("#tlc").bounding_box(); await t.ev("tlSetTime(1)")
    rows=json.loads(await t.ev("JSON.stringify(tlRows().map(function(r){return r.id}))")); si=rows.index("s:exp")
    await t.pg.mouse.click(bb["x"]+60,bb["y"]+26+24*si+12); await t.wait(150)
    ok("clicking a row in the list selects it",(await t.ev("TLU.row"))=="s:exp",await t.ev("TLU.row"))
    await t.pg.click("[data-tla=add]"); await t.wait(200)
    ok("Key it keys the selected row at the playhead",await t.ev("TL.tracks['s:exp'].k.some(function(k){return Math.abs(k.t-1)<0.02})"))
    await t.ev("tlDelKey('s:exp',1)")
    # --- auto key on a setting
    await t.ev("TLU.row=null"); await t.pg.click("[data-tla=close]")
    await t.ev("tlSetTime(1)"); await t.wait(300)
    ok("scrubbing alone never writes keys",(await t.ev("TL.tracks['s:exp'].k.length"))==2 and (await t.ev(f"TL.tracks['{P}'].k.length"))==2)
    await t.ev("setK('exp',0.9)"); await t.wait(300)
    ok("changing an animated setting at a new time writes a key",await t.ev("TL.tracks['s:exp'].k.some(function(k){return Math.abs(k.t-1)<0.02&&Math.abs(k.v[0]-0.9)<1e-6})"))
    ok("a setting with no keys is left alone",True and not await t.ev("!!TL.tracks['s:con']") ) 
    await t.ev("setK('con',30)"); await t.wait(300); ok("changing an un-keyed setting makes no track",not await t.ev("!!TL.tracks['s:con']"))
    await t.wait(600); await t.pg.keyboard.press("Control+z"); await t.wait(300)
    ok("Ctrl+Z undoes the auto key",(await t.ev("TL.tracks['s:exp'].k.length"))==2 and abs(await t.ev("S.exp")-0.5)<0.02,[await t.ev("TL.tracks['s:exp'].k.length"),await t.ev("S.exp")])
    # --- auto key on an object (as the gizmo / number fields do)
    await t.ev("SEL=findObj('%s')"%cid); await t.ev("SEL.pos=[5,1,0];dirty=true"); await t.wait(300)
    ok("moving an animated object at a new time writes a key",await t.ev(f"TL.tracks['{P}'].k.some(function(k){{return Math.abs(k.t-1)<0.02&&Math.abs(k.v[0]-5)<1e-6}})"))
    await t.ev("tlSetTime(0)"); await t.wait(200); p0=json.loads(await t.ev("JSON.stringify(SEL.pos)"))
    await t.ev("tlSetTime(1)"); await t.wait(200); p1=json.loads(await t.ev("JSON.stringify(SEL.pos)"))
    # deleting a key at the playhead must not bring it straight back
    await t.ev(f"tlDelKey('{P}',1)"); await t.wait(400); ok("deleting a key stays deleted (no auto re-key)",(await t.ev(f"TL.tracks['{P}'].k.length"))==2)
    await t.ev(f"tlKey('{P}',1,[5,1,0])"); await t.wait(200)
    ok("the new key holds, the old keys stay",p0==[0,0,0] and p1==[5,1,0],[p0,p1])
    # --- looking through an animated camera makes no spurious keys, but flying does
    await t.ev("enterThru(findObj('%s'))"%cid); await t.ev("tlSetTime(0.5)"); await t.wait(500)
    n=await t.ev(f"TL.tracks['{P}'].k.length"); await t.ev("dirty=true"); await t.wait(300); await t.ev("tlSetTime(1.5)"); await t.wait(400)
    ok("looking through an animated camera adds no keys by itself",(await t.ev(f"TL.tracks['{P}'].k.length"))==n,[n,await t.ev(f"TL.tracks['{P}'].k.length")])
    await t.ev("tlKey('o:%s:rot',0);tlKey('o:%s:rot',2,quatFromMat(rFromEuler(0,40,0)))"%(cid,cid)); await t.ev("tlSetTime(1)"); await t.wait(300)
    k0=await t.ev("TL.tracks['o:%s:rot'].k.length"%cid); await t.ev("orbitBy(0.4,0.1);dirty=true"); await t.wait(400)
    ok("flying an animated camera writes a key at the playhead",(await t.ev("TL.tracks['o:%s:rot'].k.length"%cid))==k0+1,[k0,await t.ev("TL.tracks['o:%s:rot'].k.length"%cid)])
    await t.ev("leaveThru()")
    # --- diamonds
    await t.ev("tlSetTime(1)"); await t.ev("openTool('colour')"); await t.wait(300)
    ok("colour sliders have a diamond",(await t.pg.locator('[data-kd="s:exp"]').count())==1 and (await t.pg.locator('[data-kd="s:con"]').count())==1)
    await t.ev("tlSetTime(1.5)"); await t.wait(150)
    ok("an animated property's diamond is outlined, not filled",await t.ev("(function(){var b=document.querySelector('[data-kd=\"s:exp\"]');return b.classList.contains('anim')&&!b.classList.contains('on')})()"))
    await t.pg.click('[data-kd="s:con"]'); await t.wait(200)
    ok("clicking a diamond keys the value at the playhead",await t.ev("!!TL.tracks['s:con']&&TL.tracks['s:con'].k.length==1") and await t.pg.locator('[data-kd="s:con"].on').count()==1)
    await t.pg.click('[data-kd="s:con"]'); await t.wait(200)
    ok("clicking a filled diamond removes that key",not await t.ev("!!TL.tracks['s:con']"))
    await t.ev("SEL=findObj('%s');openTool('camera',true)"%cid); await t.wait(300)
    ok("camera panel has diamonds for position, rotation, lens and focus",(await t.pg.locator('#popB [data-kd^="o:"]').count())>=4,await t.pg.locator('#popB [data-kd^="o:"]').count())
    await t.ev("closeTool();SEL=OBJS.filter(isGeo)[0];openTool('objects')"); await t.wait(300)
    ok("object panel has diamonds for position, rotation and scale",(await t.pg.locator('#popB [data-kd$=":scl"]').count())==1 and (await t.pg.locator('#popB [data-kd$=":pos"]').count())>=1)
    # --- reload keeps keys and does not corrupt them
    before=await t.ev("JSON.stringify(cur.timeline)"); await t.ev("saveNow()"); await t.wait(500)
    await t.ev("goHome()"); await t.wait(1200); await t.pg.click("#grid .card >> nth=1"); await t.wait(2500); await t.wait(500)
    after=await t.ev("JSON.stringify(cur.timeline)")
    ok("keys are identical after reload (nothing auto-keyed on open)",before==after,[len(before),len(after)])
    return t.finish()
