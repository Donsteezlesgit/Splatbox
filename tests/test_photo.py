"""V032: one photo (and optional depth map) -> a 3D splat card."""
import json
from harness import *
MK="""window.__mk=function(name,top,bot,w,h){var c=document.createElement('canvas');c.width=w;c.height=h;var g=c.getContext('2d');g.fillStyle=top;g.fillRect(0,0,w,h/2);g.fillStyle=bot;g.fillRect(0,h/2,w,h/2);return new Promise(function(r){c.toBlob(function(b){r(new File([b],name,{type:'image/png'}))})})};
window.__px=function(b,fx,fy){return createImageBitmap(b).then(function(bm){var c=document.createElement('canvas');c.width=bm.width;c.height=bm.height;var g=c.getContext('2d');g.drawImage(bm,0,0);var d=g.getImageData(Math.round(bm.width*fx),Math.round(bm.height*fy),1,1).data;return JSON.stringify([d[0],d[1],d[2]])})}"""
async def run(br,site,fx):
    t=await open_page(br,site,"photo",w=1000,h=640); ok=t.ok
    await t.pg.evaluate(MK+";0")
    await t.new_project(); n0=await t.ev("OBJS.length")
    await t.ev("window.__mk('wall.png','#ff2020','#2020ff',160,100).then(function(f){return addPhotoFiles([f])})"); await t.wait(1500)
    ok("a photo becomes one splat object",await t.ev("OBJS.length")==n0+1,await t.ev("OBJS.length"))
    ok("it has one splat per pixel",await t.ev("OBJS[OBJS.length-1].gs.n")==160*100,await t.ev("OBJS[OBJS.length-1].gs.n"))
    ok("the object name says it's a photo",await t.ev("/photo/i.test(OBJS[OBJS.length-1].name)"),await t.ev("OBJS[OBJS.length-1].name"))
    ok("the object keeps a .ply blob so it saves with the project",await t.ev("OBJS[OBJS.length-1].blob instanceof Blob&&OBJS[OBJS.length-1].blob.size>1000"))
    await t.ev("setMode('render')"); await t.wait(400)
    top=json.loads(await t.ev("rFrame(400,250,false).then(function(b){return window.__px(b,0.5,0.4)})"))
    bot=json.loads(await t.ev("rFrame(400,250,false).then(function(b){return window.__px(b,0.5,0.6)})"))
    ok("it draws: red and blue halves are both visible",max(top)>60 and max(bot)>60,[top,bot])
    ok("the photo is the right way up (red on top)",top[0]>top[2] and bot[2]>bot[0],[top,bot])
    # with a depth map, two files together
    await t.ev("setMode('edit')")
    await t.ev("Promise.all([window.__mk('shot.png','#20ff20','#ffff20',120,80),window.__mk('shot_depth.png','#ffffff','#202020',120,80)]).then(function(fs){return addPhotoFiles(fs)})"); await t.wait(1500)
    ok("a photo plus a depth map makes one object, not two",await t.ev("OBJS.length")==n0+2,await t.ev("OBJS.length"))
    zz=json.loads(await t.ev("""Promise.all([window.__mk('a.png','#808080','#808080',40,40),window.__mk('a_depth.png','#ffffff','#000000',40,40)]).then(function(fs){return photoToPly(fs[0],fs[1])}).then(function(r){var f=new Float32Array(r.ab.slice(r.ab.byteLength-1600*56)),top=0,bot=0,i;for(i=0;i<1600;i++){if(f[i*14+1]>0.5)top+=f[i*14+2];else if(f[i*14+1]<-0.5)bot+=f[i*14+2]}return JSON.stringify({top:top,bot:bot})})"""))
    ok("white areas of the depth map come toward the camera (+Z)",zz["top"]>zz["bot"]+1,zz)
    return t.finish()
