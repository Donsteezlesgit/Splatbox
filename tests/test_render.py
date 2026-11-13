"""V029: frame-exact render - fixed sizes, transparent background, numbered PNG zip, cancel, determinism."""
import json
from harness import *
ZIPINFO="""window.__zip=function(b){return b.arrayBuffer().then(function(buf){var u=new Uint8Array(buf),dv=new DataView(buf),o=0,out=[];
  while(o+30<=u.length&&dv.getUint32(o,true)===0x04034b50){var sz=dv.getUint32(o+18,true),nl=dv.getUint16(o+26,true),nm=new TextDecoder().decode(u.subarray(o+30,o+30+nl)),d=u.subarray(o+30+nl,o+30+nl+sz),h=0;for(var i=0;i<d.length;i+=7)h=(h*31+d[i])>>>0;out.push([nm,sz,h,d[0],d[1]]);o+=30+nl+sz}
  var e=u.length-22;return JSON.stringify({n:out.length,end:dv.getUint32(e,true)===0x06054b50,count:dv.getUint16(e+10,true),files:out})})}"""
PIX="""window.__pix=function(b,x,y){return createImageBitmap(b).then(function(bm){var c=document.createElement('canvas');c.width=bm.width;c.height=bm.height;var g=c.getContext('2d');g.drawImage(bm,0,0);var d=g.getImageData(x,y,1,1).data,all=g.getImageData(0,0,bm.width,bm.height).data,a0=0,a255=0;for(var i=3;i<all.length;i+=4){if(all[i]===0)a0++;else if(all[i]===255)a255++}return JSON.stringify({w:bm.width,h:bm.height,px:[d[0],d[1],d[2],d[3]],clear:a0,solid:a255,n:all.length/4})})}"""
async def run(br,site,fx):
    t=await open_page(br,site,"render",w=1000,h=640); ok=t.ok
    await t.pg.evaluate(ZIPINFO+";0"); await t.pg.evaluate(PIX+";0"); await t.pg.evaluate("window.__hash=function(b){return b.arrayBuffer().then(function(buf){var u=new Uint8Array(buf),h=0;for(var i=0;i<u.length;i+=5)h=(h*31+u[i])>>>0;return h+':'+u.length})};0")
    await t.new_project(); await t.add_ply(fx["tilt"]); await t.ev("closeTool()")
    await t.ev("setMode('render')"); await t.wait(400)
    # --- single frames
    r=json.loads(await t.ev("rFrame(640,360,false).then(function(b){return window.__pix(b,2,2)})"))
    ok("an opaque frame comes out at exactly the size asked for",r["w"]==640 and r["h"]==360,r)
    ok("an opaque frame has no clear pixels",r["clear"]==0,r["clear"])
    r2=json.loads(await t.ev("rFrame(640,360,true).then(function(b){return window.__pix(b,1,1)})"))
    ok("a transparent frame keeps its size",r2["w"]==640 and r2["h"]==360)
    ok("the background is clear and the splat is solid",r2["px"][3]==0 and r2["clear"]>1000 and r2["solid"]>200,r2)
    ok("the viewer goes back to normal afterwards",(await t.ev("RO===null&&TRANSP===false&&FORCESORT===false")))
    # same frame twice is the same picture
    a=await t.ev("rFrame(480,270,false).then(window.__hash)")
    b=await t.ev("rFrame(480,270,false).then(window.__hash)")
    ok("the same frame rendered twice is byte-identical",a==b,[a,b])
    # --- sequence with timeline keys
    await t.ev("addCamera()"); await t.ev("enterThru(SEL)"); cid=await t.ev("SEL.id"); P=f"o:{cid}:pos"
    await t.ev(f"S.dur=2;S.rfps='10';tlKey('{P}',0,[0,0,1.95]);tlKey('{P}',2,[1.2,0,1.95])"); await t.wait(300)
    z=json.loads(await t.ev("renderSeq({w:320,h:180,fps:10,transp:false}).then(window.__zip)"))
    ok("a sequence is a valid zip with one PNG per frame",z["end"] and z["n"]==20 and z["count"]==20,z["n"])
    names=[f[0] for f in z["files"]]
    ok("frames are numbered in order",names[0].endswith("_0001.png") and names[-1].endswith("_0020.png"),names[:2]+names[-1:])
    ok("every frame is a PNG",all(f[3]==0x89 and f[4]==0x50 for f in z["files"]))
    ok("the animation actually moves between frames",len(set(f[2] for f in z["files"]))>10,len(set(f[2] for f in z["files"])))
    ok("the timeline is back where it was and the viewer is normal",(await t.ev("RJ===null&&RO===null"))==True)
    # transparent sequence
    z2=json.loads(await t.ev("renderSeq({w:320,h:180,fps:10,frames:4,transp:true}).then(window.__zip)"))
    ok("a transparent sequence renders too",z2["n"]==4 and z2["end"])
    # cancel
    await t.ev("window.__p=renderSeq({w:320,h:180,fps:10,transp:false});setTimeout(function(){rjCancel()},120);0")
    res=await t.ev("window.__p.then(function(b){return b===null})")
    ok("Cancel stops a render and cleans up",res==True and (await t.ev("RJ===null&&RO===null")))
    # UI
    await t.ev("openTool('capture')"); await t.wait(300)
    ok("the Capture panel has size, transparent and render controls",(await t.pg.locator('#popB [data-k=rsize]').count())==7 and (await t.pg.locator('#popB [data-k=ralpha]').count())==1 and (await t.pg.locator('#popB [data-act=rFrames]').count())==1)
    await t.pg.click('#popB [data-k=rsize][data-v="1080"]'); ok("picking a size is remembered",(await t.ev("S.rsize"))=="1080")
    await t.pg.check('#popB [data-k=ralpha]'); ok("transparent can be switched on",(await t.ev("S.ralpha"))==True)
    return t.finish()
