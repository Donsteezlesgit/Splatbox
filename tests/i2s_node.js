// V057 image to splat: the desktop side (desktop/i2s.js), run under node with a stand-in model and recorded commands.
const fs = require("fs"), path = require("path"), os = require("os");
const { create } = require("../desktop/i2s");
let pass = 0, fails = [];
function ok(c, m) { if (c) pass++; else { fails.push(m); console.log("FAIL " + m); } }
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "i2s-"));
const logOf = (d) => { try { return fs.readFileSync(path.join(d, "image-to-splat", "image-to-splat.log"), "utf8"); } catch (e) { return ""; } };
const venvPy = (d) => path.join(d, "image-to-splat", "venv", "bin", "python");

function fakeInstall(d) {
  const root = path.join(d, "image-to-splat");
  fs.mkdirSync(path.dirname(venvPy(d)), { recursive: true });
  fs.writeFileSync(venvPy(d), "#!/bin/sh\nexec python3 \"$@\"\n"); fs.chmodSync(venvPy(d), 0o755);
  fs.mkdirSync(path.join(root, "triposplat"), { recursive: true });
  fs.writeFileSync(path.join(root, "triposplat", "triposplat.py"), "# fake");
  fs.writeFileSync(path.join(root, "setup.json"), JSON.stringify({ ok: true }));
}

(async () => {
  // 1. not set up yet
  let d = tmp(), m = create({ dataDir: d, platform: "linux" });
  ok(m.status().installed === false, "starts not set up");
  let e = await m.generate({ name: "a.jpg", bytes: [1, 2, 3] }).catch((x) => x);
  ok(e && e.code === "notsetup", "generate before setup says notsetup");

  // 2. set up with recorded commands: right order, right options, a log, a marker
  d = tmp();
  const cmds = [];
  const hook = (cmd, args, o, log) => {
    const line = [cmd].concat(args).join(" "); cmds.push(line); log("$ " + line);
    if (args.indexOf("--version") >= 0) return Promise.resolve({ code: 0, out: "Python 3.12.4\n" });
    if (cmd === "nvidia-smi") return Promise.resolve({ code: 0, out: "NVIDIA GeForce RTX 3070 Ti, 8192 MiB, 560.94\n" });
    if (args.indexOf("venv") >= 0) { fs.mkdirSync(path.dirname(venvPy(d)), { recursive: true }); fs.writeFileSync(venvPy(d), "x"); }
    if (/fetch_repo/.test(line)) { fs.mkdirSync(path.join(d, "image-to-splat", "triposplat"), { recursive: true }); fs.writeFileSync(path.join(d, "image-to-splat", "triposplat", "triposplat.py"), "#"); }
    return Promise.resolve({ code: 0, out: "" });
  };
  m = create({ dataDir: d, platform: "linux", exec: hook });
  const prog = [];
  await m.setup((p) => prog.push(p.stage));
  ok(JSON.stringify(prog) === JSON.stringify(["python", "venv", "torch", "source", "weights"]), "setup reports 5 stages in order: " + prog);
  ok(cmds.some((c) => /pip install .*torch torchvision --index-url https:\/\/download\.pytorch\.org\/whl\/cu124/.test(c)), "installs CUDA torch from the pytorch index");
  ok(cmds.some((c) => /fetch_repo\.py d8db9e018b41/.test(c)), "downloads the pinned TripoSplat commit");
  ok(cmds.some((c) => /get_weights\.py/.test(c)), "downloads the weights");
  ok(m.status().installed === true, "installed after setup");
  const L = logOf(d);
  ok(/RTX 3070 Ti/.test(L) && /Using Python 3\.12\.4/.test(L) && /Set up finished/.test(L), "log records the GPU, the Python and the end");
  ok(fs.existsSync(path.join(d, "image-to-splat", "py", "run.py")), "helper scripts copied next to the environment");

  // 3. no Python: clear message, logged
  d = tmp();
  m = create({ dataDir: d, platform: "linux", exec: (c, a, o, log) => { log("$ " + c); return Promise.resolve({ code: 1, out: "" }); } });
  e = await m.setup().catch((x) => x);
  ok(e && e.code === "nopython" && /python\.org/.test(e.message), "no Python gives nopython with where to get it");
  ok(/SET UP FAILED \[nopython\]/.test(logOf(d)), "setup failure is in the log");

  // 3b. Python too old
  d = tmp();
  m = create({ dataDir: d, platform: "linux", exec: (c, a, o, log) => Promise.resolve({ code: 0, out: "Python 3.8.10\n" }) });
  e = await m.setup().catch((x) => x);
  ok(e && e.code === "nopython" && /too old/.test(logOf(d)), "Python 3.8 is refused and logged as too old");

  // 4. a step fails (torch): setup error, log says so, not marked installed, can retry (busy cleared)
  d = tmp();
  m = create({ dataDir: d, platform: "linux", exec: (c, a, o, log) => {
    if (a.indexOf("--version") >= 0) return Promise.resolve({ code: 0, out: "Python 3.11.0\n" });
    if (a.indexOf("venv") >= 0) { fs.mkdirSync(path.dirname(venvPy(d)), { recursive: true }); fs.writeFileSync(venvPy(d), "x"); }
    if (a.indexOf("torch") >= 0) { log("ERROR: No matching distribution found for torch"); return Promise.resolve({ code: 1, out: "" }); }
    return Promise.resolve({ code: 0, out: "" });
  } });
  e = await m.setup().catch((x) => x);
  ok(e && e.code === "setup" && /PyTorch/.test(e.message) && /error log/.test(e.message), "torch failure: message points at the error log");
  ok(/No matching distribution/.test(logOf(d)), "pip's own error text is in the log");
  ok(m.status().installed === false && m.status().busy === "", "a failed setup leaves it not installed and not stuck busy");

  // 5. real child process with the stand-in model
  d = tmp(); fakeInstall(d);
  m = create({ dataDir: d, platform: "linux", runScript: path.join(__dirname, "i2s_fake_run.py") });
  ok(m.status().installed === true, "status sees a finished install");
  const ev = [];
  process.env.I2S_FAKE = "ok";
  let r = await m.generate({ name: "My Photo.JPG", bytes: Buffer.from([255, 216, 255]), count: 100000, steps: 6 }, (p) => ev.push(p));
  ok(r && fs.existsSync(r.plyPath), "generate returns a .ply that exists");
  const ply = fs.readFileSync(r.plyPath);
  ok(ply.slice(0, 3).toString() === "ply" && /element vertex 64/.test(ply.slice(0, 200).toString()), "the .ply has a valid header");
  ok(r.count === 100000 && r.gpu === "Fake GPU 8 GB", "count rounded to 32s and GPU name reported: " + r.count + " " + r.gpu);
  ok(ev.filter((p) => p.n === 6).length === 6 && ev.some((p) => p.stage === "loading"), "progress events: 6 steps and a loading stage");
  ok(fs.readdirSync(path.join(d, "image-to-splat", "work")).some((f) => /^in_.*\.jpg$/.test(f)), "the photo was written to the work folder as .jpg");
  ok(/Photo: My Photo\.JPG/.test(logOf(d)) && /Finished in/.test(logOf(d)), "log has the photo, the settings and the finish");

  // 6. out of memory: code oom, traceback in the log
  process.env.I2S_FAKE = "oom";
  e = await m.generate({ name: "a.png", bytes: [1], steps: 4 }).catch((x) => x);
  ok(e && e.code === "oom" && /ran out of memory/.test(e.message), "out of memory is reported as oom");
  ok(/CUDA out of memory/.test(logOf(d)) && /MAKE FAILED \[oom\]/.test(logOf(d)), "the traceback and the failure line are in the log");
  ok(m.status().busy === "", "not stuck busy after a failure");

  // 7. any other crash: code failed, the real traceback is kept
  process.env.I2S_FAKE = "boom";
  e = await m.generate({ name: "a.png", bytes: [1], steps: 4 }).catch((x) => x);
  ok(e && e.code === "failed" && /shape mismatch/.test(e.message) && /FAKE-TRACE/.test(logOf(d)), "a crash keeps its traceback in the log");

  // 8. exits 0 but wrote nothing: still an error, not a silent success
  process.env.I2S_FAKE = "silent";
  e = await m.generate({ name: "a.png", bytes: [1], steps: 4 }).catch((x) => x);
  ok(e && e.code === "failed" && /without making a file/.test(e.message), "no file means an error");

  // 9. cancel kills the child and says cancelled; a second job at the same time is refused
  process.env.I2S_FAKE = "hang";
  const t0 = Date.now();
  const pr = m.generate({ name: "a.png", bytes: [1], steps: 4 }).catch((x) => x);
  await new Promise((s) => setTimeout(s, 700));
  const e2 = await m.generate({ name: "b.png", bytes: [1] }).catch((x) => x);
  ok(e2 && e2.code === "busy", "a second job while one runs is refused");
  ok(m.cancel() === true, "cancel finds a running job");
  e = await pr;
  ok(e && e.code === "cancelled" && Date.now() - t0 < 10000, "cancelled quickly with code cancelled");
  ok(/Cancel pressed/.test(logOf(d)), "cancel is logged");
  ok(m.cancel() === false, "cancel with nothing running does nothing");
  ok(m.tail(5).split("\n").length <= 6 && m.tail(5).length > 0, "tail returns the last lines");

  delete process.env.I2S_FAKE;
  console.log((fails.length ? "FAILED " : "OK ") + pass + " passed, " + fails.length + " failed");
  process.exit(fails.length ? 1 : 0);
})();
