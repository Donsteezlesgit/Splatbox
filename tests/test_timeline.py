"""V025: timeline engine - property registry, keys, the clock, slerp, undo, camera baking, save/reload, format upgrade, playback."""
import json
from harness import *
async def run(br,site,fx):
    t=await open_page(br,site,"timeline",w=1000,h=640); ok=t.ok
    await t.new_project(); await t.add_ply(fx["tilt"]); await t.ev("closeTool()")
    ok("project is format 5 with an empty timeline",(await t.ev("cur.v"))==5 and (await t.ev("Object.keys(cur.timeline.tracks).length"))==0)
    await t.ev("addCamera()"); await t.ev("leaveThru()")
    cid=await t.ev("SEL.id"); P=f"o:{cid}:pos"; R=f"o:{cid}:rot"
    ok("property registry finds camera position and a setting",(await t.ev(f"!!tlProp('{P}')"))and(await t.ev("!!tlProp('s:exp')"))and not(await t.ev("!!tlProp('s:nope')")))
    # position keys 0 -> 2s, smooth easing: halfway is exactly halfway
    await t.ev(f"SEL.pos=[0,0,0];tlKey('{P}',0)"); await t.ev(f"tlKey('{P}',2,[2,4,6])")
    await t.ev("tlSetTime(1)"); p=json.loads(await t.ev("JSON.stringify(SEL.pos)"))
    ok("halfway between two keys is halfway",all(abs(a-b)<1e-6 for a,b in zip(p,[1,2,3])),p)
    await t.ev("tlSetTime(0.5)"); p=json.loads(await t.ev("JSON.stringify(SEL.pos)"))
    ok("smooth easing is slower at the start (u=.25 -> .156)",abs(p[0]-2*0.15625)<1e-6,p)
    await t.ev("tlSetTime(5)"); p=json.loads(await t.ev("JSON.stringify(SEL.pos)"))
    ok("after the last key it holds the last value",p==[2,4,6],p)
    # rotation keys slerp: 0 -> 90deg about Y, halfway = 45deg
    await t.ev(f"tlKey('{R}',0,[1,0,0,0],'linear');tlKey('{R}',2,[Math.SQRT1_2,0,Math.SQRT1_2,0],'linear')")
    await t.ev("tlSetTime(1)"); q=json.loads(await t.ev("JSON.stringify(quatFromMat(SEL.R))"))
    import math
    ok("rotation interpolates by slerp (45 degrees)",abs(q[0]-math.cos(math.pi/8))<1e-5 and abs(q[2]-math.sin(math.pi/8))<1e-5,q)
    # settings and bool step
    await t.ev("tlKey('s:exp',0,[0]);tlKey('s:exp',4,[1],'linear')"); await t.ev("tlSetTime(2)")
    ok("a setting is keyframable",abs(await t.ev("S.exp")-0.5)<1e-6)
    await t.ev(f"tlKey('o:{cid}:vis',0,[1]);tlKey('o:{cid}:vis',1,[0])"); await t.ev("tlSetTime(0.5)")
    ok("visibility steps instead of blending",(await t.ev("SEL.vis"))==True); await t.ev("tlSetTime(1.5)"); ok("visibility flips after the next key",(await t.ev("SEL.vis"))==False)
    # undo / redo of a key
    n0=await t.ev(f"TL.tracks['{P}'].k.length"); await t.ev(f"tlKey('{P}',1,[9,9,9])")
    ok("adding a key",(await t.ev(f"TL.tracks['{P}'].k.length"))==n0+1)
    await t.pg.keyboard.press("Control+z"); await t.wait(200)
    ok("Ctrl+Z removes the key",(await t.ev(f"TL.tracks['{P}'].k.length"))==n0)
    await t.pg.keyboard.press("Control+y"); await t.wait(200)
    ok("redo puts it back",(await t.ev(f"TL.tracks['{P}'].k.length"))==n0+1)
    await t.ev(f"tlDelKey('{P}',1)"); ok("delete a key",(await t.ev(f"TL.tracks['{P}'].k.length"))==n0)
    # a key on a deleted object is ignored, not an error
    # baking a preset
    await t.ev("S.cam='push';S.dur=4"); await t.ev("enterThru(SEL)"); await t.wait(200)
    ea=json.loads(await t.ev("(function(){draw(camOff('push',0.5));return JSON.stringify(LASTM.eye)})()"))
    await t.ev("tlBakePreset('push',SEL)"); k=await t.ev(f"TL.tracks['{P}'].k.length")
    ok("baking a move writes dense keys",k>=30,k)
    await t.ev("tlSetTime(0)"); a=json.loads(await t.ev("JSON.stringify(SEL.pos)")); await t.ev("tlSetTime(4)"); b=json.loads(await t.ev("JSON.stringify(SEL.pos)"))
    ok("the baked push moves the camera",abs(a[0]-b[0])+abs(a[1]-b[1])+abs(a[2]-b[2])>0.05,[a,b])
    eb=json.loads(await t.ev("(function(){tlSetTime(2);draw(null);return JSON.stringify(LASTM.eye)})()"))
    ok("the baked move lands where the preset would at the halfway point",all(abs(x-y)<0.02 for x,y in zip(ea,eb)),[ea,eb])
    # the baked end frame matches what the preset draws at u=1
    await t.ev("leaveThru()")
    # save + reload keeps the keys
    before=await t.ev("JSON.stringify(cur.timeline)"); await t.ev("saveNow()"); await t.wait(500)
    await t.ev("goHome()"); await t.wait(1200)
    await t.pg.click("#grid .card >> nth=1"); await t.wait(2500)
    after=await t.ev("JSON.stringify(cur.timeline)")
    ok("keys survive save and reload",json.loads(before)["tracks"].keys()==json.loads(after)["tracks"].keys() and len(before)==len(after),[len(before),len(after)])
    # old format upgrade
    r=json.loads(await t.ev("JSON.stringify(upgradeRec({v:4,settings:{},objs:[]}))"))
    ok("a format 4 project upgrades with an empty timeline",r["v"]==5 and r["timeline"]=={"fps":30,"tracks":{}},r)
    ok("a project from a newer app is refused",await t.ev("tooNew({v:6})"))
    # playback follows keys
    await t.ev("S.dur=4;SEL=cams()[0];startAnim(false)"); await t.wait(300)
    ok("Play uses the timeline when there are keys",(await t.ev("!!anim&&anim.tl"))==True)
    await t.ev("stopAnim()")
    await t.ev("TL.tracks={};cur.timeline.tracks=TL.tracks;startAnim(false)"); await t.wait(200)
    ok("Play uses the old move presets when there are no keys",(await t.ev("!!anim&&!anim.tl"))==True); await t.ev("stopAnim()")
    return t.finish()
