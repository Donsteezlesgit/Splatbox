"""Smoke test of the main flow + lens effects + old-project migration. Fails on any console error or GL error."""
import json
from harness import *
EFFECTS=[("none",""),("vig","S.vig=0.6"),("vigBlur","S.vigBlur=0.5"),("dist","S.dist=25"),("ca","S.ca=0.3"),("grain","S.grain=0.3"),("look","S.look='velvia';S.lookMix=1;applyLook()"),
         ("fog","S.fog=0.8"),("defocus","S.defocus=0.7"),("slice","S.sliceA=0.3"),("solid","S.render='solid'"),("points","S.render='points'"),("depth","S.render='depth'"),("lit","S.render='splat';S.lit=0.6")]
LUMA="""(()=>{const c=document.getElementById('gl'),x=document.createElement('canvas');x.width=c.width;x.height=c.height;const g=x.getContext('2d');g.drawImage(c,0,0);const d=g.getImageData(0,0,x.width,x.height).data;let s=0,n=0;for(let i=0;i<d.length;i+=16){s+=(d[i]+d[i+1]+d[i+2])/3;n++}return s/n})()"""
async def run(br,site,fx):
    t=await open_page(br,site,"core",w=1100,h=700)
    ok=t.ok
    ok("home offers a new project",await t.pg.locator("#grid .card.new").count()>=1)
    await t.new_project()
    ok("opens in Edit with an empty space",(await t.ev("MODE"))=="edit" and (await t.ev("scene.n"))==0)
    await t.add_ply(fx["tilt"]); await t.add_ply(fx["blob"]); await t.add_mesh(fx["cube"]); await t.ev("closeTool()")
    ok("splats and a model were added",(await t.ev("OBJS.map(o=>o.kind).join()"))=="splat,splat,mesh")
    await t.ev("addLight('sun')"); await t.ev("setMode('render')"); await t.ev("closeTool();draw(null)"); await t.wait(500)
    base=await t.pg.evaluate(LUMA); ok("the scene is not blank",base>3,base)
    for name,code in EFFECTS[1:]:
        await t.ev("Object.assign(S,JSON.parse(JSON.stringify(DEF)));S.ctrl='fly';S.fov=50;PF.lutKey='';applyLook();"+code+";dirty=true;draw(null)"); await t.wait(250)
        err=await t.ev("gl.getError()"); lum=await t.pg.evaluate(LUMA)
        ok(f"effect '{name}' draws, no GL error",err==0 and lum>0.5,[err,round(lum,1)])
    await t.ev("Object.assign(S,JSON.parse(JSON.stringify(DEF)));applyLook()")
    # old-format projects open as spaces
    await t.ev("goHome()"); await t.wait(1500)
    await t.pg.evaluate("""async()=>{const s=window.__ev('makeSample()');const tb=c=>new Promise(r=>c.toBlob(r,'image/png'));
      const photo=await tb(s.photo),depth=await tb(s.depth);
      const db=await new Promise(r=>{const q=indexedDB.open('splatbox');q.onsuccess=()=>r(q.result)});
      const tx=db.transaction('projects','readwrite'),st=tx.objectStore('projects'),now=Date.now();
      st.put({id:'legacyDepth',name:'Old depth photo',created:now,updated:now+10,photo,thumb:photo,depth,settings:{detail:384}});
      await new Promise(r=>tx.oncomplete=r)}""")
    await t.pg.reload(); await t.wait(900)
    await t.pg.click("#grid .card:has-text('Old depth photo')"); await t.wait(3500)
    ok("an old depth-photo project becomes a space with an object",(await t.ev("cur.kind"))=="space" and (await t.ev("OBJS.length"))>=1)
    ok("and gets the current format number",(await t.ev("cur.v"))==(await t.ev("FORMAT")))
    return t.finish()
