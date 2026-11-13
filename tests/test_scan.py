"""V034: photo-scan helpers - quality levels, blurry-photo filter, floater cleanup."""
import json, os, tempfile
import numpy as np
from PIL import Image, ImageFilter
from harness import *
PLY="""window.__plyF=function(pts){var names=['x','y','z','f_dc_0','f_dc_1','f_dc_2','opacity','scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3'],n=pts.length/3;
 var head=new TextEncoder().encode('ply\\nformat binary_little_endian 1.0\\nelement vertex '+n+'\\n'+names.map(function(p){return 'property float '+p}).join('\\n')+'\\nend_header\\n'),f=new Float32Array(n*14),i;
 for(i=0;i<n;i++){var b=i*14;f[b]=pts[i*3];f[b+1]=pts[i*3+1];f[b+2]=pts[i*3+2];f[b+3]=0.5;f[b+4]=0.5;f[b+5]=0.5;f[b+6]=3;f[b+7]=f[b+8]=f[b+9]=-5;f[b+10]=1}
 var u=new Uint8Array(head.length+f.byteLength);u.set(head,0);u.set(new Uint8Array(f.buffer),head.length);return new File([u],'cl.ply')}"""
async def run(br,site,fx):
    t=await open_page(br,site,"scan",w=1000,h=640); ok=t.ok
    await t.pg.evaluate(PLY+";0")
    await t.new_project()
    # --- quality levels
    ok("there are five quality levels, Balanced still the middle one",await t.ev("Object.keys(QUAL).join(',')")=="draft,fast,balanced,high,ultra")
    ok("each level is bigger than the one before",await t.ev("(function(){var k=Object.keys(QUAL),ok=true;for(var i=1;i<k.length;i++)if(QUAL[k[i]].iters<=QUAL[k[i-1]].iters||QUAL[k[i]].max<=QUAL[k[i-1]].max)ok=false;return ok})()"))
    ok("every level explains itself",await t.ev("Object.keys(QUAL).every(function(k){return qualNote(k).indexOf(QUAL[k].n)===0})"))
    # --- picking sharp photos
    ok("blurry photos are dropped",json.loads(await t.ev("JSON.stringify(pickSharp([100,95,110,5,102,98,99,101,97,6,103,100]))"))["dropped"]==[3,9])
    ok("a fully sharp set loses nothing",json.loads(await t.ev("JSON.stringify(pickSharp([100,95,110,102,98,99,101,97,103,100]))"))["dropped"]==[])
    ok("a small set is never cut below 8",json.loads(await t.ev("JSON.stringify(pickSharp([100,100,100,100,100,100,100,2,2]))"))["keep"].__len__()>=8)
    d=json.loads(await t.ev("JSON.stringify(pickSharp([100,100,100,100,100,100,100,100,100,100,100,100,1,1,1,1,1,1]))"))
    ok("it never drops more than 30% of a set",len(d["dropped"])<=5 and len(d["keep"])>=13,d)
    ok("the worst photos go first when it has to limit itself",all(i>=12 for i in d["dropped"]),d)
    # --- real images through the score
    tmp=tempfile.mkdtemp(); rng=np.random.default_rng(1); paths=[]
    for i in range(12):
        a=(rng.random((120,160,3))*255).astype("uint8"); im=Image.fromarray(a).resize((640,480),Image.NEAREST)
        if i in (4,9): im=im.filter(ImageFilter.GaussianBlur(14))
        p=os.path.join(tmp,f"p{i:02d}.jpg"); im.save(p,quality=92); paths.append(p)
    await t.pg.set_input_files("#multiIn",paths); await t.wait(6000)
    r=json.loads(await t.ev("JSON.stringify({d:TR&&TR.p.dropped,n:TR&&TR.p.srcs.length})"))
    ok("the scan intake left out the two blurred photos",r["d"]==[4,9] and r["n"]==10,r)
    await t.ev("trTeardown();backToEditor()")
    # --- floater cleanup
    await t.ev("goHome()"); await t.wait(900); await t.new_project()
    await t.ev("""(function(){var pts=[],i,r=function(){return Math.random()-0.5};for(i=0;i<4000;i++)pts.push(r()*0.3,r()*0.3,r()*0.3);
      for(i=0;i<30;i++)pts.push(0.4+i*0.01,r()*0.6,r()*0.6);window.__cnt=pts.length/3;return addPlyFile(window.__plyF(pts))})()"""); await t.wait(1500)
    o=json.loads(await t.ev("(function(){var o=OBJS[OBJS.length-1],k=autoFloaters(o),core=0,fl=0,i;for(i=0;i<o.gs.n;i++){if(o.gs.mask&&o.gs.mask[i]){if(i<4000)core++;else fl++}}return JSON.stringify({k:k,core:core,fl:fl,n:o.gs.n})})()"))
    ok("stray splats far from the main body are masked",o["fl"]>=20 and o["fl"]>=(o["n"]-4000)*0.9,o)
    ok("the main body is left alone",o["core"]<=40,o)
    ok("cleanup can be undone",await t.ev("(function(){var o=OBJS[OBJS.length-1];undoDo();var m=0;for(var i=0;i<o.gs.n;i++)if(o.gs.mask&&o.gs.mask[i])m++;return m===0})()"))
    await t.ev("goHome()"); await t.wait(900); await t.new_project()
    await t.ev("""(function(){var pts=[],i;for(i=0;i<300;i++)pts.push(i*0.9,((i*7)%13)*0.9,((i*3)%11)*0.9);return addPlyFile(window.__plyF(pts))})()"""); await t.wait(1200)
    ok("a scene that is nearly all stray is left alone",await t.ev("autoFloaters(OBJS[OBJS.length-1])")==0)
    ok("the floater switch is on unless turned off",await t.ev("floatersOn()") is True)
    await t.ev("localStorage.setItem('sbfl','0')"); ok("and it remembers when it's off",await t.ev("floatersOn()") is False); await t.ev("localStorage.removeItem('sbfl')")
    return t.finish()
