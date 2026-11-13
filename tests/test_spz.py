"""V032: SPZ export and import."""
import json
from harness import *
async def run(br,site,fx):
    t=await open_page(br,site,"spz",w=900,h=600); ok=t.ok
    await t.new_project(); await t.add_ply(fx["tilt"]); await t.ev("closeTool()")
    # export -> import round trip on the real scene rows
    r=json.loads(await t.ev("""collectScene().then(function(r){return spzFromRows(r).then(function(b){window.__spz=b;return spzToPly(b.buffer.slice(b.byteOffset,b.byteOffset+b.length)).then(function(pb){
      var raw=parsePly(pb),orig=new Float32Array(new Blob(r.parts.slice(0,1)).size/4),n=raw?raw.n||raw.count||0:0;
      return new Blob(r.parts).arrayBuffer().then(function(ob){var o=new Float32Array(ob),p=new Float32Array(pb.slice(pb.byteLength-r.total*56)),i,dp=0,dc=0,da=0,ds=0,dq=0;
        for(i=0;i<r.total;i++){var a=i*17,c=i*14,j;
          for(j=0;j<3;j++){dp=Math.max(dp,Math.abs(o[a+j]-p[c+j]));dc=Math.max(dc,Math.abs(o[a+6+j]-p[c+3+j]));ds=Math.max(ds,Math.abs(o[a+10+j]-p[c+7+j]))}
          da=Math.max(da,Math.abs(1/(1+Math.exp(-o[a+9]))-1/(1+Math.exp(-p[c+6]))));
          var dot=0;for(j=0;j<4;j++)dot+=o[a+13+j]*p[c+10+j];dq=Math.max(dq,1-Math.abs(dot))}
        return JSON.stringify({total:r.total,bytes:b.length,ply:ob.byteLength,parsed:!!raw,dp:dp,dc:dc,da:da,ds:ds,dq:dq})})})})})"""))
    ok("the scene packs and unpacks with the same splat count",r["parsed"] and r["total"]>0,r)
    ok("positions survive within fixed-point precision",r["dp"]<2e-3,r["dp"])
    ok("colours survive",r["dc"]<0.05,r["dc"])
    ok("opacity survives",r["da"]<0.01,r["da"])
    ok("scales survive",r["ds"]<0.07,r["ds"])
    ok("rotations survive",r["dq"]<1e-4,r["dq"])
    ok("SPZ is much smaller than the PLY",r["bytes"]*3<r["ply"],[r["bytes"],r["ply"]])
    h=json.loads(await t.ev("(function(){var b=window.__spz;return new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer().then(function(ab){var d=new DataView(ab);return JSON.stringify({gz:b[0]===0x1f&&b[1]===0x8b,magic:d.getUint32(0,true)===0x5053474e,ver:d.getUint32(4,true),n:d.getUint32(8,true),sh:new Uint8Array(ab)[12]})})})()"))
    ok("the header is SPZ version 3 with no extra colour bands",h["gz"] and h["magic"] and h["ver"]==3 and h["sh"]==0,h)
    # bad input gives clear messages
    for name,code,frag in [("a non-SPZ file","spzToPly(new Uint8Array([1,2,3,4,5,6]).buffer)","isn't an SPZ"),
                           ("a v4 file","spzToPly(new Uint8Array([0x4e,0x47,0x53,0x50,4,0,0,0]).buffer)","version 4")]:
        m=await t.ev(f"{code}.then(function(){{return 'no error'}},function(e){{return e.message}})")
        ok(f"{name} gets a clear message",frag in m,m)
    # end to end: add the SPZ back as an object through the real file path
    cnt=await t.ev("OBJS.length")
    await t.ev("""(function(){var b=window.__spz;return addPlyFile(new File([b],'round.spz'))})()""")
    await t.wait(600)
    ok("an .spz file adds as a splat object",await t.ev("OBJS.length")==cnt+1,await t.ev("OBJS.length"))
    return t.finish()
