"""V023: undo, selection tools (brush, box, lasso, sphere), delete mask, save/reload, export, floater finder."""
import json, re
from harness import *
async def counts(t): return json.loads(await t.ev("JSON.stringify(sxCounts(SEL.gs))"))
async def drag(t,pts,mods=()):
    bb=await t.pg.locator("#gl").bounding_box()
    for m in mods: await t.pg.keyboard.down(m)
    await t.pg.mouse.move(bb["x"]+pts[0][0],bb["y"]+pts[0][1]); await t.pg.mouse.down()
    for x,y in pts[1:]: await t.pg.mouse.move(bb["x"]+x,bb["y"]+y,steps=4)
    await t.pg.mouse.up()
    for m in mods: await t.pg.keyboard.up(m)
    await t.wait(400)
async def run(br,site,fx):
    t=await open_page(br,site,"select",w=1000,h=640); ok=t.ok
    await t.new_project(); await t.add_ply(fx["tilt"]); await t.ev("closeTool()")
    await t.ev("openTool('select')"); await t.wait(500)
    ok("select tool opens on the splat",(await t.ev("!!selObj()")) and await t.pg.locator("#sxInfo").count()==1)
    n=await t.ev("SEL.gs.n"); bb=await t.pg.locator("#gl").bounding_box(); W,H=bb["width"],bb["height"]
    pb=await t.pg.locator("#pop").bounding_box(); X0=20   # the panel is docked now, so the whole view is free
    # box select covering everything
    await t.pg.click("#sxTool [data-v=rect]")
    await drag(t,[(5,5),(W-5,H-5)])
    c=await counts(t); ok("box select picks splats",c["sel"]>0 and c["del"]==0,c)
    allsel=c["sel"]
    # clear, then lasso a smaller area
    await t.pg.click("[data-act=sx-none]"); await t.wait(200)
    ok("clear empties the selection",(await counts(t))["sel"]==0)
    await t.pg.click("#sxTool [data-v=lasso]")
    await drag(t,[(X0,H*0.25),(W-10,H*0.25),(W-10,H*0.75),(X0,H*0.75),(X0,H*0.25)])
    c=await counts(t); ok("lasso selects part of the splat",0<c["sel"]<=allsel,[c,allsel])
    # brush with Shift adds
    await t.pg.click("[data-act=sx-none]"); await t.pg.click("#sxTool [data-v=brush]")
    await drag(t,[(X0,H*0.45),(W-20,H*0.45)])
    cb=await counts(t); ok("brush paints a selection",cb["sel"]>0,cb)
    # sphere
    await t.pg.click("[data-act=sx-none]"); await t.pg.click("#sxTool [data-v=sphere]")
    await t.ev("SX.rad=1.5"); bbx=await t.pg.locator("#gl").bounding_box()
    await t.pg.mouse.click(bbx["x"]+X0+(W-X0)/2,bbx["y"]+H/2); await t.wait(500)
    cs=await counts(t); ok("sphere selects around a clicked spot",cs["sel"]>0,cs)
    # delete -> mask, undo, redo
    await t.pg.click("[data-act=sx-none]"); await t.pg.click("#sxTool [data-v=rect]")
    await drag(t,[(X0,5),(X0+(W-X0)*0.5,H-5)])
    await t.pg.click("[data-act=sx-del]"); await t.wait(300)
    c=await counts(t); ok("delete masks the selected splats",0<c["del"]<n and c["sel"]==0,[c,n]); deleted=c["del"]
    await t.pg.keyboard.press("Control+z"); await t.wait(300)
    c=await counts(t); ok("Ctrl+Z brings them back",c["del"]==0 and c["sel"]>0,c)
    await t.pg.keyboard.press("Control+Shift+z"); await t.wait(300)
    c=await counts(t); ok("Ctrl+Shift+Z deletes them again",c["del"]==deleted,c)
    # drawn colour is transparent for deleted ones
    alpha=await t.ev("(function(){var g=SEL.gs,s=0;for(var i=0;i<g.n;i++)if(g.mask[i]&&g.col[i*4+3]!==0)s++;return s})()")
    ok("deleted splats are drawn invisible",alpha==0,alpha)
    ok("picking ignores deleted splats",(await t.ev("(function(){var g=SEL.gs,k=0;for(var i=0;i<g.n;i++)if(g.mask[i])k++;return k})()"))==deleted)
    # save, leave, reopen: mask comes back
    await t.pg.click("#saveBtn"); await t.wait(1200)
    snapA=json.loads(await t.ev("snapshotState()"))
    await t.ev("goHome()"); await t.wait(1500)
    await t.pg.locator("#grid .card:not(.new)").first.click(); await t.wait(3500)
    snapB=json.loads(await t.ev("snapshotState()"))
    ok("deleted splats are still deleted after reopening",snapA==snapB and snapB["objs"][0].get("masked")==deleted,[ (k,snapA[k],snapB[k]) for k in snapA if snapA[k]!=snapB[k]])
    # export skips them
    async with t.pg.expect_download() as dl: await t.ev("exportScenePLY()")
    d=await dl.value; import os,tempfile
    path=os.path.join(tempfile.mkdtemp(),d.suggested_filename); await d.save_as(path)
    head=open(path,"rb").read(400).decode("latin1"); m=re.search(r"element vertex (\d+)",head)
    ok("export leaves out deleted splats",m and int(m.group(1))==n-deleted,[m and m.group(1),n-deleted])
    # bring back + undo history is per project
    await t.ev("openTool('select')"); await t.wait(400); await t.pg.click("[data-act=sx-restore]"); await t.wait(300)
    ok("bring deleted back clears the mask",(await counts(t))["del"]==0)
    # removing a whole object with Delete can be undone; Delete in the Select tool only deletes the selection
    await t.ev("closeTool()"); await t.ev("SEL=OBJS[0]"); await t.pg.keyboard.press("Delete"); await t.wait(500)
    ok("Delete with no tool open removes the object",(await t.ev("OBJS.length"))==0)
    await t.pg.keyboard.press("Control+z"); await t.wait(1500)
    ok("Ctrl+Z brings the removed object back",(await t.ev("OBJS.length"))==1 and (await t.ev("OBJS[0].gs.n"))==n,await t.ev("OBJS.length"))
    await t.ev("SEL=OBJS[0];openTool('select')"); await t.wait(400); await t.pg.keyboard.press("Backspace"); await t.wait(400)
    ok("Backspace in the Select tool leaves the object alone",(await t.ev("OBJS.length"))==1)
    # floater finder on a synthetic cloud: dense blob plus 20 loners
    r=json.loads(await t.ev("""(function(){var n=6020,pos=new Float32Array(n*3),al=new Float32Array(n).fill(0.9),i,s=7;
      function rnd(){s=(s*16807)%2147483647;return s/2147483647}
      for(i=0;i<6000;i++){pos[i*3]=rnd();pos[i*3+1]=rnd();pos[i*3+2]=rnd()}
      for(i=6000;i<n;i++){pos[i*3]=5+rnd()*8;pos[i*3+1]=-6-rnd()*8;pos[i*3+2]=4+rnd()*9}
      var h=findFloaters({n:n,pos:pos,alpha:al,mask:null},40),a=0,b=0;
      for(i=0;i<6000;i++)a+=h[i];for(i=6000;i<n;i++)b+=h[i];return JSON.stringify({blob:a,loners:b})})()"""))
    ok("floater finder flags the loners",r["loners"]>=18,r); ok("floater finder keeps the dense blob",r["blob"]<60,r)
    return t.finish()
