"""Makes the little splat/model files the tests use. Nothing here is committed; it is rebuilt every run."""
import os, tempfile
import numpy as np
PROPS=['x','y','z','nx','ny','nz','f_dc_0','f_dc_1','f_dc_2','opacity','scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3']
C0=0.28209479177387814
def rows(pts,col,op=0.5,sc=0.05):
    m=len(pts); dc=(np.array(col)-0.5)/C0
    q=np.tile([1,0,0,0],(m,1)); s=np.log(np.full((m,3),sc)); o=np.full((m,1),op)
    return np.concatenate([pts,np.zeros((m,3)),np.tile(dc,(m,1)),o,s,q],1).astype('<f4')
def ply(arr):
    h=("ply\nformat binary_little_endian 1.0\nelement vertex %d\n"%len(arr)+"".join("property float %s\n"%p for p in PROPS)+"end_header\n").encode()
    return h+arr.tobytes()
def tilted(n=12000):
    rng=np.random.default_rng(2)
    g=np.stack([rng.uniform(-3,3,n),rng.uniform(-3,3,n),rng.normal(0,0.02,n)],1)
    pill=np.stack([rng.normal(0,0.15,n//4),rng.normal(0,0.15,n//4),rng.uniform(0,2.5,n//4)],1)
    pts=np.concatenate([g,pill]); a=np.deg2rad(25); R=np.array([[1,0,0],[0,np.cos(a),-np.sin(a)],[0,np.sin(a),np.cos(a)]])
    pts=pts@R.T; col=np.concatenate([np.tile([0.1,0.1,0.1],(n,1)),np.tile([0.9,0.2,0.2],(n//4,1))])
    m=len(pts); dc=(col-0.5)/C0
    return np.concatenate([pts,np.zeros((m,3)),dc,np.full((m,1),2.0),np.log(np.full((m,3),0.06)),np.tile([1,0,0,0],(m,1))],1).astype('<f4')
def blob(n=5000):
    rng=np.random.default_rng(1); v=rng.normal(size=(n,3)); v/=np.linalg.norm(v,axis=1,keepdims=True)
    return rows(v*np.array([2,1.4,1.4]),[0.3,0.7,0.4],op=2.0,sc=0.07)
def make():
    d=tempfile.mkdtemp(prefix="splatbox-fx-"); r=np.random.default_rng(5); n=14000
    A=np.stack([r.uniform(-0.5,0.5,n),r.uniform(-0.5,0.5,n),r.normal(0,0.004,n)],1)
    B=np.stack([r.uniform(-0.5,0.5,n),r.normal(0,0.004,n),r.uniform(-0.5,0.5,n)],1)
    ra,rb=rows(A,[0.9,0.15,0.15]),rows(B,[0.15,0.3,0.95])
    f={}
    for name,arr in (("tilt",tilted()),("blob",blob()),("planeA",ra),("planeB",rb),("planeAB",np.concatenate([ra,rb]))):
        f[name]=os.path.join(d,name+".ply"); open(f[name],"wb").write(ply(arr))
    f["cube"]=os.path.join(d,"cube.obj")
    open(f["cube"],"w").write("v -1 -1 -1\nv 1 -1 -1\nv 1 1 -1\nv -1 1 -1\nv -1 -1 1\nv 1 -1 1\nv 1 1 1\nv -1 1 1\nf 1 2 3 4\nf 5 8 7 6\nf 1 5 6 2\nf 2 6 7 3\nf 3 7 8 4\nf 5 1 4 8\n")
    f["dir"]=d
    return f
