"use strict";
// SHARP (Apple): one photo -> 3D Gaussian splats. Runs on this PC with onnxruntime-node.
// The 1.3 GB model is downloaded once, on first use, into the app's data folder. It is never part of the app or the repo.
// Apple's model licence is research / non-commercial only, so this is for personal use.
const fs = require("fs");
const path = require("path");

const MODEL_URL = "https://huggingface.co/pearsonkyle/Sharp-onnx/resolve/main/sharp_fp16.onnx";
const MODEL_BYTES = 1319661752;
const SIZE = 1536;

function srgb(l) { return l <= 0.0031308 ? l * 12.92 : 1.055 * Math.pow(l, 1 / 2.4) - 0.055; }
const C0 = 1 / Math.sqrt(4 * Math.PI);

// o: {pos[N*3], sc[N*3], q[N*4], col[N*3], op[N]} straight from the model.
// Returns a Buffer holding a binary little-endian .ply the app already reads (x y z f_dc_0-2 opacity scale_0-2 rot_0-3).
// Same maths as the reference inference script, then moved into Splatbox's scene space (Y up, camera on +Z) and centred.
function buildPly(o, opt) {
  opt = opt || {};
  const keepFrac = opt.keep == null ? 0.5 : Math.min(1, Math.max(0.02, opt.keep));
  const focalPx = opt.focalPx || opt.imgW || SIZE, imgW = opt.imgW || SIZE, K = opt.scale || 1.4;
  const N = o.op.length, asp = opt.aspect || 1; // a squashed non-square photo: y was stretched to fit the square
  let zmin = Infinity;
  for (let i = 0; i < N; i++) { const z = o.pos[i * 3 + 2]; if (z < zmin) zmin = z; }
  if (!(zmin > 0)) zmin = 1e-6;
  const sf = 1 / (zmin * (2 * focalPx / imgW));
  // which splats to keep: biggest and most opaque first
  const imp = new Float32Array(N);
  for (let i = 0; i < N; i++) imp[i] = o.sc[i * 3] * o.sc[i * 3 + 1] * o.sc[i * 3 + 2] * o.op[i];
  let keep = Math.max(1, Math.floor(N * keepFrac)), thr = -Infinity;
  if (keep < N) { const s = Float32Array.from(imp).sort(); thr = s[N - keep]; }
  const idx = [];
  for (let i = 0; i < N && idx.length < keep; i++) if (imp[i] >= thr) idx.push(i);
  const n = idx.length;
  // centre on the average depth so the card sits around the origin
  let zs = 0;
  for (let j = 0; j < n; j++) zs += o.pos[idx[j] * 3 + 2] / zmin;
  const zc = zs / n;
  const names = ["x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity", "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"];
  const head = Buffer.from("ply\nformat binary_little_endian 1.0\nelement vertex " + n + "\n" + names.map((p) => "property float " + p).join("\n") + "\nend_header\n", "latin1");
  const out = new Float32Array(n * 14), lk = Math.log(K);
  for (let j = 0; j < n; j++) {
    const i = idx[j], b = j * 14;
    out[b] = o.pos[i * 3] * sf * K;
    out[b + 1] = -o.pos[i * 3 + 1] * sf * K * asp;
    out[b + 2] = -(o.pos[i * 3 + 2] / zmin - zc) * K;
    for (let c = 0; c < 3; c++) out[b + 3 + c] = (srgb(Math.min(1, Math.max(0, o.col[i * 3 + c]))) - 0.5) / C0;
    const a = Math.min(1 - 1e-6, Math.max(1e-6, o.op[i]));
    out[b + 6] = Math.log(a / (1 - a));
    out[b + 7] = Math.log(Math.max(o.sc[i * 3] * sf, 1e-10)) + lk;
    out[b + 8] = Math.log(Math.max(o.sc[i * 3 + 1] * sf, 1e-10)) + lk;
    out[b + 9] = Math.log(Math.max(o.sc[i * 3 + 2] / zmin, 1e-10)) + lk;
    out[b + 10] = o.q[i * 4]; out[b + 11] = o.q[i * 4 + 1]; out[b + 12] = -o.q[i * 4 + 2]; out[b + 13] = -o.q[i * 4 + 3];
  }
  return Buffer.concat([head, Buffer.from(out.buffer)]);
}

function modelPath(app) { return process.env.SPLATBOX_SHARP_MODEL || path.join(app.getPath("userData"), "sharp", "sharp_fp16.onnx"); }
function modelReady(app) {
  try { const s = fs.statSync(modelPath(app)); return process.env.SPLATBOX_SHARP_MODEL ? s.size > 0 : s.size === MODEL_BYTES; } catch (_) { return false; }
}

async function download(app, onProgress, signal) {
  const dest = modelPath(app), tmp = dest + ".part";
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  const res = await fetch(MODEL_URL, { redirect: "follow", signal });
  if (!res.ok || !res.body) throw new Error("The download failed (" + res.status + ").");
  const total = +res.headers.get("content-length") || MODEL_BYTES;
  const ws = fs.createWriteStream(tmp);
  let got = 0, last = 0;
  try {
    for await (const chunk of res.body) {
      if (!ws.write(chunk)) await new Promise((r) => ws.once("drain", r));
      got += chunk.length;
      const now = Date.now();
      if (now - last > 400) { last = now; onProgress(got, total); }
    }
    await new Promise((r, j) => { ws.end((e) => (e ? j(e) : r())); });
  } catch (e) { try { ws.destroy(); fs.unlinkSync(tmp); } catch (_) {} throw e; }
  if (got !== MODEL_BYTES) { try { fs.unlinkSync(tmp); } catch (_) {} throw new Error("The download came through incomplete (" + got + " bytes). Try again."); }
  fs.renameSync(tmp, dest);
  onProgress(got, total);
}

async function makeSession(file) {
  const ort = require("onnxruntime-node");
  const base = { enableMemPattern: false, executionMode: "sequential", graphOptimizationLevel: "all", logSeverityLevel: 3 };
  const tries = process.platform === "win32" ? [["dml", "cpu"], ["cpu"]] : [["cpu"]];
  let last = null;
  for (const eps of tries) {
    try { const s = await ort.InferenceSession.create(file, Object.assign({ executionProviders: eps }, base)); return { ort, session: s, eps: eps[0] }; }
    catch (e) { last = e; }
  }
  throw last;
}

// chw: Float32Array of 3*1536*1536 in 0..1. Resolves to {ply: Buffer, n, eps}
async function run(app, chw, info) {
  if (!modelReady(app)) throw new Error("The SHARP model isn't downloaded yet.");
  if (chw.length !== 3 * SIZE * SIZE) throw new Error("Wrong picture size.");
  const { ort, session, eps } = await makeSession(modelPath(app));
  try {
    const feeds = {
      image: new ort.Tensor("float32", chw, [1, 3, SIZE, SIZE]),
      disparity_factor: new ort.Tensor("float32", Float32Array.of(1), [1])
    };
    const res = await session.run(feeds);
    const names = session.outputNames, v = names.map((k) => res[k].data);
    if (v.length !== 5) throw new Error("This model has an unexpected shape (" + v.length + " outputs).");
    const f = (a) => (a instanceof Float32Array ? a : Float32Array.from(a));
    const ply = buildPly({ pos: f(v[0]), sc: f(v[1]), q: f(v[2]), col: f(v[3]), op: f(v[4]) }, info);
    return { ply, eps, n: v[4].length };
  } finally { try { await session.release(); } catch (_) {} }
}

function register(ipcMain, app, getWin, dialog, TESTING) {
  let busy = false, ctl = null;
  const send = (ch, m) => { const w = getWin(); if (w && !w.isDestroyed()) w.webContents.send(ch, m); };
  ipcMain.handle("sharp:status", () => ({ ready: modelReady(app), bytes: MODEL_BYTES }));
  ipcMain.handle("sharp:download", async () => {
    if (modelReady(app)) return { ok: true };
    if (busy) return { ok: false, error: "Already downloading." };
    if (!TESTING) {
      const r = await dialog.showMessageBox(getWin() || undefined, {
        type: "question", buttons: ["Download (1.3 GB)", "Cancel"], defaultId: 0, cancelId: 1, title: "SHARP model",
        message: "Download the SHARP model?",
        detail: "SHARP turns one photo into a 3D scene. The model is 1.3 GB, comes from Hugging Face, and is saved once on this PC.\n\nApple's licence for the model allows research and personal, non-commercial use only."
      });
      if (r.response !== 0) return { ok: false, cancelled: true };
    }
    busy = true; ctl = new AbortController();
    try { await download(app, (g, t) => send("sharp:progress", { got: g, total: t }), ctl.signal); return { ok: true }; }
    catch (e) { return { ok: false, error: (ctl.signal.aborted ? "Download cancelled." : (e && e.message) || "The download failed.") }; }
    finally { busy = false; ctl = null; }
  });
  ipcMain.handle("sharp:cancel", () => { if (ctl) ctl.abort(); });
  ipcMain.handle("sharp:run", async (ev, chw, info) => {
    if (busy) return { ok: false, error: "Busy." };
    busy = true;
    try {
      const r = await run(app, chw instanceof Float32Array ? chw : new Float32Array(chw.buffer || chw), info || {});
      return { ok: true, ply: r.ply.buffer.slice(r.ply.byteOffset, r.ply.byteOffset + r.ply.length), eps: r.eps, n: r.n };
    } catch (e) {
      const m = (e && e.message) || "SHARP failed.";
      return { ok: false, error: /alloc|memory/i.test(m) ? "SHARP ran out of memory. It needs roughly 8 GB free on a CPU. Close other apps and try again. (" + m + ")" : m };
    } finally { busy = false; }
  });
}

module.exports = { buildPly, register, MODEL_BYTES, SIZE };
