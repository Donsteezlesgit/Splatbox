"""Overlapping splat objects must sort like one merged object."""
from harness import *
async def run(br,site,fx):
    t=await open_page(br,site,"overlap",w=760,h=480)
    await t.new_project(); await t.add_ply(fx["planeA"],1300); await t.add_ply(fx["planeB"],1300)
    await t.ev("OBJS.forEach(o=>o.pos=[0,0,0]);closeTool();persistObjs();dirty=true")
    angles=[(0.5,0.4),(2.4,0.5)]
    async def shots(old=False):
        out=[]
        if old: await t.ev("window.__so=splatsOverlap;splatsOverlap=function(){return false};0")
        for yw,pt in angles:
            await t.ev(f"Rm=[1,0,0,0,1,0,0,0,1];TG=[0,0,0];zoom=0.7;rawTurnTo({yw},{pt});OBJS.forEach(o=>{{if(o.gs)o.gs.lastV=null}});dirty=true"); await t.wait(500)
            await t.ev("OBJS.forEach(o=>{if(o.gs)o.gs.lastV=null});dirty=true"); await t.wait(450)
            out.append(await t.pg.evaluate(SNAP))
        if old: await t.ev("splatsOverlap=window.__so;0")
        return out
    new=await shots(); old=await shots(True)
    await t.ev("goHome()"); await t.wait(900); await t.new_project(); await t.add_ply(fx["planeAB"],1500); await t.ev("closeTool();dirty=true")
    mer=await shots()
    for i in range(len(angles)):
        n,o=dif(new[i],mer[i]),dif(old[i],mer[i])
        t.ok(f"angle {i}: overlapping objects match the merged picture better than whole-object sorting",o>1000 and n<o*0.5,[n,o])
    return t.finish()
