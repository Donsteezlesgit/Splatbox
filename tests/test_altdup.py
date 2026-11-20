"""V060: Alt + drag duplicates, in the viewport (gizmo handle) and in the Objects list."""
import json
from harness import *
async def run(br,site,fx):
    t=await open_page(br,site,"altdup",w=1440,h=900); ok=t.ok; pg=t.pg
    await t.new_project(); await t.add_ply(fx["tilt"],1800)
    await t.ev("addLight('point');SEL=OBJS.filter(function(o){return o.kind==='splat'})[0];closeTool();dirty=true;0"); await t.wait(600)
    n0=await t.ev("OBJS.length"); sid=await t.ev("SEL.id"); p0=await t.ev("JSON.stringify(SEL.pos)")
    # ---- viewport: Alt + drag a move handle
    h=await t.ev("(function(){var g=gzGeo(),r=cv.getBoundingClientRect(),e=g.ends[0];return [r.left+g.c[0]+(e[0]-g.c[0])*0.7,r.top+g.c[1]+(e[1]-g.c[1])*0.7]})()")
    ok("the move handle is under the pointer",await t.ev(f"!!gizmoHit({h[0]},{h[1]})"),h)
    await pg.mouse.move(h[0],h[1]); await pg.keyboard.down("Alt"); await pg.mouse.down(); await t.wait(1500)
    await pg.mouse.move(h[0]+25,h[1]+3,steps=4); await pg.mouse.move(h[0]+70,h[1]+8,steps=6); await pg.mouse.up(); await pg.keyboard.up("Alt"); await t.wait(500)
    ok("Alt + drag on the gizmo adds one object",await t.ev("OBJS.length")==n0+1,[n0,await t.ev("OBJS.length")])
    ok("the original stayed where it was",await t.ev(f"JSON.stringify(findObj('{sid}').pos)")==p0)
    ok("the copy is selected and was moved",await t.ev(f"SEL.id!=='{sid}'&&SEL.name.indexOf('copy')>0&&JSON.stringify(SEL.pos)!==JSON.stringify(findObj('{sid}').pos)"))
    ok("the copy sits right after the original in the list",await t.ev(f"OBJS.map(function(o){{return o.id}}).indexOf(SEL.id)==OBJS.map(function(o){{return o.id}}).indexOf('{sid}')+1"))
    await t.ev("document.activeElement&&document.activeElement.blur();0"); await pg.keyboard.press("Control+z"); await t.wait(900)
    await pg.keyboard.press("Control+z"); await t.wait(900)
    ok("undo removes the copy again",await t.ev("OBJS.length")==n0,await t.ev("OBJS.length"))
    # ---- a plain drag on the gizmo still only moves
    await t.ev(f"SEL=findObj('{sid}');dirty=true;0"); await t.wait(300)
    h=await t.ev("(function(){var g=gzGeo(),r=cv.getBoundingClientRect(),e=g.ends[0];return [r.left+g.c[0]+(e[0]-g.c[0])*0.7,r.top+g.c[1]+(e[1]-g.c[1])*0.7]})()")
    await pg.mouse.move(h[0],h[1]); await pg.mouse.down(); await pg.mouse.move(h[0]+40,h[1]+4,steps=5); await pg.mouse.up(); await t.wait(400)
    ok("a plain gizmo drag adds nothing",await t.ev("OBJS.length")==n0)
    # ---- Objects list: Alt + drag a row
    async def drag(src,dst,alt):
        await t.ev("(function(){var rows=document.querySelectorAll('#outlB .orw'),a=rows[%d],b=rows[%d],dt=new DataTransfer();"
                   "a.dispatchEvent(new DragEvent('dragstart',{bubbles:true,altKey:%s,dataTransfer:dt}));"
                   "b.dispatchEvent(new DragEvent('dragover',{bubbles:true,cancelable:true,altKey:%s,dataTransfer:dt}));"
                   "b.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,altKey:%s,dataTransfer:dt}));"
                   "a.dispatchEvent(new DragEvent('dragend',{bubbles:true,dataTransfer:dt}))})()"%(src,dst,*(["true" if alt else "false"]*3)))
        await t.wait(1800)
    await t.ev("renderOutl(true);0"); await t.wait(300)
    names0=await t.ev("OBJS.map(function(o){return o.kind}).join()")
    await drag(0,1,False)
    ok("a plain row drag only reorders",await t.ev("OBJS.length")==n0)
    await t.ev("renderOutl(true);0"); await t.wait(300)
    await drag(0,1,True)
    ok("Alt + drag a row adds a copy",await t.ev("OBJS.length")==n0+1,[n0,await t.ev("OBJS.length")])
    ok("the copy is a splat with its own name",await t.ev("OBJS.filter(function(o){return o.kind==='splat'}).length")==2 and await t.ev("OBJS.some(function(o){return o.name.indexOf(' copy')>0})"))
    ok("the original is still there",await t.ev(f"!!findObj('{sid}')"))
    # ---- lights and cameras copy too
    await t.ev("addCamera();0"); await t.wait(300)
    nl=await t.ev("OBJS.length"); lid=await t.ev("OBJS.filter(function(o){return o.kind==='point'})[0].id")
    await t.ev(f"dupObj(findObj('{lid}'))"); await t.wait(600)
    ok("a light can be duplicated",await t.ev("OBJS.filter(function(o){return o.kind==='point'}).length")==2)
    cid=await t.ev("OBJS.filter(function(o){return o.kind==='camera'})[0].id")
    await t.ev(f"dupObj(findObj('{cid}'))"); await t.wait(600)
    ok("a camera can be duplicated",await t.ev("OBJS.filter(function(o){return o.kind==='camera'}).length")==2)
    ok("no console or page errors",len(t.errs)==0,t.errs[:3])
    return t.finish()
