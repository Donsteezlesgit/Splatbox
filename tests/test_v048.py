"""V048: quiet corner messages, gizmo cycle (T), save indicator, folder warning, undo instead of confirm, remembered panels, / search, slider reset, number maths, accessibility options."""
import json
from harness import *
async def msgs(br,site,fx):
    t=await open_page(br,site,"v048msgs",w=1300,h=800); ok=t.ok
    await t.new_project(); await t.add_ply(fx["tilt"])
    await t.ev("setStatus('Short one','ok');0"); await t.wait(300)
    b=json.loads(await t.ev("var r=$('toast').getBoundingClientRect(),v=$('gl').getBoundingClientRect();JSON.stringify({l:r.left-v.left,b:v.bottom-r.bottom,w:r.width})"))
    ok("the message sits small in the bottom-left corner",b["l"]<40 and b["b"]<120 and b["w"]<=345,b)
    await t.wait(3500)
    ok("a short message is gone after about 3 s",(await t.ev("$('toast').hidden"))==True)
    await t.ev("setStatus('Bad thing','bad');0"); await t.wait(3500)
    ok("an error is still there at 3.5 s",(await t.ev("$('toast').hidden"))==False)
    await t.wait(3200)
    ok("an error is gone by about 6.5 s",(await t.ev("$('toast').hidden"))==True)
    await t.ev("setStatus('Click me','ok');0"); await t.pg.click("#toast"); await t.wait(100)
    ok("clicking a message dismisses it",(await t.ev("$('toast').hidden"))==True)
    await t.ev("busy(true,'Working…');setStatus('Hello','ok');0"); await t.wait(200)
    g=json.loads(await t.ev("var a=$('busyT').getBoundingClientRect(),b=$('toast').getBoundingClientRect();JSON.stringify({busyTop:a.top,toastBottom:b.bottom})"))
    ok("the Working spinner and a message do not overlap",g["toastBottom"]<=g["busyTop"]+1,g)
    await t.ev("busy(false);0")
    return t.finish()
