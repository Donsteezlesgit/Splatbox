"""Real ffmpeg encode test inside Electron (not in run.py: needs Electron + deps in desktop/).
   (cd desktop && npm i && node prepare.js) && python3 tests/desktop_encode.py"""
import subprocess, time, os, sys, json, re, tempfile
from playwright.sync_api import sync_playwright
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D=os.path.join(ROOT,"desktop")
FF=subprocess.check_output(["node","-e","console.log(require('@ffmpeg-installer/ffmpeg').path)"],cwd=D,text=True).strip()
out=tempfile.mkdtemp(prefix="sbx-enc-")
env=dict(os.environ,SPLATBOX_TEST="1",SPLATBOX_TEST_OUT=out)
p=subprocess.Popen(["xvfb-run","-a",D+"/node_modules/.bin/electron",D,"--no-sandbox","--use-angle=swiftshader","--enable-unsafe-swiftshader","--remote-debugging-port=9334"],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
fails=[]
def ok(name,cond,info=""):
    print(("PASS " if cond else "FAIL ")+name+(" "+str(info) if (info and not cond) else ""));
    if not cond: fails.append(name)
JS="""async(o)=>{
  const E=window.splatboxDesktop.encode;
  const id=await E.start({fmt:o.fmt,fps:25,w:320,h:240,transp:o.transp,name:o.name});
  if(!id)return {id:null};
  const c=document.createElement('canvas');c.width=320;c.height=240;const g=c.getContext('2d');
  for(let i=0;i<10;i++){
    g.clearRect(0,0,320,240);g.fillStyle='rgba(255,'+(i*20)+',40,'+(o.transp?0.5:1)+')';g.fillRect(40+i*12,40,120,120);
    const b=await new Promise(r=>c.toBlob(r,'image/png'));
    await E.frame(id,new Uint8Array(await b.arrayBuffer()));
  }
  return await E.finish(id);
}"""
def probe(f):
    r=subprocess.run([FF,"-hide_banner","-i",f,"-f","null","-"],capture_output=True,text=True)
    t=r.stderr; m=re.findall(r"frame=\s*(\d+)",t)
    return t,(int(m[-1]) if m else -1)
try:
    with sync_playwright() as pw:
        b=None
        for i in range(60):
            try: b=pw.chromium.connect_over_cdp("http://127.0.0.1:9334"); break
            except Exception: time.sleep(0.5)
        assert b,"no electron"
        pg=None
        for i in range(60):
            for c in b.contexts:
                for x in c.pages:
                    if x.url.startswith("app://"): pg=x
            if pg: break
            time.sleep(0.5)
        assert pg,"no app page"
        pg.wait_for_timeout(1500)
        for fmt,tr,want in [("prores4444",True,["prores","4444","yuva444p12le"]),("prores4444",False,["prores","4444","yuv444p12le"]),("prores422",False,["prores","HQ","yuv422p10le"]),("dnxhr",False,["dnxhd","yuv422p10le"]),("mp4",False,["h264","yuv420p"])]:
            name=fmt+("-a" if tr else "")
            r=pg.evaluate("("+JS+")",{"fmt":fmt,"transp":tr,"name":name})
            f=os.path.join(out,name+("." + ("mp4" if fmt=="mp4" else "mov")))
            ok(name+" file written",bool(r) and r.get("bytes",0)>500 and os.path.exists(f),r)
            if os.path.exists(f):
                t,n=probe(f)
                ok(name+" 10 frames",n==10,n)
                for w in want: ok(name+" has "+w,w.lower() in t.lower(),t[-400:])
                ok(name+" 320x240","320x240" in t)
                if fmt=="prores4444" and not tr: ok(name+" has no alpha plane","yuva" not in t.lower())
        # cancel removes the file
        r=pg.evaluate("""async()=>{const E=window.splatboxDesktop.encode;const id=await E.start({fmt:'mp4',fps:25,name:'cancelme'});return await E.cancel(id)}""")
        ok("cancel ok",r is True,r); ok("cancel removes file",not os.path.exists(os.path.join(out,"cancelme.mp4")))
        # bad frame data -> finish fails cleanly
        r=pg.evaluate("""async()=>{const E=window.splatboxDesktop.encode;const id=await E.start({fmt:'mp4',fps:25,name:'bad'});await E.frame(id,new Uint8Array([1,2,3,4]));try{await E.finish(id);return 'no error'}catch(e){return 'err'}}""")
        ok("bad input errors cleanly",r=="err",r); ok("bad output removed",not os.path.exists(os.path.join(out,"bad.mp4")))
finally:
    import signal;os.killpg(os.getpgid(p.pid),signal.SIGKILL)
print("FAILED: "+", ".join(fails) if fails else "ALL PASS"); sys.exit(1 if fails else 0)
