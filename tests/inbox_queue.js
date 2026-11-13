// Queue logic of the Splatbox inbox (desktop/inbox.js), driven with a fake clock and real temp folders.
// Prints PASS/FAIL lines; tests/test_inbox.py runs this and reports them with the rest of the suite.
"use strict";
const fs = require("fs"), os = require("os"), path = require("path"), crypto = require("crypto");
const { create, parseName, MAX_STARTS } = require("../desktop/inbox.js");
let bad = 0;
function ok(name, c, d) { if (c) console.log("PASS " + name); else { bad++; console.log("FAIL " + name + (d !== undefined ? "  -> " + JSON.stringify(d) : "")); } }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const JPG = (seed) => Buffer.concat([Buffer.from([0xff, 0xd8, 0xff, 0xe0]), Buffer.from("splatbox-test-" + seed + "-padding-padding")]);
function hashDir(d) { const h = crypto.createHash("sha1"); fs.readdirSync(d).filter((f) => /\.(jpg|png|webp|heic)$/i.test(f)).sort().forEach((f) => { h.update(f); h.update(fs.readFileSync(path.join(d, f))); }); return h.digest("hex"); }

function rig(opts) {
  opts = opts || {};
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "sbx-inbox-"));
  const inboxDir = path.join(root, "Inbox"), dataDir = path.join(root, "data");
  fs.mkdirSync(inboxDir, { recursive: true }); fs.mkdirSync(dataDir, { recursive: true });
  fs.writeFileSync(path.join(dataDir, "inbox-config.json"), JSON.stringify({ dir: inboxDir, enabled: true, quality: "", startWithWindows: false }));
  const R = { root, inboxDir, dataDir, t: 1700000000000, sent: [], notes: [], power: 0, aborted: [], free: opts.free == null ? 50e9 : opts.free };
  R.mk = () => create({ dataDir, now: () => R.t, stableMs: 3 * 60000, stallMs: 30 * 60000, pollMs: 1e9, send: (j) => R.sent.push(j), notify: (t, b) => R.notes.push(t + " | " + b), power: { start() { R.power++; }, stop() { R.power--; } }, freeBytes: () => Promise.resolve(R.free), abort: (n) => R.aborted.push(n), log: () => {} });
  R.ib = R.mk();
  R.folder = (name, n, extra) => { const d = path.join(inboxDir, name); fs.mkdirSync(d, { recursive: true }); for (let i = 0; i < n; i++) fs.writeFileSync(path.join(d, "IMG_" + String(i).padStart(3, "0") + ".jpg"), JPG(name + i)); if (extra) extra(d); return d; };
  R.st = (name) => { try { return fs.readFileSync(path.join(inboxDir, name, "STATUS.txt"), "utf8"); } catch (e) { return ""; } };
  R.line = (name) => ((/^Status: (.*?)\r?$/m.exec(R.st(name))) || [])[1];
  R.adv = async (ms) => { R.t += ms; await R.ib.scan(); await sleep(5); };
  return R;
}

(async function () {
  /* ---- names ---- */
  ok("a quality can be put in the folder name", JSON.stringify(parseName("statue [high]")) === JSON.stringify({ project: "statue", quality: "high" }));
  ok("a folder name without one uses the default", parseName("old church").quality === "" && parseName("old church").project === "old church");
  ok("an unknown quality is not treated as one", parseName("x [turbo]").project === "x [turbo]");

  /* ---- slow arrival: never starts on a half-synced folder ---- */
  let R = rig(); await R.ib.start(); await R.ib.hello({ ready: true });
  R.folder("statue", 5); await R.adv(1000);
  ok("a new folder is picked up and waits", R.line("statue") === "Waiting for the photos to finish syncing", R.st("statue"));
  await R.adv(2 * 60000);
  fs.writeFileSync(path.join(R.inboxDir, "statue", "IMG_005.jpg"), JPG("late")); fs.utimesSync(path.join(R.inboxDir, "statue", "IMG_005.jpg"), new Date(R.t), new Date(R.t));
  await R.adv(2 * 60000);
  ok("a photo arriving late restarts the wait", R.sent.length === 0 && /Waiting/.test(R.line("statue")), R.sent.length);
  await R.adv(2 * 60000);
  ok("it still waits until nothing has changed for the full time", R.sent.length === 0);
  await R.adv(2 * 60000);
  ok("once nothing has changed for 3 minutes the job starts", R.sent.length === 1 && R.sent[0].name === "statue" && R.sent[0].photos.length === 6, R.sent);
  ok("the sleep blocker is on while it runs", R.power === 1);
  ok("status says it is running", /^Starting|Training|Reading/.test(R.line("statue")), R.line("statue"));

  /* ---- progress and done ---- */
  R.ib.report({ name: "statue", kind: "progress", text: "Training 45%" });
  ok("progress is written for the phone", R.line("statue") === "Training 45%", R.line("statue"));
  const before = hashDir(path.join(R.inboxDir, "statue"));
  R.ib.report({ name: "statue", kind: "done", project: "statue", notes: ["Left out 1 blurry photo"] }); await sleep(120);
  ok("done is written, with the project name", R.line("statue") === "Done" && /Project: statue/.test(R.st("statue")), R.st("statue"));
  ok("a notification is sent when it finishes", R.notes.some((n) => /Splat ready/.test(n)), R.notes);
  ok("the sleep blocker is released", R.power === 0);
  ok("the photos were never changed", hashDir(path.join(R.inboxDir, "statue")) === before);
  await R.adv(60000); await R.adv(60000);
  ok("a finished folder is not run again", R.sent.length === 1);
  fs.unlinkSync(path.join(R.inboxDir, "statue", "STATUS.txt")); await R.adv(1000); await R.adv(4 * 60000);
  ok("deleting STATUS.txt runs it again", R.sent.length === 2, R.sent.length);
  R.ib.report({ name: "statue", kind: "done", project: "statue 2" }); await sleep(120);

  /* ---- the queue file is lost: finished folders are still recognised ---- */
  R.ib.stop(); fs.unlinkSync(path.join(R.dataDir, "inbox-queue.json")); R.ib = R.mk(); await R.ib.start(); await R.ib.hello({ ready: true }); await R.adv(5 * 60000);
  ok("a lost queue file does not cause finished folders to run again", R.sent.length === 2 && R.line("statue") === "Done", R.sent.length);
  fs.writeFileSync(path.join(R.dataDir, "inbox-queue.json"), "{ not json"); R.ib.stop(); R.ib = R.mk(); await R.ib.start(); await R.ib.hello({ ready: true }); await R.adv(5 * 60000);
  ok("a damaged queue file is set aside and the app carries on", R.sent.length === 2 && fs.readdirSync(R.dataDir).some((f) => /\.bad-/.test(f)));
  R.ib.stop();

  /* ---- five folders at once: one at a time, in order ---- */
  R = rig(); await R.ib.start(); await R.ib.hello({ ready: true });
  ["e", "d", "c", "b", "a"].forEach((n) => R.folder(n, 4)); await R.adv(1000); await R.adv(4 * 60000);
  ok("only one job runs at a time", R.sent.length === 1, R.sent.map((j) => j.name));
  ok("the others say where they are in line", /Queued, 2nd in line/.test(R.line(R.ib.state().jobs.filter((j) => j.status === "queued")[0].name)) || R.ib.state().jobs.filter((j) => j.status === "queued").length === 4, R.ib.state().jobs.map((j) => j.line));
  const order = [R.sent[0].name];
  for (let i = 0; i < 4; i++) { R.ib.report({ name: R.sent[i].name, kind: "done", project: R.sent[i].name }); await sleep(120); if (R.sent[i + 1]) order.push(R.sent[i + 1].name); }
  ok("all five get done, one after another", R.sent.length === 5 && new Set(order).size === 5, order);
  R.ib.report({ name: R.sent[4].name, kind: "done", project: R.sent[4].name }); await sleep(120);
  ok("every folder ends up Done", ["a", "b", "c", "d", "e"].every((n) => R.line(n) === "Done"), ["a", "b", "c", "d", "e"].map(R.line));
  R.ib.stop();

  /* ---- quality from the folder name, default from settings ---- */
  R = rig(); await R.ib.start(); await R.ib.setConfig({ dir: R.inboxDir, enabled: true, quality: "fast" }); await R.ib.hello({ ready: true });
  R.folder("vase [ultra]", 4); R.folder("plain", 4); await R.adv(1000); await R.adv(4 * 60000);
  const j1 = R.sent[0]; R.ib.report({ name: j1.name, kind: "done", project: "x" }); await sleep(120);
  const byName = {}; R.sent.forEach((j) => { byName[j.name] = j; });
  ok("[ultra] in the name sets the quality and is stripped from the project name", byName["vase [ultra]"] && byName["vase [ultra]"].quality === "ultra" && byName["vase [ultra]"].project === "vase", byName);
  ok("no suffix uses the default quality", byName["plain"] && byName["plain"].quality === "fast", byName);
  R.ib.stop();

  /* ---- not ready: nothing starts, nothing is lost ---- */
  R = rig(); await R.ib.start(); await R.ib.setConfig({ dir: R.inboxDir, enabled: true });
  R.folder("a", 4); await R.adv(1000); await R.adv(4 * 60000);
  ok("with the app window not ready nothing starts", R.sent.length === 0 && R.ib.state().jobs[0].status === "queued");
  await R.ib.hello({ ready: true }); await sleep(20);
  ok("it starts as soon as the app says it is ready", R.sent.length === 1);
  /* blocked (project folder not connected): put back, not failed, no attempt used */
  R.ib.report({ name: "a", kind: "blocked", reason: "your project folder isn't connected" }); await sleep(20);
  ok("a blocked job goes back in the queue, not to failed", R.ib.state().jobs[0].status === "queued" && /Paused: your project folder/.test(R.line("a")), R.line("a"));
  ok("a blocked job does not use up an attempt", R.ib._jobs()["a"].starts === 0);
  R.t += 60000; await R.ib.scan(); await sleep(10);
  ok("nothing restarts while it is paused", R.sent.length === 1);
  await R.ib.hello({ ready: true }); await sleep(20);
  ok("it carries on when the app is ready again", R.sent.length === 2);
  R.ib.stop();

  /* ---- a bad job never blocks the rest ---- */
  R = rig(); await R.ib.start(); await R.ib.hello({ ready: true });
  R.folder("blurry", 4); R.folder("good", 4); await R.adv(1000); await R.adv(4 * 60000);
  const first = R.sent[0].name; const hashBefore = hashDir(path.join(R.inboxDir, first));
  R.ib.report({ name: first, kind: "failed", error: "Only 2 of 6 photos could be placed in 3D." }); await sleep(120);
  ok("a failed job writes FAILED.txt with the reason", fs.existsSync(path.join(R.inboxDir, first, "FAILED.txt")) && /Only 2 of 6/.test(fs.readFileSync(path.join(R.inboxDir, first, "FAILED.txt"), "utf8")));
  ok("the status says Failed and gives the reason", R.line(first) === "Failed" && /Why: Only 2 of 6/.test(R.st(first)), R.st(first));
  ok("the next set starts straight away", R.sent.length === 2 && R.sent[1].name !== first, R.sent.map((j) => j.name));
  ok("a notification says what went wrong", R.notes.some((n) => /failed/i.test(n) && /Only 2 of 6/.test(n)), R.notes);
  ok("the photos of a failed set are untouched", hashDir(path.join(R.inboxDir, first)) === hashBefore);
  await R.adv(5 * 60000); ok("a failed set is not retried in a loop", R.sent.length === 2);
  fs.writeFileSync(path.join(R.inboxDir, first, "IMG_900.jpg"), JPG("fix")); fs.utimesSync(path.join(R.inboxDir, first, "IMG_900.jpg"), new Date(R.t), new Date(R.t));
  R.ib.report({ name: R.sent[1].name, kind: "done", project: "x" }); await sleep(120);
  await R.adv(1000); await R.adv(4 * 60000);
  ok("adding photos to a failed set tries it again", R.sent.length === 3 && R.sent[2].name === first && R.sent[2].photos.length === 5, R.sent.map((j) => j.name));
  ok("FAILED.txt is removed when it is tried again", !fs.existsSync(path.join(R.inboxDir, first, "FAILED.txt")) || R.line(first) !== "Failed");
  R.ib.stop();

  /* ---- retryable failure ---- */
  R = rig(); await R.ib.start(); await R.ib.hello({ ready: true }); R.folder("a", 4); await R.adv(1000); await R.adv(4 * 60000);
  R.ib.report({ name: "a", kind: "failed", error: "graphics card reset", retry: true }); await sleep(120);
  ok("a retryable failure is queued again", R.sent.length === 2, R.sent.length);
  R.ib.report({ name: "a", kind: "failed", error: "graphics card reset", retry: true }); await sleep(120);
  R.ib.report({ name: "a", kind: "failed", error: "graphics card reset", retry: true }); await sleep(120);
  ok("it gives up after " + MAX_STARTS + " attempts and says so", R.line("a") === "Failed" && R.sent.length === MAX_STARTS, [R.line("a"), R.sent.length]);
  R.ib.stop();

  /* ---- app killed mid-job ---- */
  R = rig(); await R.ib.start(); await R.ib.hello({ ready: true }); R.folder("a", 4); await R.adv(1000); await R.adv(4 * 60000);
  ok("(job is running)", R.sent.length === 1);
  R.ib.stop(); R.ib = R.mk(); await R.ib.start(); await R.ib.hello({ ready: true, fresh: true }); await sleep(30);
  ok("after a crash the interrupted job starts again from the beginning", R.sent.length === 2 && R.sent[1].name === "a", R.sent.length);
  ok("and says why", /Restarted/.test(R.st("a")), R.st("a"));
  for (let k = 0; k < 2; k++) { R.ib.stop(); R.ib = R.mk(); await R.ib.start(); await R.ib.hello({ ready: true }); await sleep(30); }
  ok("a job that keeps crashing the app is eventually given up on", R.line("a") === "Failed" && /crashed/.test(R.st("a")), R.st("a"));
  R.ib.stop();
  /* window reload while a job is running */
  R = rig(); await R.ib.start(); await R.ib.hello({ ready: true }); R.folder("a", 4); await R.adv(1000); await R.adv(4 * 60000);
  await R.ib.hello({ ready: true, fresh: true }); await sleep(30);
  ok("reloading the window puts the running job back and starts it again", R.sent.length === 2 && R.power === 1, [R.sent.length, R.power]);
  R.ib.stop();

  /* ---- stall watchdog ---- */
  R = rig(); await R.ib.start(); await R.ib.hello({ ready: true }); R.folder("a", 4); R.folder("b", 4); await R.adv(1000); await R.adv(4 * 60000);
  R.t += 31 * 60000; R.ib.report({ name: R.sent[0].name, kind: "progress", text: "Training 1%" }); R.t += 29 * 60000; await R.ib.scan();
  ok("steady progress keeps a long job alive", R.sent.length === 1 && R.aborted.length === 0);
  R.t += 31 * 60000; R.ib.stop(); R.ib = R.mk(); /* a fresh instance has no running job */ R.ib.stop();
  R = rig(); await R.ib.start(); await R.ib.hello({ ready: true }); R.folder("a", 4); R.folder("b", 4); await R.adv(1000); await R.adv(4 * 60000);
  const hung = R.sent[0].name; R.t += 31 * 60000; await R.ib.scan(); await sleep(150); const iv = R.ib; // the watchdog runs on the poll timer in the app; call it the same way
  iv.stop(); R.ib = R.mk(); /* simulate poll tick */
  R.ib.stop();
  { const R2 = rig(); const ib2 = create({ dataDir: R2.dataDir, now: () => R2.t, stableMs: 1000, stallMs: 30 * 60000, pollMs: 50, send: (j) => R2.sent.push(j), notify: () => {}, power: { start() {}, stop() {} }, freeBytes: () => Promise.resolve(50e9), abort: (n) => R2.aborted.push(n), log: () => {} });
    await ib2.setConfig({ dir: R2.inboxDir, enabled: true }); R2.folder("a", 4); R2.folder("b", 4); await ib2.start(); await ib2.hello({ ready: true });
    R2.t += 5000; await sleep(120); R2.t += 5000; await sleep(120);
    ok("(a job is running for the watchdog test)", R2.sent.length === 1, R2.sent.length);
    R2.t += 31 * 60000; await sleep(200);
    ok("a job with no sign of life for 30 minutes is stopped and reported", R2.aborted.length === 1 && R2.sent.length === 2, [R2.aborted, R2.sent.length]);
    ok("and the reason is written down", /Nothing happened for 30 minutes/.test(R2.st(R2.aborted[0] || "a")), R2.st("a"));
    ib2.stop(); }

  /* ---- junk, hidden, sync leftovers ---- */
  R = rig(); await R.ib.start(); await R.ib.hello({ ready: true });
  R.folder("_archive", 5); R.folder(".hidden", 5);
  R.folder("mixed", 4, (d) => { fs.writeFileSync(path.join(d, "IMG_000 (Max's conflicted copy 2026-11-13).jpg", ), JPG("c")); fs.writeFileSync(path.join(d, "x.jpg.tmp"), "partial"); fs.writeFileSync(path.join(d, ".dropbox"), ""); fs.writeFileSync(path.join(d, "notes.txt"), "hello"); fs.writeFileSync(path.join(d, "IMG_9.heic"), "heic"); });
  await R.adv(1000); await R.adv(4 * 60000);
  ok("folders starting with _ or . are ignored", !fs.existsSync(path.join(R.inboxDir, "_archive", "STATUS.txt")) && !fs.existsSync(path.join(R.inboxDir, ".hidden", "STATUS.txt")));
  ok("temp, conflicted-copy and non-photo files are not counted", R.sent[0] && R.sent[0].photos.length === 4, R.sent[0] && R.sent[0].photos);
  ok("unsupported formats are mentioned", /HEIC/.test(R.st("mixed")), R.st("mixed"));
  R.ib.stop();

  /* ---- corrupt and unreadable photos ---- */
  R = rig(); await R.ib.start(); await R.ib.hello({ ready: true });
  R.folder("dmg", 5, (d) => { fs.writeFileSync(path.join(d, "IMG_000.jpg"), Buffer.from("this is not a jpeg at all, it is text")); });
  await R.adv(1000); await R.adv(4 * 60000);
  ok("a corrupt photo is left out and the rest still run", R.sent.length === 1 && R.sent[0].photos.length === 4 && !R.sent[0].photos.includes("IMG_000.jpg"), R.sent[0]);
  ok("and the status mentions it", /Left out 1 unreadable/.test(R.st("dmg")), R.st("dmg"));
  R.folder("tiny", 2); await R.adv(1000); await R.adv(4 * 60000);
  ok("fewer than 3 photos waits (more may be on the way) instead of failing", /Waiting for at least 3 photos \(found 2\)/.test(R.line("tiny")), R.line("tiny"));
  R.ib.stop();

  /* ---- disk space ---- */
  R = rig({ free: 0.5e9 }); await R.ib.start(); await R.ib.setConfig({ dir: R.inboxDir, enabled: true }); await R.ib.hello({ ready: true }); R.folder("a", 4); await R.adv(1000); await R.adv(4 * 60000);
  ok("low disk space pauses instead of starting", R.sent.length === 0 && /disk space/.test(R.ib.state().pause), R.ib.state().pause);
  R.free = 50e9; await R.adv(60000); await R.adv(1000);
  ok("it carries on once there is room", R.sent.length === 1 && !R.ib.state().pause, [R.sent.length, R.ib.state().pause]);
  R.ib.stop();

  /* ---- folder missing / vanishing ---- */
  R = rig(); await R.ib.start(); await R.ib.hello({ ready: true }); R.folder("a", 4); await R.adv(1000);
  fs.renameSync(R.inboxDir, R.inboxDir + "-gone"); await R.adv(1000);
  ok("an unreadable inbox folder is reported, not treated as empty", /Can't read the inbox folder/.test(R.ib.state().problem) && R.ib._jobs()["a"], R.ib.state().problem);
  fs.renameSync(R.inboxDir + "-gone", R.inboxDir); await R.adv(1000);
  ok("and recovers when it comes back", R.ib.state().problem === "");
  fs.rmSync(path.join(R.inboxDir, "a"), { recursive: true }); await R.adv(1000);
  ok("a folder you delete while it waits is forgotten", !R.ib._jobs()["a"]);
  R.ib.stop();

  /* ---- reading photos is limited to the running job ---- */
  R = rig(); await R.ib.start(); await R.ib.hello({ ready: true }); R.folder("a", 4); await R.adv(1000); await R.adv(4 * 60000);
  let b1 = null; try { b1 = R.ib.readPhoto("a", "IMG_000.jpg"); } catch (e) {}
  ok("the running job's photos can be read", b1 && b1.length > 10);
  let leak = true; try { R.ib.readPhoto("a", "../../data/inbox-queue.json"); } catch (e) { leak = false; }
  ok("a path outside the set can't be read", leak === false);
  let leak2 = true; try { R.ib.readPhoto("../Inbox", "IMG_000.jpg"); } catch (e) { leak2 = false; }
  ok("another folder can't be read", leak2 === false);
  R.ib.report({ name: "a", kind: "done", project: "a" }); await sleep(100);
  let leak3 = true; try { R.ib.readPhoto("a", "IMG_000.jpg"); } catch (e) { leak3 = false; }
  ok("nothing can be read once the job is over", leak3 === false);
  R.ib.stop();

  /* ---- settings survive a restart ---- */
  R = rig(); await R.ib.start(); await R.ib.setConfig({ dir: R.inboxDir, enabled: true, quality: "high", startWithWindows: true }); R.ib.stop(); R.ib = R.mk(); await R.ib.start();
  const c = R.ib.state().config; ok("the inbox settings are remembered", c.dir === R.inboxDir && c.enabled && c.quality === "high" && c.startWithWindows, c);
  R.ib.stop();
  console.log(bad ? "\n" + bad + " failed" : "\nall passed");
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.log("FAIL crashed -> " + (e && e.stack || e)); process.exit(1); });
