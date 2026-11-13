"""V032: TouchDesigner export - camera path, 16-bit depth pass, colour frames, point cloud."""
import json, math
from harness import *
ZF="""window.__zfiles=function(b){return b.arrayBuffer().then(function(buf){var u=new Uint8Array(buf),dv=new DataView(buf),o=0,m={};while(o+30<=u.length&&dv.getUint32(o,true)===0x04034b50){var sz=dv.getUint32(o+18,true),nl=dv.getUint16(o+26,true),nm=new TextDecoder().decode(u.subarray(o+30,o+30+nl));m[nm]=u.slice(o+30+nl,o+30+nl+sz);o+=30+nl+sz}window.__Z=m;var e=u.length-22;return JSON.stringify({names:Object.keys(m),end:dv.getUint32(e,true)===0x06054b50})})}"""
PI="""window.__pngInfo=function(name){var u=window.__Z[name],dv=new DataView(u.buffer,u.byteOffset);var w=dv.getUint32(16),h=dv.getUint32(20),bd=u[24],ct=u[25],sig=u[0]===137&&u[1]===80;var o=8,idat=[];while(o<u.length){var n=dv.getUint32(o),t=String.fromCharCode(u[o+4],u[o+5],u[o+6],u[o+7]);if(t==='IDAT')idat.push(u.subarray(o+8,o+8+n));o+=12+n}var tot=idat.reduce(function(a,c){return a+c.length},0),cat=new Uint8Array(tot),p=0;idat.forEach(function(c){cat.set(c,p);p+=c.length});if(bd!==16)return Promise.resolve(JSON.stringify({w:w,h:h,bd:bd,ct:ct,sig:sig}));return new Response(new Blob([cat]).stream().pipeThrough(new DecompressionStream('deflate'))).arrayBuffer().then(function(raw){var r=new Uint8Array(raw),row=w*2+1,vals=new Uint16Array(w*h),y,x;for(y=0;y<h;y++)for(x=0;x<w;x++)vals[y*w+x]=(r[y*row+1+x*2]<<8)|r[y*row+2+x*2];var nz=0,set={};for(var i=0;i<vals.length;i++){if(vals[i]){nz++;set[vals[i]]=1}}return JSON.stringify({w:w,h:h,bd:bd,ct:ct,sig:sig,center:vals[(h>>1)*w+(w>>1)],nz:nz,distinct:Object.keys(set).length,len:r.length,exp:h*row})})};
window.__txt=function(name){return new TextDecoder().decode(window.__Z[name])};
window.__plyInfo=function(name){var u=window.__Z[name],t=new TextDecoder('latin1').decode(u.subarray(0,400)),e=t.indexOf('end_header\\n')+11,n=+(/element vertex (\\d+)/.exec(t)||[])[1];return JSON.stringify({n:n,hdr:e,len:u.length,okLen:u.length===e+n*15,props:(t.match(/property \\w+ \\w+/g)||[]).length})}"""
async def run(br,site,fx):
    t=await open_page(br,site,"render",w=1000,h=640); ok=t.ok
    await t.pg.evaluate(ZF+";0"); await t.pg.evaluate(PI+";0")
    await t.new_project(); await t.add_ply(fx["tilt"]); await t.ev("closeTool()")
    await t.ev("setMode('render')"); await t.wait(400)
    # the shared camera maths must agree with what the renderer actually used
    r=json.loads(await t.ev("rFrame(320,180,false).then(function(){var v=viewNow(null,320,180),L=LASTM,d=0,i;for(i=0;i<16;i++)d=Math.max(d,Math.abs(v.V[i]-L.V[i]));for(i=0;i<3;i++)d=Math.max(d,Math.abs(v.eye[i]-L.eye[i]));return JSON.stringify({d:d,t:Math.abs(v.tyv-L.tyv)})})"))
    ok("the camera maths matches what the renderer used",r["d"]<1e-6 and r["t"]<1e-9,r)
    # a camera that dollies in
    await t.ev("addCamera()"); await t.ev("enterThru(SEL)"); cid=await t.ev("SEL.id"); P=f"o:{cid}:pos"
    await t.ev(f"S.dur=2;S.rfps='3';tlKey('{P}',0,[0,0,1.95]);tlKey('{P}',2,[0,0,1.0])"); await t.wait(300)
    R=await t.ev("SEL.R.slice()")
    names=json.loads(await t.ev("tdExport({w:320,h:180,fps:3,frames:6,rgb:true,ply:true}).then(window.__zfiles)"))
    ns=names["names"]
    ok("the export is a valid zip",names["end"] and len(ns)>0,names)
    ok("it has one depth frame per frame",len([n for n in ns if n.startswith("depth/")])==6,ns)
    ok("it has one colour frame per frame",len([n for n in ns if n.startswith("rgb/")])==6,ns)
    ok("it has the camera files, readme and point cloud",all(x in ns for x in ["camera.json","camera.csv","camera.chan","README.txt","points.ply"]),ns)
    cam=json.loads(await t.ev("window.__txt('camera.json')"))
    ok("camera.json describes 6 frames at 320x180",cam["frames"]==6 and len(cam["camera"])==6 and cam["width"]==320 and cam["height"]==180 and cam["fps"]==3,{k:cam[k] for k in("frames","width","height","fps")})
    c0=cam["camera"][0]; zs=[c["position"][2] for c in cam["camera"]]
    ok("the camera starts where its key is",all(abs(a-b)<1e-3 for a,b in zip(c0["position"],[0,0,1.95])),c0["position"])
    ok("the camera dollies in over the frames",all(zs[i+1]<zs[i] for i in range(5)) and zs[-1]<1.5,zs)
    back=[c0["matrix"][2],c0["matrix"][6],c0["matrix"][10]]
    ok("the camera's back axis matches the camera object",all(abs(a-b)<1e-4 for a,b in zip(back,[R[2],R[5],R[8]])),[back,[R[2],R[5],R[8]]])
    ok("the rotation matrix is orthonormal",abs(math.hypot(*[c0["matrix"][i] for i in (0,4,8)])-1)<1e-4 and abs(math.hypot(*[c0["matrix"][i] for i in (1,5,9)])-1)<1e-4)
    ok("field of view agrees with the aspect ratio",abs(math.tan(math.radians(c0["fov_x"]/2))/math.tan(math.radians(c0["fov_y"]/2))-320/180)<1e-3,[c0["fov_x"],c0["fov_y"]])
    csv=(await t.ev("window.__txt('camera.csv')")).strip().split("\n"); chan=(await t.ev("window.__txt('camera.chan')")).strip().split("\n")
    ok("camera.csv has a header and one row per frame",len(csv)==7 and csv[0].startswith("frame,time,tx,ty,tz,rx,ry,rz") and len(csv[1].split(","))==10,csv[:2])
    ok("camera.chan has one 7-number line per frame",len(chan)==6 and all(len(l.split())==7 for l in chan),chan[:2])
    far=cam["depth"]["far"]
    d1=json.loads(await t.ev("window.__pngInfo('"+[n for n in ns if n.startswith("depth/")][0]+"')"))
    d6=json.loads(await t.ev("window.__pngInfo('"+[n for n in ns if n.startswith("depth/")][-1]+"')"))
    ok("depth frames are 16-bit greyscale PNGs of the right size",d1["bd"]==16 and d1["ct"]==0 and d1["sig"] and d1["w"]==320 and d1["h"]==180 and d1["len"]==d1["exp"],d1)
    ok("the depth pass hits the splats",d1["nz"]>200,d1)
    ok("depth uses the full 16 bits, not 8",d1["distinct"]>400,d1["distinct"])
    z1=d1["center"]/65535*far; z6=d6["center"]/65535*far
    ok("centre depth is a sensible distance",0.3<z1<far,[z1,far])
    ok("depth gets smaller as the camera dollies in",d6["center"]>0 and z1-z6>0.3,[z1,z6])
    rg=json.loads(await t.ev("window.__pngInfo('"+[n for n in ns if n.startswith("rgb/")][0]+"')"))
    ok("colour frames are PNGs of the right size",rg["sig"] and rg["w"]==320 and rg["h"]==180 and rg["bd"]==8,rg)
    pl=json.loads(await t.ev("window.__plyInfo('points.ply')"))
    ok("the point cloud is a well-formed coloured PLY",pl["n"]>100 and pl["okLen"] and pl["props"]==6,pl)
    ok("the viewer and timeline are back to normal",(await t.ev("RO===null&&TRANSP===false&&DEPTHP===null&&FORCESORT===false&&RJ===null")))
    # options
    n2=json.loads(await t.ev("tdExport({w:320,h:180,fps:3,frames:2,rgb:false,ply:false}).then(window.__zfiles)"))["names"]
    ok("colour frames and point cloud can be left out",not any(n.startswith("rgb/") for n in n2) and "points.ply" not in n2 and len([n for n in n2 if n.startswith("depth/")])==2,n2)
    # cancel
    await t.ev("window.__p=tdExport({w:320,h:180,fps:3,frames:12,rgb:true,ply:true});setTimeout(function(){rjCancel()},150);0")
    res=await t.ev("window.__p.then(function(b){return b===null})")
    ok("Cancel stops the export and cleans up",res==True and (await t.ev("RJ===null&&RO===null&&DEPTHP===null")))
    # normal frames are untouched by the depth machinery
    a=await t.ev("rFrame(320,180,false).then(function(b){return b.arrayBuffer().then(function(x){var u=new Uint8Array(x),h=0;for(var i=0;i<u.length;i+=5)h=(h*31+u[i])>>>0;return h+':'+u.length})})")
    b=await t.ev("rFrame(320,180,false).then(function(b){return b.arrayBuffer().then(function(x){var u=new Uint8Array(x),h=0;for(var i=0;i<u.length;i+=5)h=(h*31+u[i])>>>0;return h+':'+u.length})})")
    ok("ordinary frames are still identical frame to frame",a==b,[a,b])
    await t.ev("openTool('capture')"); await t.wait(300)
    ok("the Capture panel has the TouchDesigner export controls",(await t.pg.locator('#popB [data-act=tdExport]').count())==1 and (await t.pg.locator('#popB [data-k=tdrgb]').count())==1 and (await t.pg.locator('#popB [data-k=tdply]').count())==1)
    return t.finish()
