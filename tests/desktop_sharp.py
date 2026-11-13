"""V033: SHARP plumbing. (1) buildPly matches Apple-reference maths. (2) Electron end to end with a stand-in ONNX model:
status -> run -> PLY the app can load. Not in run.py (needs Electron + xvfb)."""
import os, sys, json, subprocess, struct, tempfile, math, time, signal
import numpy as np
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","desktop")
res=[]
def ok(n,c,d=""): res.append((n,bool(c),d)); print(("PASS " if c else "FAIL ")+n+("  -> "+str(d) if d!="" and not c else ""),flush=True)
def lin2srgb(l): return np.where(l<=0.0031308,l*12.92,1.055*np.power(np.maximum(l,1e-9),1/2.4)-0.055)
rng=np.random.default_rng(3); N=5000
pos=np.stack([rng.uniform(-.6,.6,N),rng.uniform(-.4,.4,N),rng.uniform(.5,.7,N)],1).astype(np.float32)
sc=rng.uniform(.001,.02,(N,3)).astype(np.float32); q=rng.normal(size=(N,4)).astype(np.float32); q/=np.linalg.norm(q,axis=1,keepdims=True)
col=rng.uniform(0,1,(N,3)).astype(np.float32); op=rng.uniform(.05,.99,N).astype(np.float32)
tmp=tempfile.mkdtemp()
for k,v in dict(pos=pos,sc=sc,q=q,col=col,op=op).items(): v.tofile(os.path.join(tmp,k+".bin"))
js=f"""const fs=require('fs');const {{buildPly}}=require({json.dumps(os.path.join(D,'sharp.js'))});
const rd=(n)=>{{const b=fs.readFileSync({json.dumps(tmp)}+'/'+n+'.bin');return new Float32Array(b.buffer,b.byteOffset,b.length/4)}};
const o={{pos:rd('pos'),sc:rd('sc'),q:rd('q'),col:rd('col'),op:rd('op')}};
fs.writeFileSync({json.dumps(tmp)}+'/full.ply',buildPly(o,{{keep:1,scale:1,focalPx:1000,imgW:1000}}));
fs.writeFileSync({json.dumps(tmp)}+'/half.ply',buildPly(o,{{keep:0.5,scale:1,focalPx:1000,imgW:1000}}));"""
subprocess.run(["node","-e",js],check=True)
def readply(p):
    b=open(p,"rb").read(); e=b.index(b"end_header\n")+11; n=int(b[:e].split(b"element vertex ")[1].split()[0])
    return np.frombuffer(b[e:e+n*56],dtype="<f4").reshape(n,14),b[:e].count(b"property float")
v,np_=readply(os.path.join(tmp,"full.ply"))
ok("full PLY has every splat and 14 properties",v.shape==(N,14) and np_==14,v.shape)
zmin=pos[:,2].min(); sf=1/(zmin*2.0); z=pos[:,2]/zmin; zc=z.mean()
ok("x matches the reference",np.allclose(v[:,0],pos[:,0]*sf,atol=1e-5))
ok("y is flipped to Y-up",np.allclose(v[:,1],-pos[:,1]*sf,atol=1e-5))
ok("z is depth, centred, flipped toward +Z for near",np.allclose(v[:,2],-(z-zc),atol=1e-5))
ref=(lin2srgb(col)-0.5)/(1/math.sqrt(4*math.pi))
ok("colour is linear->sRGB->SH like the reference",np.allclose(v[:,3:6],ref,atol=2e-4),float(np.abs(v[:,3:6]-ref).max()))
ok("opacity is the inverse sigmoid",np.allclose(v[:,6],np.log(op/(1-op)),atol=1e-3))
ok("scales are logs, depth scale uses 1/zmin",np.allclose(v[:,7],np.log(sc[:,0]*sf),atol=1e-4) and np.allclose(v[:,9],np.log(sc[:,2]/zmin),atol=1e-4))
ok("rotation is kept with y and z flipped",np.allclose(v[:,10],q[:,0]) and np.allclose(v[:,12],-q[:,2]) and np.allclose(v[:,13],-q[:,3]))
h,_=readply(os.path.join(tmp,"half.ply")); imp=sc.prod(1)*op
ok("half keeps the biggest/most opaque half",abs(len(h)-N//2)<=2 and imp[np.argsort(-imp)[:N//2]].min()>=np.sort(imp)[N//2-1]-1e-12,len(h))
# ---- stand-in model + Electron
import onnx
from onnx import helper, TensorProto as T, numpy_helper
M=1000
outs=[("p",pos[:M],3),("s",sc[:M],3),("r",q[:M],4),("c",col[:M],3),("o",op[:M].reshape(1,M),0)]
nodes=[];vi=[];
for n_,arr,k in outs:
    a=arr.reshape(1,M,k) if k else arr
    nodes.append(helper.make_node("Constant",[],[n_],value=numpy_helper.from_array(a.astype(np.float32))))
    vi.append(helper.make_tensor_value_info(n_,T.FLOAT,list(a.shape)))
g=helper.make_graph(nodes,"stub",[helper.make_tensor_value_info("image",T.FLOAT,[1,3,1536,1536]),helper.make_tensor_value_info("disparity_factor",T.FLOAT,[1])],vi)
m=helper.make_model(g,opset_imports=[helper.make_opsetid("",17)]); m.ir_version=8
stub=os.path.join(tmp,"stub.onnx"); onnx.save(m,stub)
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright
env=dict(os.environ,SPLATBOX_TEST="1",SPLATBOX_SHARP_MODEL=stub)
pr=subprocess.Popen(["xvfb-run","-a",D+"/node_modules/.bin/electron",D,"--no-sandbox","--use-angle=swiftshader","--enable-unsafe-swiftshader","--remote-debugging-port=9335"],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
try:
    with sync_playwright() as pw:
        b=None
        for _ in range(60):
            try: b=pw.chromium.connect_over_cdp("http://127.0.0.1:9335"); break
            except Exception: time.sleep(0.5)
        assert b,"no electron"
        pg=None
        for _ in range(60):
            for c in b.contexts:
                for x in c.pages:
                    if x.url.startswith("app://"): pg=x
            if pg: break
            time.sleep(0.5)
        assert pg,"no app page"; pg.wait_for_timeout(1500)
        st=pg.evaluate("()=>window.splatboxDesktop.sharp.status()")
        ok("status says the model is ready",st.get("ready") is True,st)
        r=pg.evaluate("""async()=>{const S=window.splatboxDesktop.sharp;const r=await S.run(new Float32Array(3*1536*1536),{focalPx:1536,imgW:1536});
          if(!r.ok)return {ok:false,error:r.error};const u=new Uint8Array(r.ply);
          let s='';for(let i=0;i<u.length;i+=8192)s+=String.fromCharCode.apply(null,u.subarray(i,i+8192));
          return {ok:true,len:u.length,eps:r.eps,n:r.n,b64:btoa(s),head:new TextDecoder().decode(u.slice(0,120))}}""")
        ok("running the stand-in model returns a PLY",r.get("ok") is True,r)
        import base64
        pb=base64.b64decode(r.get("b64","")); e=pb.index(b"end_header\n")+11
        ok("the PLY is exactly header + 500 x 14 floats",len(pb)==e+500*56 and pb.count(b"property float")==14,len(pb))
        ok("onnxruntime ran on the CPU provider here",r.get("eps")=="cpu",r.get("eps"))
        ok("the model's 1000 splats were halved to 500",("element vertex 500" in r.get("head","")) and r.get("n")==1000,r.get("head"))
        bad=pg.evaluate("""async()=>{const r=await window.splatboxDesktop.sharp.run(new Float32Array(10),{});return r}""")
        ok("a wrong-sized picture gives a clear error",bad.get("ok") is False and "size" in bad.get("error",""),bad)
        b.close()
finally:
    try: os.killpg(os.getpgid(pr.pid),signal.SIGKILL)
    except Exception: pass
print("done",sum(1 for _,c,_ in res if c),"passed",sum(1 for _,c,_ in res if not c),"failed")
sys.exit(0 if all(c for _,c,_ in res) else 1)
