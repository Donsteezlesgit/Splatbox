"""V032: big scenes sort in a Worker."""
import json
from harness import *
HASH="window.__h=function(b){return b.arrayBuffer().then(function(buf){var u=new Uint8Array(buf),h=0;for(var i=0;i<u.length;i+=3)h=(h*31+u[i])>>>0;return h+':'+u.length})}"
async def run(br,site,fx):
    t=await open_page(br,site,"sortworker",w=1000,h=640); ok=t.ok
    await t.pg.evaluate(HASH+";0")
    await t.new_project(); await t.add_ply(fx["tilt"]); await t.ev("closeTool()"); await t.wait(500)
    ok("small scenes are not sorted in the worker",await t.ev("(function(){var g=OBJS[OBJS.length-1].gs;return !g.wId&&SORT_ASYNC_N>g.n})()"))
    await t.ev("SORT_ASYNC_N=1000;dirty=true"); await t.wait(300)
    # orbit a little a few times; the worker should take over
    for i in range(6):
        await t.ev(f"rawTurnTo({0.3+0.15*i},0.1);dirty=true"); await t.wait(250)
    r=json.loads(await t.ev("(function(){var g=OBJS[OBJS.length-1].gs;return JSON.stringify({id:!!g.wId,done:g.wDone||0,busy:!!g.wBusy,ready:g.ibReady,sw:!!SW})})()"))
    ok("the worker started and finished sorts",r["sw"] and r["id"] and r["done"]>=1,r)
    await t.wait(600)
    # the finished order is a true back-to-front order for the view it was made for
    ordr=json.loads(await t.ev("""(function(){var g=OBJS[OBJS.length-1].gs,v=g.lastV,P=g.pos,n=g.n,i;
      return new Promise(function(res){var gl2=gl;gl2.bindBuffer(gl2.ARRAY_BUFFER,g.ib);var out=new Int32Array(n);gl2.getBufferSubData(gl2.ARRAY_BUFFER,0,out);
        var bad=0,prev=1e9,rng=g.dmx-g.dmn,tol=rng/65535*1.01;for(i=0;i<n;i++){var d=-(v[0]*P[out[i]*3]+v[1]*P[out[i]*3+1]+v[2]*P[out[i]*3+2]+v[3]);if(d>prev+tol)bad++;prev=Math.min(prev,d)}
        var seen=new Uint8Array(n),dup=0;for(i=0;i<n;i++){if(seen[out[i]])dup++;seen[out[i]]=1}
        res(JSON.stringify({bad:bad,dup:dup,n:n}))})})()"""))
    ok("the order from the worker is sorted back to front",ordr["bad"]==0 and ordr["dup"]==0,ordr)
    # renders never use the worker, and look the same either way
    await t.ev("setMode('render')"); await t.wait(300)
    a=await t.ev("rFrame(320,180,false).then(window.__h)")
    await t.ev("SORT_ASYNC_N=1e9"); b=await t.ev("rFrame(320,180,false).then(window.__h)")
    ok("a rendered frame is identical with or without the worker",a==b,[a,b])
    # re-uploading geometry drops the worker's copy
    await t.ev("SORT_ASYNC_N=1000;uploadGSGeo(OBJS[OBJS.length-1].gs)")
    ok("re-uploading resets the worker copy",await t.ev("!OBJS[OBJS.length-1].gs.wId"))
    return t.finish()
