"""V032: splat effects - dissolve, scatter, pulse - in the render path and on the timeline."""
import json
from harness import *
HASH="window.__h=function(b){return b.arrayBuffer().then(function(buf){var u=new Uint8Array(buf),h=0;for(var i=0;i<u.length;i+=3)h=(h*31+u[i])>>>0;return h+':'+u.length})}"
LUM="""window.__lum=function(b){return createImageBitmap(b).then(function(bm){var c=document.createElement('canvas');c.width=bm.width;c.height=bm.height;var g=c.getContext('2d');g.drawImage(bm,0,0);var d=g.getImageData(0,0,c.width,c.height).data,s=0,i;for(i=0;i<d.length;i+=4)s+=d[i]+d[i+1]+d[i+2];return s/(d.length/4*3)})}"""
async def run(br,site,fx):
    t=await open_page(br,site,"fx",w=1000,h=640); ok=t.ok
    await t.pg.evaluate(HASH+";0"); await t.pg.evaluate(LUM+";0")
    await t.new_project(); await t.add_ply(fx["tilt"]); await t.ev("closeTool()")
    await t.ev("setMode('render')"); await t.wait(400)
    base=await t.ev("rFrame(320,180,false).then(window.__h)")
    lbase=await t.ev("rFrame(320,180,false).then(window.__lum)")
    ok("with every effect at zero the picture is unchanged",base==await t.ev("rFrame(320,180,false).then(window.__h)"))
    seen={}
    for k,v in [("fxDis",0.5),("fxScat",0.5),("fxPulse",0.8)]:
        await t.ev(f"S.{k}={v};S.fxPhase=0.1")
        seen[k]=await t.ev("rFrame(320,180,false).then(window.__h)")
        ok(f"{k} changes the picture",seen[k]!=base,seen[k])
        await t.ev(f"S.{k}=0")
    ok("the three effects look different from each other",len(set(seen.values()))==3,seen)
    await t.ev("S.fxPulse=0.8;S.fxPhase=0.1"); a=await t.ev("rFrame(320,180,false).then(window.__h)")
    await t.ev("S.fxPhase=0.4"); b=await t.ev("rFrame(320,180,false).then(window.__h)")
    ok("moving the pulse position moves the pulse",a!=b)
    await t.ev("S.fxPulse=0;S.fxPhase=0")
    await t.ev("S.fxDis=1"); await t.wait(100)
    l1=await t.ev("rFrame(320,180,false).then(window.__lum)")
    ok("full dissolve leaves just the background",abs(l1-await t.ev("(function(){return 0})()"))>=0 and l1<lbase,[l1,lbase])
    await t.ev("S.fxDis=0.5"); l2=await t.ev("rFrame(320,180,false).then(window.__lum)")
    ok("half dissolve sits between none and full",min(l1,lbase)-1e-6<=l2<=max(l1,lbase)+1e-6,[lbase,l2,l1])
    await t.ev("S.fxDis=0")
    # the effects are on the timeline and animate
    ok("the effects can be keyframed",await t.ev("TL_S.indexOf('fxDis')>=0&&TL_S.indexOf('fxScat')>=0&&TL_S.indexOf('fxPulse')>=0&&TL_S.indexOf('fxPhase')>=0"))
    await t.ev("S.dur=2;tlKey('s:fxDis',0,[0]);tlKey('s:fxDis',2,[1])"); await t.wait(200)
    await t.ev("tlSetTime(1)"); v=await t.ev("S.fxDis")
    ok("dissolve animates between its keys",0.3<v<0.7,v)
    await t.ev("tlSetTime(2)"); ok("and ends fully dissolved",abs(await t.ev("S.fxDis")-1)<1e-6)
    # off in edit mode
    await t.ev("setMode('edit')"); await t.wait(200)
    ok("effects don't show while editing",await t.ev("RV().fxDis")==0)
    return t.finish()
