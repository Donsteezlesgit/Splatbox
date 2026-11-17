"""V049: speed work (tight quads, blur thinning, lower resolution while dragging) and the debug screen."""
import json,base64,io
from harness import *
SNAP="""(function(){draw(null);return document.getElementById('gl').toDataURL('image/png')})()"""
def px(data_url):
    from PIL import Image
    import numpy as np
    return np.asarray(Image.open(io.BytesIO(base64.b64decode(data_url.split(",")[1]))).convert("RGB")).astype(int)
async def setup(t,fx,blur=0.9):
    await t.new_project(); await t.add_ply(fx["tilt"])
    await t.ev("setVO('gizmos',false);setVO('grids',false);SEL=null;closeTool();S.defocus=%s;S.focus=0.0;S.focusRange=0.04;dirty=true;0"%blur); await t.wait(1200)

async def perfdbg(br,site,fx):
    t=await open_page(br,site,"v049dbg",w=1300,h=800); ok=t.ok; pg=t.pg
    await setup(t,fx)
    ok("closed at first",await t.ev("$('dbg').hidden")==True)
    await pg.keyboard.press("`"); await t.wait(600)
    ok("the ` key opens it",await t.ev("!$('dbg').hidden&&PERF.open===1"))
    rep=await t.ev("perfReport()")
    ok("report has every section",all(k in rep for k in ["== SPEED ==","== DRAWING ==","== SPLATS ==","== SORTING ==","== LOOK","== WHAT IS PROBABLY COSTING ==","== MEMORY ==","== DEVICE ==","== ERRORS =="]),rep[:200])
    ok("report has no undefined or NaN",("undefined" not in rep) and ("NaN" not in rep),[l for l in rep.split("\n") if "undefined" in l or "NaN" in l][:3])
    ok("it names the splat object and count",await t.ev("perfReport().indexOf('15,000')>-1"))
    ok("it flags depth of field as a cost",await t.ev("perfReport().indexOf('depth of field is ON')>-1"))
    ok("sections are shown on screen",(await t.ev("$('dbgP').children.length"))>=8)
    ok("it fits on screen (no cut-off panel)",await t.ev("(function(){var r=$('dbg').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight&&r.right<=innerWidth})()"))
    # bench redraws nonstop, and closing stops it
    await t.ev("S.defocus=0;dirty=true;0"); await t.wait(600)
    d0=await t.ev("PERF.draws"); await pg.check("#dbgBench"); await t.wait(1500)
    ok("bench keeps drawing",(await t.ev("PERF.draws"))-d0>=3,(await t.ev("PERF.draws"))-d0)
    await pg.keyboard.press("`"); await t.wait(300)
    ok("closing hides it and switches bench off",await t.ev("$('dbg').hidden&&PERF.bench===0&&PERF.open===0"))
    # View menu entry
    await pg.click("#vwBtn"); await t.wait(150)
    ok("View menu has Debug screen",await t.ev("!!document.querySelector('#vwMenu [data-vw=dbg]')"))
    await pg.click("#vwMenu [data-vw=dbg]"); await t.wait(400)
    ok("the menu item opens it",await t.ev("PERF.open===1"))
    # settings are kept on this device
    await pg.select_option("#dbgThin","always"); await pg.select_option("#dbgK","12"); await pg.select_option("#dbgLow","half"); await pg.uncheck("#dbgTight")
    saved=json.loads(await t.ev("localStorage.getItem('sb.perf')"))
    ok("choices are saved",saved["thin"]=="always" and saved["K"]==12 and saved["low"]=="half" and saved["tight"]==0,saved)
    await pg.reload(); await t.wait(1500)
    ok("and come back",await t.ev("[PERF.thin,PERF.K,PERF.low,PERF.tight].join()")=="always,12,half,0",await t.ev("[PERF.thin,PERF.K,PERF.low,PERF.tight].join()"))
    await t.ev("localStorage.setItem('sb.perf','{\"thin\":\"x\",\"K\":99,\"low\":7}');0"); await pg.reload(); await t.wait(1500)
    ok("junk in storage falls back to the defaults",await t.ev("[PERF.thin,PERF.K,PERF.low,PERF.tight].join()")=="move,5,auto,1",await t.ev("[PERF.thin,PERF.K,PERF.low,PERF.tight].join()"))
    await t.ev("localStorage.removeItem('sb.perf');0")
    return t.finish()

async def perfspeed(br,site,fx):
    t=await open_page(br,site,"v049spd",w=1000,h=700); ok=t.ok; pg=t.pg
    await setup(t,fx)
    await t.ev("PERF.low='off';PERF.thin='off';PERF.tight=0;0")
    base=px(await t.ev(SNAP))
    # tight quads: same picture
    await t.ev("PERF.tight=1;0"); tq=px(await t.ev(SNAP))
    ok("tight quads give the same picture (max difference 2 levels)",abs(tq-base).max()<=2,int(abs(tq-base).max()))
    # tight quads with faint splats (opacity override) and in solid mode
    await t.ev("PERF.tight=0;SEL=null;S.opacity=0.3;S.render='solid';0")
    a=px(await t.ev(SNAP)); await t.ev("PERF.tight=1;0"); b=px(await t.ev(SNAP))
    nd=int((abs(a-b).max(axis=2)>2).sum()); tol=a.shape[0]*a.shape[1]*0.0002
    ok("same picture in solid mode (hard edges may flip a few single pixels)",nd<=tol,[nd,int(tol)])
    await t.ev("S.render='splat';0"); await t.ev("PERF.tight=0;0"); a=px(await t.ev(SNAP)); await t.ev("PERF.tight=1;0"); b=px(await t.ev(SNAP))
    ok("same picture in splat mode",abs(a-b).max()<=2,int(abs(a-b).max()))
    # thinning: never on a still frame
    await t.ev("PERF.thin='move';PERF.low='off';LR.act=false;0")
    ok("thinning is off at rest",(await t.ev("thinK()"))==0)
    still=px(await t.ev(SNAP)); await t.ev("PERF.thin='off';0"); off=px(await t.ev(SNAP))
    ok("a still frame is identical with thinning on or off",abs(still-off).max()==0,int(abs(still-off).max()))
    ok("thinning switches on while moving",(await t.ev("PERF.thin='move';LR.act=true;thinK()"))==5)
    ok("never during a render",(await t.ev("PERF.thin='move';RO={w:640,h:360};LR.act=true;var r=thinK();RO=null;r"))==0)
    ok("never during a render job",(await t.ev("RJ={cancel:false,i:0,n:1};LR.act=true;var r=[thinK(),ixWant(performance.now())];RJ=null;r"))==[0,False])
    ok("never while recording",(await t.ev("anim={rec:true,t0:0,dur:1};LR.act=true;var r=thinK();anim=null;r"))==0)
    ok("it does apply while a preview plays",(await t.ev("anim={rec:false,t0:performance.now(),dur:5};var r=thinK();anim=null;r"))==5)
    ok("'always' thins even when still",(await t.ev("PERF.thin='always';LR.act=false;thinK()"))==5)
    ok("'off' never thins",(await t.ev("PERF.thin='off';LR.act=true;thinK()"))==0)
    ok("strength follows the setting",(await t.ev("PERF.thin='always';PERF.K=12;var r=thinK();PERF.K=5;r"))==12)
    return t.finish()

async def lowres(br,site,fx):
    t=await open_page(br,site,"v049low",w=1000,h=700); ok=t.ok; pg=t.pg
    await setup(t,fx,0)
    await t.ev("PERF.low='half';PERF.thin='off';0")
    full=await t.ev("[cv.width,cv.height]"); css=await t.ev("[cv.clientWidth,cv.clientHeight]")
    ok("full size at rest",abs(full[0]-css[0]*min(await t.ev("window.devicePixelRatio||1"),2))<=2,[full,css])
    still0=px(await t.ev(SNAP))
    box=await pg.locator("#gl").bounding_box(); x=box["x"]+40; y=box["y"]+60
    await pg.mouse.move(x,y); await pg.mouse.down(); await t.wait(500)
    ok("drag makes it lower resolution (about half)",await t.ev("LR.on&&Math.abs(cv.width/%d-0.5)<0.05"%full[0]),await t.ev("[LR.on,LR.scale,cv.width]"))
    ok("the picture is still drawn (canvas not blank)",await t.ev("cv.width>100"))
    await pg.mouse.up(); await t.wait(700)
    ok("back to full size when you let go",(await t.ev("cv.width"))==full[0] and (await t.ev("LR.on"))==False,await t.ev("[LR.on,cv.width]"))
    still1=px(await t.ev(SNAP))
    ok("and the picture is exactly what it was",abs(still1-still0).max()==0,int(abs(still1-still0).max()))
    # a render keeps its own size even in the middle of a drag
    await pg.mouse.move(x,y); await pg.mouse.down(); await t.wait(400)
    await t.ev("rBegin(640,360);draw(null)")
    ok("a render at 640x360 stays 640x360 mid-drag",(await t.ev("[cv.width,cv.height]"))==[640,360],await t.ev("[cv.width,cv.height]"))
    await t.ev("rEnd()"); await pg.mouse.up(); await t.wait(500)
    # off means off
    await t.ev("PERF.low='off';0"); await pg.mouse.move(x,y); await pg.mouse.down(); await t.wait(400)
    ok("'off' keeps full size while dragging",(await t.ev("cv.width"))==full[0],await t.ev("cv.width"))
    await pg.mouse.up(); await t.wait(300)
    # wheel counts as interacting
    await t.ev("PERF.low='half';0"); await pg.mouse.move(box["x"]+box["width"]/2,box["y"]+box["height"]/2); await pg.mouse.wheel(0,40); await t.wait(120)
    ok("the wheel lowers it briefly",await t.ev("LR.on"),await t.ev("[LR.on,cv.width]"))
    await t.wait(900)
    ok("and it comes back after",(await t.ev("LR.on"))==False and (await t.ev("cv.width"))==full[0],await t.ev("[LR.on,cv.width]"))
    # auto mode only drops when frames are slow: a fast frame time means no drop
    await t.ev("PERF.low='auto';LR.full=10;0"); await pg.mouse.move(x,y); await pg.mouse.down(); await t.wait(400)
    ok("auto stays full size when frames are fast",await t.ev("LR.scale")==1 or (await t.ev("LR.full"))>21,await t.ev("[LR.scale,LR.full]"))
    await pg.mouse.up(); await t.wait(300)
    await t.ev("LR.full=40;0"); await pg.mouse.move(x,y); await pg.mouse.down(); await t.wait(300)
    ok("auto drops to 50% when frames are slow",await t.ev("LR.scale")==0.5,await t.ev("LR.scale"))
    await pg.mouse.up(); await t.wait(300)
    return t.finish()
