"""V046: Space in the timeline, auto smooth, key-all, look-through button, reopen at the camera, lighting (spot, range, gradient), draggable numbers, tooltips."""
import json
from harness import *
async def run(br,site,fx):
    t=await open_page(br,site,"v046",w=1100,h=800); ok=t.ok
    await t.new_project(); await t.add_ply(fx["tilt"])
    # ---- dock is always split
    ok("the outliner and a settings menu are both visible",await t.pg.is_visible("#outl") and await t.pg.is_visible("#pop"))
    # ---- reopen puts the free view at the camera
    await t.ev("addCamera();leaveThru()"); rid=await t.ev("SEL.id")
    await t.ev("var c=findObj('"+rid+"');c.pos=[0.7,0.2,0.4];c.R=rFromEuler(10,30,0);persistObjs();saveNow()"); await t.wait(800)
    await t.ev("window.__p=cur;goHome()"); await t.wait(500); await t.ev("openSpace(window.__p)"); await t.wait(3000)
    d=json.loads(await t.ev("var c=findObj('"+rid+"');var d=0;for(var i=0;i<9;i++)d+=Math.abs(Rm[i]-c.R[i]);JSON.stringify({thru:THRU,d:d})"))
    ok("reopening starts the free view at the camera (not looking through it)",d["thru"]==False and d["d"]<0.05,d)
    await t.ev("removeObj(findObj('"+rid+"'))")
    # ---- space toggles play from the timeline (once, not twice)
    await t.ev("addCamera();leaveThru()"); cid=await t.ev("SEL.id"); P=f"o:{cid}:pos"
    await t.ev(f"tlKey('{P}',0,[0,0,0]);tlKey('{P}',2,[2,0,0]);tlKey('{P}',4,[4,3,0])")
    await t.pg.click("#tlBtn"); await t.wait(400)
    bb=await t.pg.locator("#tlc").bounding_box(); await t.pg.mouse.click(bb["x"]+200,bb["y"]+10); await t.wait(150)
    await t.pg.keyboard.press("Space"); await t.wait(250)
    ok("Space plays when the timeline has focus",await t.ev("!!anim&&!anim.rec"))
    await t.pg.keyboard.press("Space"); await t.wait(250)
    ok("Space pauses again",await t.ev("!anim"))
    # ---- auto smooth: speed carries through the middle key (no stop)
    await t.ev("TLU.sel=[]"); await t.ev("tlAutoSmooth()")
    a=await t.ev(f"tlEval(TL.tracks['{P}'],1.95,tlProp('{P}'))[0]"); b=await t.ev(f"tlEval(TL.tracks['{P}'],2.05,tlProp('{P}'))[0]")
    ok("auto smooth keeps moving through a key",(b-a)>0.05,[a,b])
    ok("every key got the auto ease",await t.ev(f"TL.tracks['{P}'].k.every(function(k){{return k.e==='auto'}})"))
    # ---- key all on an object
    await t.ev("tlSetTime(1)"); n0=await t.ev("Object.keys(TL.tracks).length")
    await t.ev("tlKeyAllToggle(findObj('"+cid+"'))"); n1=await t.ev("Object.keys(TL.tracks).length")
    ok("key-all adds keys for every setting of the camera",n1>n0,[n0,n1])
    await t.ev("tlKeyAllToggle(findObj('"+cid+"'))")
    ok("key-all again removes the keys at the playhead",await t.ev(f"objKeyIds(findObj('{cid}')).every(function(id){{return !keyAt(id)}})"))
    # ---- outliner row has the key-all diamond and delete
    ok("outliner rows have key-all and delete",await t.ev("document.querySelectorAll('#outlB [data-kall]').length")>=1 and await t.ev("document.querySelectorAll('#outlB [data-oa=del]').length")>=1)
    # ---- look-through button is visible with a camera
    ok("the look-through-camera button is visible",await t.pg.is_visible("#camBtn"))
    await t.ev("leaveThru()"); await t.pg.click("#camBtn"); await t.wait(200); ok("it looks through the camera",await t.ev("THRU"))
    await t.pg.click("#camBtn"); await t.wait(200); ok("and leaves again",not await t.ev("THRU"))
    # ---- lights: spot, range, gradient, up to 8; the shader compiles and draws
    await t.ev("leaveThru();addLight('sun');addLight('point');addLight('spot')"); sid=await t.ev("SEL.id")
    await t.ev("SEL.lx={cone:40,soft:0.4,range:2.5,fall:2,side:'gradient',sstr:1,ssoft:0.4};S.lit=1;dirty=true"); await t.wait(500)
    ok("a spot light is a light",await t.ev("isLight(SEL)&&SEL.kind==='spot'"))
    d=json.loads(await t.ev("var L=lightsData(false);JSON.stringify({n:L.n,t:L.lp[11],side:L.ls[8],cone:Math.round(Math.acos(L.la[10])*360/Math.PI)})"))
    ok("the spot reaches the shader with its cone and gradient",d["t"]==2 and d["side"]==1 and abs(d["cone"]-40)<2,d)
    await t.ev("for(var i=0;i<6;i++)addLight('point')"); ok("up to 8 lights are used",await t.ev("lightsData(false).n")==8)
    await t.ev("SEL=findObj('"+sid+"');openTool('light')"); await t.wait(200)
    ok("the light menu shows the spot's own controls",await t.ev("!!document.getElementById('oo-lx_cone')&&!!document.getElementById('oo-lx_range')"))
    # ---- typed value on the camera focus distance slider
    await t.ev("SEL=findObj('"+cid+"');openTool('camera')"); await t.wait(200)
    ok("camera focus distance is a slider with a typed box",await t.ev("!!document.getElementById('oo-cfd')&&document.getElementById('oov-cfd').tagName==='INPUT'"))
    await t.pg.fill("#oov-cfd","3.5"); await t.pg.press("#oov-cfd","Enter"); await t.wait(200)
    ok("typing sets it",abs(await t.ev("findObj('"+cid+"').fdist")-3.5)<0.01)
    ok("no console or page errors",len(t.errs)==0,t.errs[:3])
    return t.finish()
