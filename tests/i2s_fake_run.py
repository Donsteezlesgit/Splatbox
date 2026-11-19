"""Stand-in for desktop/i2s_py/run.py: no model, no GPU. Writes a real-format Gaussian .ply (the same 14 properties TripoSplat writes)."""
import argparse, json, os, struct, sys, time

def emit(**k):
    print("@@" + json.dumps(k), flush=True)

ap = argparse.ArgumentParser()
for k in ("repo", "ckpts", "image", "out"):
    ap.add_argument("--" + k)
ap.add_argument("--count", type=int); ap.add_argument("--steps", type=int); ap.add_argument("--seed", type=int)
a = ap.parse_args()
mode = os.environ.get("I2S_FAKE", "ok")
emit(event="env", python="3.12", torch="2.6", cuda=True, gpu="Fake GPU", vram_gb=8.0)
emit(event="stage", stage="loading", text="Loading the model into the graphics card")
if mode == "hang":
    time.sleep(30)
if mode == "oom":
    print("Traceback (most recent call last):\n  File \"x.py\", line 1\ntorch.OutOfMemoryError: CUDA out of memory", file=sys.stderr, flush=True)
    emit(event="error", kind="oom", message="The graphics card ran out of memory.")
    sys.exit(4)
if mode == "boom":
    print("Traceback (most recent call last):\n  File \"model.py\", line 7, in forward\nRuntimeError: shape mismatch FAKE-TRACE", file=sys.stderr, flush=True)
    emit(event="error", kind="failed", message="RuntimeError: shape mismatch")
    sys.exit(1)
if mode == "silent":
    sys.exit(0)
for i in range(1, a.steps + 1):
    emit(event="step", i=i, n=a.steps)
n = 64
names = ["x","y","z","nx","ny","nz","f_dc_0","f_dc_1","f_dc_2","opacity","scale_0","scale_1","scale_2","rot_0","rot_1","rot_2","rot_3"]
hdr = "ply\nformat binary_little_endian 1.0\nelement vertex %d\n" % n + "".join("property float %s\n" % k for k in names) + "end_header\n"
with open(a.out, "wb") as f:
    f.write(hdr.encode())
    for i in range(n):
        f.write(struct.pack("<17f", (i % 8) * 0.1, (i // 8) * 0.1, 0.0, 0, 0, 0, 0.5, 0.2, 0.1, 1.0, -3.0, -3.0, -3.0, 1, 0, 0, 0))
emit(event="done", ply=a.out, prepared="", seconds=0.1, peak_gb=1.0)
