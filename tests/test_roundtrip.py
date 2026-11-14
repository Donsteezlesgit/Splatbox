"""The guard against 'a new feature is missed by Save'.
Every setting, object kind and piece of state must survive save -> reopen. If you add one and forget to save it,
or forget to list it here, this test fails."""
import json
from harness import *
# one non-default value for EVERY setting in DEF. A new setting that is not listed here fails the test on purpose.
PERTURB={"dofNear":0.7,"dofFar":0.6,"dofSoft":0.2,"dofTilt":0.5,"dofTiltA":20,"dofTiltP":0.3,"dofTiltB":0.4,"dofVis":True,"fast":True,"grainSoft":0.8,"grainCol":0.6,"grainRate":3,"fxDis":0.3,"fxScat":0.2,"fxPulse":0.4,"fxPhase":0.6,"range":1.2,"smooth":2,"cut":0.3,"invert":True,"fill":0.5,"size":1.5,"detail":384,"shape":1,"bg":"#123456",
 "exp":10,"con":11,"sat":12,"hue":13,"warm":14,"fog":0.4,"defocus":0.3,"focus":0.7,"sliceA":0.1,"sliceB":0.9,
 "cam":"sway","dur":9,"loop":True,"turn":1,"render":"solid","ctrl":"orbit","ctrlV":16,"fov":65,"sens":1.7,"tiltX":3,"tiltZ":4,"spin":5,"flip":True,
 "vig":0.3,"vigSoft":0.5,"vigBlur":0.2,"dist":9,"ca":0.1,"grain":0.2,"grainSize":2,"look":"cube","lookMix":0.6,"focusRange":0.2,
 "gridY":True,"gridX":True,"gridZ":True,"axes":True,"lit":0.4,"amb":0.3,"bakeGrade":True,"rsize":"1080","rfps":60,"ralpha":True,"rfmt":"mp4","tdrgb":False,"tdply":False}
LUT="LUT_3D_SIZE 2\n"+"\n".join(f"{r} {g} {b}" for b in (0,1) for g in (0,1) for r in (0,1))+"\n"
RUNTIME={"gs","mesh","main"}
def diff(a,b,p=None):
    if p is None: a,b,p=json.loads(a),json.loads(b),""
    out=[]
    if isinstance(a,dict) and isinstance(b,dict):
        for k in sorted(set(a)|set(b)): out+=diff(a.get(k),b.get(k),p+"."+k)
    elif isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
        for i,(x,y) in enumerate(zip(a,b)): out+=diff(x,y,f"{p}[{i}]")
    elif a!=b: out.append(f"{p}: {str(a)[:70]} != {str(b)[:70]}")
    return out
async def waitthru(t,want):
    for _ in range(60):
        try:
            if await t.ev("THRU&&ACAM&&ACAM.id")==want: return
        except Exception: pass
        await t.wait(500)
async def run(br,site,fx):
    t=await open_page(br,site,"roundtrip")
    defs=json.loads(await t.ev("JSON.stringify(DEF)"))
    missing=[k for k in defs if k not in PERTURB]
    t.ok("every setting is covered by this test (add new ones to PERTURB)",not missing,missing)
    kinds=json.loads(await t.ev("JSON.stringify(OBJ_KINDS)"))
    await t.new_project()
    await t.add_ply(fx["tilt"]); await t.add_ply(fx["blob"]); await t.add_mesh(fx["cube"])
    await t.ev("closeTool()")
    await t.ev("addLight('sun');addLight('point');addLight('spot')")
    await t.ev("addCamera();addCamera()")
    await t.ev("OBJS.filter(o=>o.kind==='splat')[1].pos=[1.2,0.3,0.1];OBJS.filter(o=>o.kind==='splat')[1].scl=0.8;OBJS[0].crop={on:true,inv:false,x0:0.1,x1:0.9,y0:0,y1:1,z0:0,z1:1}")
    await t.ev("cur.lut="+json.dumps(LUT)+";cur.lutName='Test LUT'")
    pert={k:v for k,v in PERTURB.items() if k in defs}
    await t.ev("Object.assign(S,"+json.dumps(pert)+");PF.lutKey='';applyLook();dirty=true")
    await t.ev("rawTurnTo(0.8,0.25);TG=[0.3,0.1,-0.4];zoom=0.7;dirty=true;persistObjs()")
    await t.ev("enterThru(cams()[1])")
    have=set(json.loads(await t.ev("JSON.stringify(OBJS.map(o=>o.kind))")))
    t.ok("test scene contains every object kind",set(kinds)<=have,sorted(set(kinds)-have))
    snapA=await t.ev("snapshotState()")
    want=await t.ev("ACAM.id")
    await t.pg.click("#saveBtn"); await t.wait(1500)
    # 1. reopen straight from storage
    await t.ev("dbAll().then(function(l){return openSpace(l.find(function(x){return x.id===cur.id}))})"); await waitthru(t,want); await t.wait(500)
    snapB=await t.ev("snapshotState()")
    t.ok("reopen from storage: everything identical",not diff(snapA,snapB),diff(snapA,snapB))
    # 2. every live object field is in the stored record
    rec=json.loads(await t.ev("JSON.stringify(cur.objs.map(function(o){return Object.keys(o)}))"))
    live=json.loads(await t.ev("JSON.stringify(OBJS.map(function(o){return {k:o.kind,keys:Object.keys(o)}}))"))
    lost=[]
    for i,o in enumerate(live):
        for k in o["keys"]:
            if k not in RUNTIME and k not in rec[i]: lost.append(f"{o['k']}.{k}")
    t.ok("no object field is missing from the saved record",not lost,sorted(set(lost)))
    t.ok("saved record carries a format number",(await t.ev("cur.v"))==(await t.ev("FORMAT")))
    # 3. the real way: full page reload, then open from the project list
    name=await t.ev("cur.name")
    await t.pg.reload(); await t.wait(1200)
    await t.pg.click(f"#grid .card:has-text('{name}')"); await waitthru(t,want); await t.wait(500)
    snapC=await t.ev("snapshotState()")
    t.ok("after a full page reload and opening from the list: identical",not diff(snapA,snapC),diff(snapA,snapC))
    t.ok("opens in the workspace with the same camera",(await t.ev("MODE"))=="edit" and (await t.ev("THRU"))==True)
    # 4. a project from a newer app version is refused, not opened
    await t.ev("goHome()"); await t.wait(1500)
    await t.pg.evaluate("""async()=>{const db=await new Promise(r=>{const q=indexedDB.open('splatbox');q.onsuccess=()=>r(q.result)});
      const tx=db.transaction('projects','readwrite');tx.objectStore('projects').put({id:'future',v:99,name:'From the future',kind:'space',created:1,updated:Date.now()+5,settings:{},objs:[]});
      await new Promise(r=>tx.oncomplete=r)}""")
    await t.pg.reload(); await t.wait(1000)
    await t.pg.click("#grid .card:has-text('From the future')"); await t.wait(1200)
    t.ok("a project from a newer version is refused",not await t.pg.is_visible("#editor"))
    t.errs=[e for e in t.errs if "newer" not in e]
    return t.finish()
