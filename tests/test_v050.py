"""V050: four rail pages (Add, Look, Scene, File), one page per kind of object, and clear open/close/selection rules."""
import json
from harness import *

async def S(t):
    return json.loads(await t.ev("JSON.stringify({g:curGroup,t:curTool,sel:SEL?SEL.id:null,kind:SEL?SEL.kind:null,open:!$('pop').hidden,title:$('popT').textContent})"))

async def setup(t,fx):
    await t.new_project(); await t.add_ply(fx["tilt"]); await t.add_ply(fx["tilt"])
    await t.ev("addLight('sun');addCamera();leaveThru();SEL=null;closeTool();dirty=true"); await t.wait(400)

async def pages(br,site,fx):
    t=await open_page(br,site,"v050pages",w=1440,h=900); ok=t.ok; pg=t.pg
    await setup(t,fx)
    ok("four pages on the rail: Add, Look, Scene, File",(await t.ev("[].map.call(rail.children,function(b){return b.dataset.tool}).join()"))=="add,look,scene,file")
    # --- clicking an object opens the page for its kind, from any page (the old bug)
    rows=await t.ev("OBJS.map(function(o){return o.kind})"); ok("scene has two splats, a light and a camera",rows==["splat","splat","sun","camera"],rows)
    for start in ["add","look","scene","file"]:
        for i,(want,kind) in enumerate([("o-splat","splat"),("o-splat","splat"),("o-light","sun"),("o-camera","camera")]):
            await t.ev(f"openTool('{start}')"); await t.wait(80)
            await pg.click(f'#outlB .orw >> nth={i}'); await t.wait(150)
            s=await S(t)
            ok(f"from {start}: clicking the {kind} row opens its page",s["g"]==want and s["kind"]==kind and s["open"],s)
    s=await S(t); ok("the page title names the object",s["title"].startswith("Camera: "),s["title"])
    # --- the splat page has the splat sections, the camera page the camera's own, nothing else mixed in
    await pg.click('#outlB .orw >> nth=0'); await t.wait(150)
    secs=await t.ev("[].map.call(document.querySelectorAll('#popB .sechb'),function(b){return b.dataset.sec}).join()")
    ok("splat page: Transform, Object look, Crop, Select, Orient",secs=="objects,ofx,crop,select,orient",secs)
    await pg.click('#outlB .orw >> nth=3'); await t.wait(150)
    secs=await t.ev("[].map.call(document.querySelectorAll('#popB .sechb'),function(b){return b.dataset.sec}).join()")
    ok("camera page: Camera, Depth of field",secs=="camobj,dof",secs)
    txt=await t.ev("$('popB').innerText")
    ok("camera page has its own lens and focus distance",("Camera lens" in txt) and ("Focus distance" in txt),txt[:200])
    ok("camera page has no free-view or mouse-speed settings",("Mouse speed" not in txt) and ("Free view" not in txt))
    await pg.click('#outlB .orw >> nth=2'); await t.wait(150)
    txt=await t.ev("$('popB').innerText")
    ok("light page has no scene-wide light sliders",("Ambient light" not in txt) and ("Light the splats" not in txt) and ("Intensity" in txt),txt[:200])
    ok("a one-section page has no fold-out header",(await t.ev("document.querySelectorAll('#popB .sechb').length"))==0)
    # --- the four rail pages
    async def sections(page):
        await t.ev(f"openTool('{page}')"); await t.wait(100)
        return await t.ev("[].map.call(document.querySelectorAll('#popB .sechb'),function(b){return b.dataset.sec}).join()")
    ok("Add: Bring in, Lights, Camera",(await sections("add"))=="add,addlight,addcam")
    ok("Look: Colour, Look, Lens, Depth and effects (no depth of field)",(await sections("look"))=="colour,looks,lens,fx")
    ok("Scene: Light the splats, Display, Free view, Grids and axes",(await sections("scene"))=="lighting,display,freeview,helpers")
    ok("File: File, Capture, History",(await sections("file"))=="file,capture,hist")
    await t.ev("openTool('add')"); await pg.click("[data-sec=addlight]"); await t.wait(150)
    ok("Add page has the three light buttons",(await pg.locator("#popB [data-act=oAddSun], #popB [data-act=oAddPoint], #popB [data-act=oAddSpot]").count())==3)
    await pg.click("[data-sec=addcam]"); await t.wait(150)
    ok("Add page has Add camera here",(await pg.locator("#popB [data-act=camAdd]").count())==1)
    await t.ev("openTool('scene');openTool('helpers')"); await t.wait(100)
    ok("Scene page has the grids and axes",(await pg.locator("#popB [data-k=gridY]").count())==1 and (await pg.locator("#popB [data-k=axes]").count())==1)
    await t.ev("openTool('freeview')"); await t.wait(100)
    ok("Scene page has the free view settings",(await pg.locator("#popB [data-k=sens]").count())==1)
    # --- adding from the Add page opens the new object's page
    await t.ev("SEL=null;openTool('add')"); await pg.click("[data-sec=addlight]"); await t.wait(100)
    await pg.click("[data-act=oAddPoint]"); await t.wait(300)
    s=await S(t); ok("adding a point light opens the light page",s["g"]=="o-light" and s["kind"]=="point",s)
    await t.ev("SEL=null;openTool('add')"); await pg.click("[data-sec=addcam]"); await t.wait(100)
    await pg.click("[data-act=camAdd]"); await t.wait(300)
    s=await S(t); ok("adding a camera opens the camera page",s["g"]=="o-camera" and s["kind"]=="camera",s)
    ok("no console or page errors",len(t.errs)==0,t.errs[:3])
    return t.finish()

async def rules(br,site,fx):
    t=await open_page(br,site,"v050rules",w=1440,h=900); ok=t.ok; pg=t.pg
    await setup(t,fx)
    # --- opening or closing a page never changes what is selected
    await t.ev("SEL=OBJS.filter(isLight)[0];dirty=true"); sid=await t.ev("SEL.id")
    for page in ["add","look","scene","file"]:
        await pg.click(f"#rail .tool[data-tool={page}]"); await t.wait(80)
        ok(f"opening {page} keeps the light selected",(await S(t))["sel"]==sid)
    for k in ["Digit1","Digit2","Digit3","Digit4","Digit4","Digit1","Digit1"]:
        await pg.keyboard.press(k); await t.wait(60)
        if (await S(t))["sel"]!=sid: ok("number keys never change the selection",False,k); break
    else: ok("number keys never change the selection",True)
    await t.ev("openTool('look')"); await pg.click("#popX"); await t.wait(80)
    ok("closing with X keeps the selection",(await S(t))["sel"]==sid)
    await t.ev("openTool('scene')"); await t.ev("closeTool()")
    ok("closeTool keeps the selection",(await S(t))["sel"]==sid)
    # none-selected stays none-selected when a page opens (it used to pick the only light or camera)
    await t.ev("SEL=null;closeTool();dirty=true"); await t.ev("openTool('scene')"); await t.wait(80)
    ok("opening a page with nothing selected picks nothing",(await S(t))["sel"] is None)
    ok("opening an object page with the wrong or no object does nothing",(await t.ev("openTool('crop')"))==False and (await t.ev("openTool('camobj')"))==False)
    # --- closing: X, the active rail icon, the same number key
    await t.ev("openTool('look')"); await t.wait(80)
    await pg.click("#popX"); await t.wait(100); s=await S(t)
    ok("X closes the page (and it stays closed)",s["g"] is None and not s["open"],s)
    ok("with the page closed the Objects window fills the dock",await pg.is_visible("#outl") and not await pg.is_visible("#pop"))
    await pg.click("#rail .tool[data-tool=file]"); await t.wait(100)
    await pg.click("#rail .tool[data-tool=file]"); await t.wait(100); s=await S(t)
    ok("clicking the active rail icon closes its page",s["g"] is None and not s["open"],s)
    await pg.keyboard.press("Digit3"); await t.wait(100); ok("3 opens Scene",(await S(t))["g"]=="scene")
    await pg.keyboard.press("Digit3"); await t.wait(100); ok("3 again closes it",(await S(t))["g"] is None)
    await pg.keyboard.press("Digit5"); await t.wait(100); ok("there is no page 5",(await S(t))["g"] is None)
    # --- Escape: deselect first, then close
    await t.ev("openTool('look')"); await pg.click('#outlB .orw >> nth=0'); await t.wait(120)
    await pg.click("#rail .tool[data-tool=look]"); await t.wait(100)
    s=await S(t); ok("a rail page open with a splat selected",s["g"]=="look" and s["kind"]=="splat",s)
    await pg.keyboard.press("Escape"); await t.wait(100); s=await S(t)
    ok("Escape deselects first and leaves the page open",s["sel"] is None and s["g"]=="look",s)
    await pg.keyboard.press("Escape"); await t.wait(100); s=await S(t)
    ok("a second Escape closes the page",s["g"] is None,s)
    await pg.click('#outlB .orw >> nth=0'); await t.wait(120)
    await pg.keyboard.press("Escape"); await t.wait(100); s=await S(t)
    ok("Escape on an object page deselects and closes it",s["sel"] is None and s["g"] is None,s)
    # --- empty space in the view deselects (and closes the object page)
    await pg.click('#outlB .orw >> nth=0'); await t.wait(120)
    r=await t.ev("(function(){var rr=cv.getBoundingClientRect();return tapObj({clientX:rr.left+4,clientY:rr.top+4})})()")
    s=await S(t); ok("tapping empty space deselects",r is True and s["sel"] is None and s["g"] is None,[r,s])
    await t.ev("openTool('look')")
    r=await t.ev("(function(){var rr=cv.getBoundingClientRect();return tapObj({clientX:rr.left+4,clientY:rr.top+4})})()")
    ok("tapping empty space with nothing selected leaves a rail page alone on a wide screen",(await S(t))["g"]=="look")
    # --- deleting the selected object closes its page
    await pg.click('#outlB .orw >> nth=3'); await t.wait(150)
    s=await S(t); ok("camera page open",s["g"]=="o-camera",s)
    await t.ev("removeObj(SEL)"); await t.wait(250); s=await S(t)
    ok("deleting the object closes its page",s["sel"] is None and s["g"] is None,s)
    # --- going back to a kind starts on its first section; clicking another of the same kind keeps the section
    await pg.click('#outlB .orw >> nth=0'); await t.wait(120); await t.ev("openTool('crop',true)"); await t.wait(100)
    await pg.click('#outlB .orw >> nth=1'); await t.wait(150)
    ok("another splat keeps the section you were on",(await S(t))["t"]=="crop")
    await pg.click('#outlB .orw >> nth=2'); await t.wait(150); await pg.click('#outlB .orw >> nth=0'); await t.wait(150)
    ok("coming back from another kind starts on Transform",(await S(t))["t"]=="objects")
    ok("no console or page errors",len(t.errs)==0,t.errs[:3])
    return t.finish()

async def remember(br,site,fx):
    t=await open_page(br,site,"v050mem",w=1440,h=900); ok=t.ok; pg=t.pg
    await setup(t,fx)
    s=json.loads(await t.ev("localStorage.getItem('sb.ui')||'{}'"))
    await t.ev("openTool('scene')"); await t.ev("openTool('freeview')")
    u=json.loads(await t.ev("localStorage.getItem('sb.ui')"))
    ok("the open page and section are remembered",u.get("g")=="scene" and u.get("ls",{}).get("scene")=="freeview",u)
    await pg.click('#outlB .orw >> nth=3'); await t.wait(150)
    u=json.loads(await t.ev("localStorage.getItem('sb.ui')"))
    ok("an object page is not remembered as the open page (the last rail page is)",u.get("g")=="scene",u)
    await t.ev("closeTool()")
    u=json.loads(await t.ev("localStorage.getItem('sb.ui')"))
    ok("closed is remembered as closed",u.get("g") is None,u)
    await t.ev("saveNow()"); await t.wait(700)
    await pg.reload(); await t.wait(1800)
    await pg.click("#grid .card:not(.new) >> nth=0"); await t.wait(2800)
    ok("reopening the project keeps it closed",(await S(t))["g"] is None,await S(t))
    await t.ev("openTool('look')"); await t.ev("saveNow()"); await t.wait(500)
    await pg.reload(); await t.wait(1800)
    await pg.click("#grid .card:not(.new) >> nth=0"); await t.wait(2800)
    ok("reopening the project opens the page you left",(await S(t))["g"]=="look",await S(t))
    await t.ev("localStorage.removeItem('sb.ui');0")
    await pg.reload(); await t.wait(1800)
    await pg.click("#grid .card:not(.new) >> nth=0"); await t.wait(2800)
    ok("with nothing remembered, Scene opens",(await S(t))["g"]=="scene",await S(t))
    return t.finish()

async def phone(br,site,fx):
    t=await open_page(br,site,"v050phone",w=390,h=844); ok=t.ok; pg=t.pg
    await setup(t,fx)
    await t.ev("SEL=OBJS[0];showObjPage();0"); await t.wait(150)
    ok("on a phone, picking a splat does not pop the sheet open by itself",not (await S(t))["open"])
    await pg.click("#rail .tool[data-tool=look]"); await t.wait(150)
    ok("a rail tab opens the sheet",(await S(t))["g"]=="look")
    await t.ev("SEL=OBJS[0];showObjPage();0"); await t.wait(150)
    ok("with the sheet open, picking a splat shows its page",(await S(t))["g"]=="o-splat")
    r=await t.ev("(function(){var rr=cv.getBoundingClientRect();return tapObj({clientX:rr.left+3,clientY:rr.top+3})})()"); await t.wait(100)
    ok("tapping empty space deselects",(await S(t))["sel"] is None)
    ok("no console or page errors",len(t.errs)==0,t.errs[:3])
    return t.finish()
