"""V033: SHARP button and flow in the app, with a stand-in desktop bridge (the real model is tested on a PC)."""
import json
from harness import *
STUB="""window.__sh={calls:[],dl:'ok',ready:false,run:'ok',prog:null};
window.__plyAB=function(n){var names=['x','y','z','f_dc_0','f_dc_1','f_dc_2','opacity','scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3'];
 var head=new TextEncoder().encode('ply\\nformat binary_little_endian 1.0\\nelement vertex '+n+'\\n'+names.map(function(p){return 'property float '+p}).join('\\n')+'\\nend_header\\n'),f=new Float32Array(n*14),i;
 for(i=0;i<n;i++){var b=i*14;f[b]=(i%10)*0.1-0.5;f[b+1]=Math.floor(i/10)*0.1-0.5;f[b+2]=0;f[b+3]=1;f[b+4]=0;f[b+5]=0;f[b+6]=3;f[b+7]=f[b+8]=f[b+9]=-3;f[b+10]=1}
 var u=new Uint8Array(head.length+f.byteLength);u.set(head,0);u.set(new Uint8Array(f.buffer),head.length);return u.buffer};
window.splatboxDesktop={isDesktop:true,encode:{start:function(){return Promise.resolve(1)},frame:function(){return Promise.resolve()},finish:function(){return Promise.resolve({})},cancel:function(){return Promise.resolve(true)}},
 sharp:{status:function(){__sh.calls.push('status');return Promise.resolve({ready:__sh.ready,bytes:1319661752})},
  onProgress:function(fn){__sh.prog=fn},
  download:function(){__sh.calls.push('download');if(__sh.dl==='cancel')return Promise.resolve({ok:false,cancelled:true});if(__sh.dl==='fail')return Promise.resolve({ok:false,error:'no network'});if(__sh.prog)__sh.prog({got:5e8,total:1.3e9});__sh.ready=true;return Promise.resolve({ok:true})},
  cancel:function(){return Promise.resolve()},
  run:function(chw,info){__sh.calls.push('run');__sh.len=chw.length;__sh.type=chw.constructor.name;__sh.info=info;__sh.max=chw.reduce(function(a,b){return Math.max(a,b)},0);if(__sh.run==='fail')return Promise.resolve({ok:false,error:'SHARP ran out of memory.'});return Promise.resolve({ok:true,ply:__plyAB(400),eps:'dml',n:800})}}};
window.__mk=function(name,col,w,h){var c=document.createElement('canvas');c.width=w;c.height=h;var g=c.getContext('2d');g.fillStyle=col;g.fillRect(0,0,w,h);return new Promise(function(r){c.toBlob(function(b){r(new File([b],name,{type:'image/png'}))})})}"""
async def run(br,site,fx):
    t=await open_page(br,site,"sharp",w=1000,h=640); ok=t.ok
    await t.new_project()
    ok("no SHARP button in the web version",await t.ev("sharpOK()") is False)
    await t.pg.evaluate(STUB+";0")
    ok("the desktop bridge turns SHARP on",await t.ev("sharpOK()") is True)
    await t.ev("openTool('add')"); await t.wait(300)
    ok("the SHARP button is in the Objects panel",await t.pg.locator("[data-act=oSharp]").count()==1)
    n0=await t.ev("OBJS.length")
    # download cancelled: nothing added, no run
    await t.ev("__sh.dl='cancel'")
    await t.ev("__mk('beach.png','#3080c0',300,200).then(addSharpPhoto)"); await t.wait(800)
    ok("cancelling the download adds nothing and doesn't run",await t.ev("OBJS.length")==n0 and "run" not in await t.ev("__sh.calls"),await t.ev("__sh.calls"))
    ok("busy overlay is closed again",not await t.ev("$('busy').classList.contains('on')"))
    # download fails: clear error
    await t.ev("__sh.dl='fail';__sh.calls=[]")
    await t.ev("__mk('beach.png','#3080c0',300,200).then(addSharpPhoto)"); await t.wait(800)
    ok("a failed download says why",await t.ev("OBJS.length")==n0 and "no network" in await t.ev("$('toast').textContent"),await t.ev("$('toast').textContent"))
    # the happy path
    await t.ev("__sh.dl='ok';__sh.calls=[]")
    await t.ev("__mk('beach.png','#ff8000',300,200).then(addSharpPhoto)"); await t.wait(2500)
    ok("it downloads, then runs, in that order",await t.ev("__sh.calls.join(',')")=="status,download,status,run" or await t.ev("__sh.calls.join(',')")=="status,download,run",await t.ev("__sh.calls.join(',')"))
    ok("the model is fed a 1536x1536 float picture scaled 0..1",await t.ev("__sh.len")==3*1536*1536 and await t.ev("__sh.type")=="Float32Array" and 0.99<await t.ev("__sh.max")<=1.0,[await t.ev("__sh.len"),await t.ev("__sh.max")])
    info=json.loads(await t.ev("JSON.stringify(__sh.info)"))
    ok("it passes the photo's width as focal length and its shape",info["focalPx"]==300 and info["imgW"]==300 and abs(info["aspect"]-200/300)<1e-6,info)
    ok("the result becomes one splat object named for the photo",await t.ev("OBJS.length")==n0+1 and "SHARP" in await t.ev("OBJS[OBJS.length-1].name"),await t.ev("OBJS[OBJS.length-1].name"))
    ok("it has the splats SHARP returned",await t.ev("OBJS[OBJS.length-1].gs.n")==400)
    ok("the status mentions the graphics card and the licence",("graphics card" in await t.ev("$('toast').textContent")) and ("personal" in await t.ev("$('toast').textContent")))
    # already downloaded: no second download. run error is reported
    await t.ev("__sh.calls=[];__sh.run='fail'")
    await t.ev("__mk('b.png','#222222',200,200).then(addSharpPhoto)"); await t.wait(1200)
    ok("with the model ready it skips the download",await t.ev("__sh.calls.join(',')")=="status,run",await t.ev("__sh.calls.join(',')"))
    ok("a failed run shows the reason and adds nothing",await t.ev("OBJS.length")==n0+1 and "out of memory" in await t.ev("$('toast').textContent"),await t.ev("$('toast').textContent"))
    return t.finish()
