// Image to splat (V057): one photo -> a 3D Gaussian splat, made on this PC's NVIDIA graphics card by TripoSplat (MIT licence).
// This file runs in the desktop shell. It sets up a private Python environment, runs the model, and writes everything it does
// (and every error, with the full Python traceback) to image-to-splat.log so a failure can be read afterwards.
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const TRIPOSPLAT_SHA = "d8db9e018b413dd9c4a9fe22463781bf98e8e68d"; // pinned: the version this was written against
const TORCH_INDEX = "https://download.pytorch.org/whl/cu124";
const PIP_PACKAGES = ["numpy", "safetensors", "pillow", "tqdm", "huggingface_hub"];
const MAX_LOG = 2 * 1024 * 1024;

function fail(code, message) {
  const e = new Error(message);
  e.code = code;
  return e;
}

// opt: dataDir (required), helperDir (where the .py files are), pythonCandidates, exec (test hook), runScript (test hook), log
function create(opt) {
  const dir = path.join(opt.dataDir, "image-to-splat");
  const logFile = path.join(dir, "image-to-splat.log");
  const venv = path.join(dir, "venv");
  const repo = path.join(dir, "triposplat");
  const ckpts = path.join(dir, "ckpts");
  const work = path.join(dir, "work");
  const pyDir = path.join(dir, "py");
  const marker = path.join(dir, "setup.json");
  const helperDir = opt.helperDir || path.join(__dirname, "i2s_py");
  const isWin = (opt.platform || process.platform) === "win32";
  const venvPy = isWin ? path.join(venv, "Scripts", "python.exe") : path.join(venv, "bin", "python");
  const candidates = opt.pythonCandidates || (isWin
    ? [["py", "-3.12"], ["py", "-3.11"], ["py", "-3.13"], ["py", "-3.10"], ["py", "-3"], ["python"], ["python3"]]
    : [["python3.12"], ["python3.11"], ["python3.13"], ["python3.10"], ["python3"], ["python"]]);
  let seenOutside = ""; // a Python that was found but PyTorch can't use (too old or too new)
  let busy = "";
  let child = null;
  let cancelled = false;
  let stage = "";

  fs.mkdirSync(dir, { recursive: true });

  function log(msg) {
    try {
      try {
        if (fs.statSync(logFile).size > MAX_LOG) fs.renameSync(logFile, logFile + ".old");
      } catch (e) {}
      const lines = String(msg).replace(/\r/g, "").split("\n");
      const stamp = new Date().toISOString();
      fs.appendFileSync(logFile, lines.map((l) => stamp + "  " + l).join("\n") + "\n");
    } catch (e) {}
    try { if (opt.log) opt.log(msg); } catch (e) {}
  }

  // run one command, copy every line it prints into the log, resolve with the exit code
  function exec(cmd, args, o) {
    o = o || {};
    if (opt.exec) return opt.exec(cmd, args, o, log);
    return new Promise((resolve) => {
      log("$ " + [cmd].concat(args).join(" "));
      let p;
      try {
        p = spawn(cmd, args, { cwd: o.cwd, env: Object.assign({}, process.env, o.env || {}), windowsHide: true });
      } catch (e) {
        log("could not start: " + e.message);
        resolve({ code: -1, out: "" });
        return;
      }
      if (o.track) child = p;
      let out = "", partial = "";
      const feed = (buf) => {
        const t = buf.toString();
        out += t;
        if (out.length > 200000) out = out.slice(-100000);
        if (o.onData) { o.onData(t); return; }
        partial += t;
        const k = partial.lastIndexOf("\n");
        if (k >= 0) { log(partial.slice(0, k)); partial = partial.slice(k + 1); }
      };
      p.stdout.on("data", feed);
      p.stderr.on("data", feed);
      p.on("error", (e) => { log("could not start: " + e.message); resolve({ code: -1, out }); });
      p.on("close", (code) => { if (o.track) child = null; if (partial.trim()) log(partial); log("exit code " + code); resolve({ code, out }); });
    });
  }

  function copyHelpers() {
    fs.mkdirSync(pyDir, { recursive: true });
    for (const f of ["run.py", "fetch_repo.py", "get_weights.py"]) {
      const from = path.join(helperDir, f);
      if (fs.existsSync(from)) fs.writeFileSync(path.join(pyDir, f), fs.readFileSync(from));
    }
    if (opt.runScript) fs.writeFileSync(path.join(pyDir, "run.py"), fs.readFileSync(opt.runScript));
  }

  async function findPython() {
    seenOutside = "";
    for (const c of candidates) {
      const r = await exec(c[0], c.slice(1).concat(["--version"]), {});
      const m = /Python (\d+)\.(\d+)\.(\d+)/.exec(r.out || "");
      if (r.code === 0 && m) {
        const maj = +m[1], min = +m[2];
        if (maj === 3 && min >= 10 && min <= 13) return { cmd: c[0], args: c.slice(1), version: m[1] + "." + m[2] + "." + m[3] };
        log("found Python " + m[1] + "." + m[2] + "." + m[3] + " but PyTorch needs 3.10 to 3.13 (3.12 is best)");
        if (!seenOutside) seenOutside = m[1] + "." + m[2] + "." + m[3];
      }
    }
    return null;
  }

  async function gpuInfo() {
    const r = await exec("nvidia-smi", ["--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"], {});
    return r.code === 0 ? String(r.out).trim() : "";
  }

  function installed() {
    try {
      const j = JSON.parse(fs.readFileSync(marker, "utf8"));
      return !!(j && j.ok && fs.existsSync(venvPy) && fs.existsSync(path.join(repo, "triposplat.py")));
    } catch (e) { return false; }
  }

  function status() {
    let info = null;
    try { info = JSON.parse(fs.readFileSync(marker, "utf8")); } catch (e) {}
    return { installed: installed(), busy, stage, logPath: logFile, setup: info };
  }

  function tail(n) {
    try {
      const t = fs.readFileSync(logFile, "utf8").split("\n");
      return t.slice(-(n || 60)).join("\n");
    } catch (e) { return ""; }
  }

  function step(on, name, text, i, n) {
    stage = name;
    log("== " + text);
    if (on) { try { on({ stage: name, text, i, n }); } catch (e) {} }
  }

  async function setup(on) {
    if (busy) throw fail("busy", "Something is already running (" + busy + ").");
    busy = "setup";
    cancelled = false;
    const t0 = Date.now();
    try {
      log("---------- SET UP image to splat ----------");
      log("Splatbox desktop, platform " + process.platform + " " + process.arch);
      const total = 5;
      step(on, "python", "Looking for Python 3.12 (3.10 to 3.13 also work)", 1, total);
      const py = await findPython();
      if (!py) {
        if (seenOutside) throw fail("pyversion", "Found Python " + seenOutside + ", but PyTorch doesn't work with it yet. Install Python 3.12 from python.org (it can sit next to your newer one; tick \"Add python.exe to PATH\"), then press Set up again.");
        throw fail("nopython", "Python 3.10 to 3.13 wasn't found. Install Python 3.12 from python.org (tick \"Add python.exe to PATH\"), then press Set up again.");
      }
      log("Using Python " + py.version);
      const gpu = await gpuInfo();
      log("Graphics card: " + (gpu || "nvidia-smi not found (no NVIDIA driver?)"));
      if (!gpu) log("WARNING: no NVIDIA graphics card was reported. Setup carries on, but running will probably fail.");
      copyHelpers();

      step(on, "venv", "Making a private Python environment", 2, total);
      fs.rmSync(venv, { recursive: true, force: true });
      let r = await exec(py.cmd, py.args.concat(["-m", "venv", venv]), {});
      if (r.code !== 0) throw fail("setup", "Couldn't make the Python environment. See the error log.");

      step(on, "torch", "Installing PyTorch with CUDA (about 2.5 GB, a few minutes)", 3, total);
      r = await exec(venvPy, ["-m", "pip", "install", "--no-input", "--disable-pip-version-check", "torch", "torchvision", "--index-url", TORCH_INDEX], {});
      if (r.code !== 0) throw fail("setup", "Installing PyTorch failed. See the error log.");
      r = await exec(venvPy, ["-m", "pip", "install", "--no-input", "--disable-pip-version-check"].concat(PIP_PACKAGES), {});
      if (r.code !== 0) throw fail("setup", "Installing the helper packages failed. See the error log.");

      step(on, "source", "Downloading the TripoSplat code", 4, total);
      r = await exec(venvPy, [path.join(pyDir, "fetch_repo.py"), TRIPOSPLAT_SHA, repo], {});
      if (r.code !== 0) throw fail("setup", "Couldn't download the TripoSplat code from GitHub. See the error log.");

      step(on, "weights", "Downloading the model files (about 3.8 GB, once)", 5, total);
      r = await exec(venvPy, [path.join(pyDir, "get_weights.py"), ckpts], {});
      if (r.code !== 0) throw fail("setup", "Couldn't download the model files from Hugging Face. See the error log.");

      fs.writeFileSync(marker, JSON.stringify({ ok: true, python: py.version, gpu, sha: TRIPOSPLAT_SHA, when: new Date().toISOString() }));
      log("Set up finished in " + Math.round((Date.now() - t0) / 1000) + " s");
      stage = "";
      return status();
    } catch (e) {
      log("SET UP FAILED [" + (e.code || "error") + "]: " + e.message);
      stage = "";
      throw e;
    } finally {
      busy = "";
    }
  }

  // generate({name, bytes (Buffer or Uint8Array), count, steps, seed}, onProgress) -> {plyPath, count, seconds, gpu}
  async function generate(o, on) {
    if (busy) throw fail("busy", "Something is already running (" + busy + ").");
    if (!installed()) throw fail("notsetup", "Image to splat isn't set up yet. Press Set up first.");
    busy = "generate";
    cancelled = false;
    const t0 = Date.now();
    try {
      log("---------- MAKE a splat ----------");
      copyHelpers();
      fs.mkdirSync(work, { recursive: true });
      const id = Date.now().toString(36);
      const em = /\.(png|webp|jpe?g)$/i.exec(o.name || "");
      const ext = em ? em[1].toLowerCase() : "jpg";
      const img = path.join(work, "in_" + id + "." + ext);
      const out = path.join(work, "out_" + id + ".ply");
      fs.writeFileSync(img, Buffer.from(o.bytes));
      const count = Math.max(32768, Math.min(262144, Math.round((+o.count || 131072) / 32) * 32));
      const steps = Math.max(4, Math.min(50, Math.round(+o.steps || 20)));
      log("Photo: " + (o.name || "photo") + " (" + Buffer.from(o.bytes).length + " bytes), " + count + " splats, " + steps + " steps, seed " + (o.seed || 42));
      stage = "starting";
      if (on) on({ stage: "starting", text: "Starting" });
      let done = null, err = null, gpu = "";
      let pending = "";
      const onData = (t) => {
        pending += t;
        let k;
        while ((k = pending.indexOf("\n")) >= 0) {
          const line = pending.slice(0, k).replace(/\r$/, "");
          pending = pending.slice(k + 1);
          if (line.indexOf("@@") === 0) {
            let j = null;
            try { j = JSON.parse(line.slice(2)); } catch (e) {}
            if (!j) { log(line); continue; }
            if (j.event === "step") { if (on) on({ stage: "running", text: "Making the splat", i: j.i, n: j.n }); }
            else if (j.event === "stage") { stage = j.stage; log("== " + j.text); if (on) on({ stage: j.stage, text: j.text }); }
            else if (j.event === "env") { gpu = (j.gpu || "") + (j.vram_gb ? " " + j.vram_gb + " GB" : ""); log("env " + JSON.stringify(j)); }
            else if (j.event === "done") { done = j; log("done " + JSON.stringify(j)); }
            else if (j.event === "error") { err = j; log("error " + JSON.stringify(j)); }
            else log(line);
          } else if (line) log(line);
        }
      };
      const r = await exec(venvPy, [path.join(pyDir, "run.py"), "--repo", repo, "--ckpts", ckpts, "--image", img, "--out", out,
        "--count", String(count), "--steps", String(steps), "--seed", String(o.seed || 42)], { cwd: repo, onData, track: true });
      if (pending.trim()) onData("\n");
      if (cancelled) throw fail("cancelled", "Cancelled.");
      if (r.code !== 0 || err || !done || !fs.existsSync(out)) {
        const kind = (err && err.kind) || "failed";
        const msg = (err && err.message) || "Image to splat stopped without making a file (exit code " + r.code + ").";
        throw fail(kind, msg);
      }
      const secs = Math.round((Date.now() - t0) / 100) / 10;
      log("Finished in " + secs + " s, " + fs.statSync(out).size + " bytes");
      stage = "";
      return { plyPath: out, count, seconds: secs, gpu };
    } catch (e) {
      log("MAKE FAILED [" + (e.code || "error") + "]: " + e.message);
      stage = "";
      throw e;
    } finally {
      busy = "";
      child = null;
    }
  }

  function cancel() {
    cancelled = true;
    if (child) {
      log("Cancel pressed: stopping the helper");
      try { child.kill(); } catch (e) {}
      return true;
    }
    return false;
  }

  function clearWork() {
    try { fs.rmSync(work, { recursive: true, force: true }); } catch (e) {}
  }

  return { status, setup, generate, cancel, tail, log, logPath: () => logFile, installed, clearWork, dir };
}

module.exports = { create, TRIPOSPLAT_SHA, TORCH_INDEX };
