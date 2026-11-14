"""Backup files: export, import, wrong files, newer files, typed arrays, download buttons."""
import json, os, struct, tempfile
from harness import *
async def run(br,site,fx):
    t=await open_page(br,site,"backup")
    await t.new_project()
    await t.add_ply(fx["tilt"]); await t.add_mesh(fx["cube"]); await t.ev("closeTool()")
    await t.ev("addCamera();S.vig=0.4;cur.lut='LUT_3D_SIZE 2\\n0 0 0\\n1 0 0\\n0 1 0\\n1 1 0\\n0 0 1\\n1 0 1\\n0 1 1\\n1 1 1\\n';cur.lutName='x';cur.extra=new Float32Array([1.5,2.5,3.5])")
    await t.pg.click("#saveBtn"); await t.wait(1200)
    # round trip in memory, byte for byte
    res=await t.ev("""(function(){var rec=cur;var f=new File([packProjects([rec])],'x.splatbox');
      return unpackProjects(f).then(function(r){
        function cmp(a,b,path){
          if(a instanceof Blob){return b instanceof Blob&&a.size===b.size?a.arrayBuffer().then(function(x){return b.arrayBuffer().then(function(y){var u=new Uint8Array(x),v=new Uint8Array(y);for(var i=0;i<u.length;i++)if(u[i]!==v[i])return [path+' bytes differ'];return []})}):Promise.resolve([path+' blob'])}
          if(ArrayBuffer.isView(a)){return Promise.resolve(ArrayBuffer.isView(b)&&a.constructor===b.constructor&&a.length===b.length&&a.every(function(x,i){return x===b[i]})?[]:[path+' typed array'])}
          if(a&&typeof a==='object'){var ks=Object.keys(a),ps=[];ks.forEach(function(k){ps.push(cmp(a[k],b?b[k]:undefined,path+'.'+k))});var kb=b&&typeof b==='object'?Object.keys(b):[];if(kb.length!==ks.length)ps.push(Promise.resolve([path+' key count '+ks.length+' vs '+kb.length]));return Promise.all(ps).then(function(x){return [].concat.apply([],x)})}
          return Promise.resolve(a===b?[]:[path+' '+a+' != '+b])}
        return cmp(rec,r[0],'rec').then(function(d){return JSON.stringify({n:r.length,diffs:d})})})})()""")
    res=json.loads(res)
    t.ok("export then unpack gives back an identical project (blobs byte for byte)",res["n"]==1 and not res["diffs"],res["diffs"][:3])
    snapA=await t.ev("snapshotState()"); nm=await t.ev("cur.name")
    # download buttons
    await t.ev("openTool('file')")
    async with t.pg.expect_download() as dl: await t.pg.click('[data-act=fExport]')
    d=await dl.value; path=os.path.join(tempfile.mkdtemp(),d.suggested_filename); await d.save_as(path)
    t.ok("File > Export gives a .splatbox file",path.endswith(".splatbox") and os.path.getsize(path)>1000,os.path.basename(path))
    data=open(path,"rb").read()
    await t.ev("goHome()"); await t.wait(1500)
    n0=await t.pg.locator("#grid .card:not(.new)").count()
    async with t.pg.expect_download() as dl2: await t.pg.click("#homeBackup")
    d2=await dl2.value
    t.ok("Back up all gives a file",d2.suggested_filename.startswith("splatbox-backup-"))
    t.ok("home shows when you last backed up","Last backup" in await t.pg.inner_text("#bk"),await t.pg.inner_text("#bk"))
    # import it back as a copy
    await t.pg.set_input_files("#projIn",path); await t.wait(1500)
    n1=await t.pg.locator("#grid .card:not(.new)").count()
    t.ok("import adds a copy and overwrites nothing",n1==n0+1,[n0,n1])
    cards=t.pg.locator(f"#grid .card:has-text('{nm}')"); idx=await cards.count()
    await cards.nth(0).click(); await t.wait(3500)
    snapB=await t.ev("snapshotState()")
    a,b=json.loads(snapA),json.loads(snapB)
    # ids and blobs sizes may legitimately match; compare everything
    t.ok("an imported project opens exactly like the original",a==b,[k for k in a if a[k]!=b.get(k)])
    # bad files
    await t.ev("goHome()"); await t.wait(1500)
    junk=os.path.join(tempfile.mkdtemp(),"junk.splatbox"); open(junk,"w").write("not a backup")
    n2=await t.pg.locator("#grid .card:not(.new)").count()
    await t.pg.set_input_files("#projIn",junk); await t.wait(800)
    t.ok("a wrong file is refused",await t.pg.locator("#grid .card:not(.new)").count()==n2)
    t.errs=[e for e in t.errs if "isn't a Splatbox" in e]  # (status text only; not console)
    hl=struct.unpack("<I",data[8:12])[0]; head=json.loads(data[12:12+hl]); head["format"]=99
    nh=json.dumps(head).encode(); newer=os.path.join(tempfile.mkdtemp(),"newer.splatbox")
    open(newer,"wb").write(data[:8]+struct.pack("<I",len(nh))+nh+data[12+hl:])
    await t.pg.set_input_files("#projIn",newer); await t.wait(800)
    t.ok("a backup from a newer version is refused",await t.pg.locator("#grid .card:not(.new)").count()==n2)
    t.errs=[]
    return t.finish()
