// Splatbox inbox (V039): a watch folder (for example inside Dropbox) where each sub-folder of photos becomes a splat project.
// This file is the queue only. It never touches a photo: it reads the folder, decides when a set is ready, hands one job at a time
// to the app window, and writes STATUS.txt / FAILED.txt next to the photos so progress can be read from a phone.
// It has no Electron imports so the tests can drive it with a fake clock and a temp folder.
"use strict";
const path = require("path");
const realFs = require("fs");

const QUALS = ["draft", "fast", "balanced", "high", "ultra"];
const PHOTO = /\.(jpe?g|png|webp)$/i;
const UNSUPPORTED = /\.(heic|heif|dng|cr2|cr3|nef|arw|raf|orf|rw2|tif|tiff|bmp|gif)$/i;
const JUNK = /(^\.|^~\$|\.tmp$|\.part$|\.crdownload$|\.dropbox|conflicted copy|^desktop\.ini$|^thumbs\.db$)/i;
const MIN_PHOTOS = 3;
const MAX_STARTS = 3;               // a job that has been started this many times without finishing is given up on (stops crash loops)
const MIN_FREE = 2 * 1024 * 1024 * 1024;

function ordinal(n) { const s = ["th", "st", "nd", "rd"], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); }
function pad(n) { return n < 10 ? "0" + n : "" + n; }
function stamp(t) { const d = new Date(t); return d.getDate() + " " + ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][d.getMonth()] + " " + d.getFullYear() + " " + pad(d.getHours()) + ":" + pad(d.getMinutes()); }

/* "statue [high]" -> { project: "statue", quality: "high" } */
function parseName(folder) {
  const m = /^(.*?)\s*\[(draft|fast|balanced|high|ultra)\]\s*$/i.exec(folder);
  if (m && m[1].trim()) return { project: m[1].trim(), quality: m[2].toLowerCase() };
  return { project: folder.trim() || "Photo scan", quality: "" };
}

function create(o) {
  const fs = o.fs || realFs;
  const now = o.now || (() => Date.now());
  const stableMs = o.stableMs != null ? o.stableMs : 3 * 60 * 1000;
  const stallMs = o.stallMs != null ? o.stallMs : 30 * 60 * 1000;
  const minFree = o.minFree != null ? o.minFree : MIN_FREE;
  const cfgFile = path.join(o.dataDir, "inbox-config.json");
  const qFile = path.join(o.dataDir, "inbox-queue.json");
  const log = o.log || function () {};
  const send = o.send || function () {};
  const notify = o.notify || function () {};
  const changed = o.onChange || function () {};
  const power = o.power || { start() {}, stop() {} };
  const freeBytes = o.freeBytes || (() => Promise.resolve(null));

  let cfg = { dir: "", enabled: false, quality: "", startWithWindows: false };
  let jobs = {};                    // folder name -> job record
  let ready = false;                // the app window has said it can run jobs
  let pause = "";                   // why jobs are not being started right now ("" = not paused)
  let problem = "";                 // why the watch folder can't be read
  let running = null;               // name of the job in the app window
  let busy = false;                 // a scan is in progress
  let timer = null;
  const lastStatus = {};            // name -> last STATUS text written (to avoid needless Dropbox churn)
  const lastWrite = {};             // name -> time of last progress write

  /* ---------- small file helpers ---------- */
  function atomicWrite(file, text) {
    const tmp = file + "." + process.pid + ".tmp";
    fs.writeFileSync(tmp, text);
    fs.renameSync(tmp, file);
  }
  function readJson(file) {
    try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch (e) { return null; }
  }
  function saveQueue() {
    try { fs.mkdirSync(o.dataDir, { recursive: true }); atomicWrite(qFile, JSON.stringify({ v: 1, jobs })); } catch (e) { log("queue save failed: " + e.message); }
  }
  function saveCfg() {
    try { fs.mkdirSync(o.dataDir, { recursive: true }); atomicWrite(cfgFile, JSON.stringify(cfg)); } catch (e) { log("config save failed: " + e.message); }
  }

  /* ---------- load (and recover) ---------- */
  function load() {
    const c = readJson(cfgFile);
    if (c && typeof c === "object") cfg = Object.assign(cfg, { dir: String(c.dir || ""), enabled: !!c.enabled, quality: QUALS.indexOf(c.quality) >= 0 ? c.quality : "", startWithWindows: !!c.startWithWindows });
    let q = null;
    if (fs.existsSync(qFile)) {
      q = readJson(qFile);
      if (!q || typeof q.jobs !== "object") {
        try { fs.renameSync(qFile, qFile + ".bad-" + now()); } catch (e) {}
        q = null; log("queue file was unreadable; starting empty (finished folders are recognised from their STATUS.txt)");
      }
    }
    jobs = (q && q.jobs) || {};
    Object.keys(jobs).forEach((k) => {
      const j = jobs[k];
      if (j.status === "running") {
        if ((j.starts || 0) >= MAX_STARTS) { j.status = "failed"; j.error = "Splatbox was closed or crashed " + j.starts + " times while working on this set, so it was given up on. Delete STATUS.txt in this folder to try again."; j.finished = now(); }
        else { j.status = "queued"; j.note = "Restarted after Splatbox was closed. Starting this set again from the beginning."; }
      }
    });
    saveQueue();
  }

  /* ---------- reading a scan folder ---------- */
  function readSet(dirPath) {
    const out = { photos: [], bad: [], unsupported: 0, sig: "", unreadable: 0 };
    let names;
    try { names = fs.readdirSync(dirPath, { withFileTypes: true }); } catch (e) { out.unreadable = 1; return out; }
    let total = 0, newest = 0;
    names.forEach((d) => {
      if (!d.isFile() || JUNK.test(d.name)) return;
      if (UNSUPPORTED.test(d.name)) { out.unsupported++; return; }
      if (!PHOTO.test(d.name)) return;
      let st; try { st = fs.statSync(path.join(dirPath, d.name)); } catch (e) { out.unreadable++; return; }
      total += st.size; if (st.mtimeMs > newest) newest = st.mtimeMs;
      out.photos.push({ name: d.name, size: st.size });
    });
    out.photos.sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
    out.sig = out.photos.length + "|" + total + "|" + Math.round(newest) + "|" + out.unsupported;
    return out;
  }
  /* the first bytes must look like the format the name claims. Catches half-synced and corrupt files before a job starts. */
  function looksOk(file) {
    let fd = null;
    try {
      fd = fs.openSync(file, "r");
      const b = Buffer.alloc(12), n = fs.readSync(fd, b, 0, 12, 0);
      if (n < 12) return false;
      if (/\.jpe?g$/i.test(file)) return b[0] === 0xff && b[1] === 0xd8;
      if (/\.png$/i.test(file)) return b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47;
      if (/\.webp$/i.test(file)) return b.toString("latin1", 0, 4) === "RIFF" && b.toString("latin1", 8, 12) === "WEBP";
      return true;
    } catch (e) { return false; } finally { if (fd != null) { try { fs.closeSync(fd); } catch (e) {} } }
  }

  /* ---------- status files ---------- */
  function queuePos(name) {
    const q = Object.keys(jobs).filter((k) => jobs[k].status === "queued").sort(byQueue);
    const i = q.indexOf(name);
    return i < 0 ? 0 : i + 1;
  }
  function byQueue(a, b) { const x = jobs[a], y = jobs[b]; return (x.queued || 0) - (y.queued || 0) || (a < b ? -1 : 1); }
  function statusLine(name) {
    const j = jobs[name];
    switch (j.status) {
      case "seen": return j.waitMsg || "Waiting for the photos to finish syncing";
      case "queued": {
        if (pause) return "Paused: " + pause;
        const pos = queuePos(name), ahead = pos - 1 + (running ? 1 : 0);
        return ahead <= 0 ? "Queued, next up" : "Queued, " + ordinal(ahead + 1) + " in line";
      }
      case "running": return j.progress || "Starting";
      case "done": return "Done";
      case "failed": return "Failed";
    }
    return j.status;
  }
  function statusText(name) {
    const j = jobs[name], p = parseName(name), L = [];
    L.push("Splatbox inbox");
    L.push("Status: " + statusLine(name));
    L.push("Scan: " + p.project);
    L.push("Photos: " + (j.count != null ? j.count : "?"));
    L.push("Quality: " + (j.quality || p.quality || cfg.quality || "default"));
    if (j.status === "done" && j.project) L.push("Project: " + j.project);
    if (j.status === "failed" && j.error) L.push("Why: " + j.error);
    if (j.notes && j.notes.length) j.notes.forEach((n) => L.push("Note: " + n));
    if (j.note && j.status !== "done") L.push("Note: " + j.note);
    L.push("Updated: " + stamp(now()));
    if (j.status === "done" || j.status === "failed") L.push("To run this folder again, delete this file.");
    return L.join("\r\n") + "\r\n";
  }
  function writeStatus(name, force) {
    const j = jobs[name]; if (!j) return;
    const dirPath = path.join(cfg.dir, name);
    const body = statusText(name).replace(/Updated: .*\r\n/, "");
    if (!force && lastStatus[name] === body && fs.existsSync(path.join(dirPath, "STATUS.txt"))) return;
    try {
      atomicWrite(path.join(dirPath, "STATUS.txt"), statusText(name));
      lastStatus[name] = body;
      const ff = path.join(dirPath, "FAILED.txt");
      if (j.status === "failed") atomicWrite(ff, "This scan could not be turned into a splat.\r\n\r\nWhy: " + (j.error || "unknown") + "\r\n" + (j.notes && j.notes.length ? "\r\n" + j.notes.join("\r\n") + "\r\n" : "") + "\r\nPhotos in this folder were not changed. Fix the problem (or add more photos) and the folder will be tried again. You can also delete STATUS.txt to force another try.\r\n");
      else if (fs.existsSync(ff)) fs.unlinkSync(ff);
    } catch (e) { log("status write failed for " + name + ": " + e.message); }
  }
  function refreshStatuses() {
    Object.keys(jobs).forEach((k) => { if (jobs[k].status === "queued" || jobs[k].status === "seen") writeStatus(k); });
  }

  /* ---------- the scan ---------- */
  function adopt(name, dirPath, set) {
    /* A folder we have no record of. If its STATUS.txt says it already finished, believe that (this is how a lost queue file is rebuilt). */
    const j = { status: "seen", sig: set.sig, stable: now(), count: set.photos.length, starts: 0, added: now() };
    try {
      const t = fs.readFileSync(path.join(dirPath, "STATUS.txt"), "utf8");
      if (/^Status: Done/m.test(t)) { j.status = "done"; const m = /^Project: (.*)$/m.exec(t); if (m) j.project = m[1].trim(); }
      else if (/^Status: Failed/m.test(t)) { j.status = "failed"; j.error = ((/^Why: (.*)$/m.exec(t)) || [])[1] || "failed earlier"; }
    } catch (e) {}
    return j;
  }
  function scan() {
    if (busy) return Promise.resolve();
    busy = true;
    try { scanOnce(); } catch (e) { log("scan error: " + (e && e.stack || e)); }
    return Promise.resolve(spaceOk()).then((sp) => { busy = false; if (sp) dispatch(); changed(); }, () => { busy = false; });
  }
  function scanOnce() {
    problem = "";
    if (!cfg.enabled || !cfg.dir) return;
    let ents;
    try { ents = fs.readdirSync(cfg.dir, { withFileTypes: true }); }
    catch (e) { problem = "Can't read the inbox folder (" + cfg.dir + "). Is Dropbox running and is the folder still there?"; return; }
    const seenNames = {};
    ents.forEach((d) => {
      if (!d.isDirectory()) return;
      const name = d.name;
      if (name.charAt(0) === "." || name.charAt(0) === "_" || JUNK.test(name)) return;
      seenNames[name] = 1;
      const dirPath = path.join(cfg.dir, name), set = readSet(dirPath);
      let j = jobs[name], fresh = false;
      if (!j) { j = jobs[name] = adopt(name, dirPath, set); fresh = true; }
      j.count = set.photos.length;
      if (j.status === "running") return;      // never disturb a running job
      const hasStatus = fs.existsSync(path.join(dirPath, "STATUS.txt"));
      if ((j.status === "done" || j.status === "failed") && !fresh) {
        if (!hasStatus) { reset(j, set); }       // STATUS.txt deleted = run it again
        else if (j.status === "failed" && j.sig !== set.sig) { reset(j, set); }   // photos changed since it failed
        else { syncFinal(name); return; }
      } else if (j.status === "done" || j.status === "failed") { return; }
      if (j.sig !== set.sig) { j.sig = set.sig; j.stable = now(); if (j.status === "queued") { j.status = "seen"; delete j.queued; } }
      if (j.status === "seen") {
        if (set.unreadable) { j.waitMsg = "Waiting for the folder to become readable"; j.stable = now(); }
        else if (now() - j.stable < stableMs) j.waitMsg = "Waiting for the photos to finish syncing";
        else {
          const good = set.photos.filter((p) => looksOk(path.join(dirPath, p.name)));
          const bad = set.photos.filter((p) => good.indexOf(p) < 0).map((p) => p.name);
          if (good.length < MIN_PHOTOS) {
            if (set.photos.length >= MIN_PHOTOS && bad.length) j.waitMsg = "Waiting: " + bad.length + " photo" + (bad.length === 1 ? "" : "s") + " can't be read yet (still syncing, or damaged)";
            else j.waitMsg = "Waiting for at least " + MIN_PHOTOS + " photos (found " + good.length + ")" + (set.unsupported ? ". " + set.unsupported + " file" + (set.unsupported === 1 ? " is" : "s are") + " in a format Splatbox can't read (HEIC, RAW, TIFF): export them as JPG" : "");
            j.stable = now() - stableMs + 60 * 1000; // look again in a minute rather than every poll
          } else {
            j.photos = good.map((p) => p.name); j.count = good.length; j.notes = [];
            if (bad.length) j.notes.push("Left out " + bad.length + " unreadable file" + (bad.length === 1 ? "" : "s") + ": " + bad.slice(0, 8).join(", ") + (bad.length > 8 ? " and more" : ""));
            if (set.unsupported) j.notes.push(set.unsupported + " file" + (set.unsupported === 1 ? "" : "s") + " in a format Splatbox can't read (HEIC, RAW, TIFF) " + (set.unsupported === 1 ? "was" : "were") + " ignored");
            j.status = "queued"; j.queued = now(); delete j.waitMsg;
          }
        }
      }
      writeStatus(name, fresh);
    });
    Object.keys(jobs).forEach((k) => {
      if (!seenNames[k] && jobs[k].status !== "running") { delete jobs[k]; delete lastStatus[k]; }
    });
    refreshStatuses();
    saveQueue();
  }
  /* a finished job's STATUS.txt must say what the queue says (it can differ after a crash or when a job was given up on at start-up) */
  function syncFinal(name) {
    try {
      const t = fs.readFileSync(path.join(cfg.dir, name, "STATUS.txt"), "utf8"), m = /^Status: (.*?)\r?$/m.exec(t);
      if (!m || m[1] !== statusLine(name)) writeStatus(name, true);
    } catch (e) { writeStatus(name, true); }
  }
  function reset(j, set) {
    j.status = "seen"; j.sig = set.sig; j.stable = now(); j.starts = 0; delete j.error; delete j.project; delete j.queued; delete j.finished; delete j.note; delete j.progress; j.count = set.photos.length;
  }
  function spaceOk() {
    if (!cfg.enabled || !cfg.dir || running) return true;
    return Promise.resolve(freeBytes(cfg.dir)).then((b) => {
      if (b != null && b < minFree) { pause = "low disk space (" + (b / 1073741824).toFixed(1) + " GB free, need " + (minFree / 1073741824).toFixed(0) + " GB)"; return false; }
      if (pause && /disk space/.test(pause)) pause = "";
      return true;
    }, () => true);
  }

  /* ---------- dispatching to the app window ---------- */
  function dispatch() {
    if (!cfg.enabled || !ready || running || pause || problem) return;
    const q = Object.keys(jobs).filter((k) => jobs[k].status === "queued").sort(byQueue);
    if (!q.length) return;
    const name = q[0], j = jobs[name], p = parseName(name);
    running = name;
    j.status = "running"; j.starts = (j.starts || 0) + 1; j.started = now(); j.progress = "Starting"; j.beat = now();
    j.quality = p.quality || cfg.quality || "";
    saveQueue(); writeStatus(name, true); power.start(); changed();
    send({ name, project: p.project, quality: p.quality || cfg.quality || "", dir: path.join(cfg.dir, name), photos: j.photos.slice(), key: name + "|" + j.sig, attempt: j.starts });
  }
  function finish(name, ok, info) {
    const j = jobs[name]; if (!j) return;
    if (running === name) { running = null; power.stop(); }
    j.finished = now(); delete j.progress; delete j.beat;
    if (ok) { j.status = "done"; j.project = info.project || ""; j.notes = (j.notes || []).concat(info.notes || []); delete j.error; delete j.note; }
    else if (info.retry && (j.starts || 0) < MAX_STARTS) { j.status = "queued"; j.queued = now(); j.note = "Tried again after: " + info.error; }
    else { j.status = "failed"; j.error = info.error || "Unknown problem"; j.notes = (j.notes || []).concat(info.notes || []); }
    saveQueue(); writeStatus(name, true); delete lastWrite[name];
    const p = parseName(name);
    if (j.status === "done") notify("Splat ready: " + p.project, "Saved to your project folder as “" + j.project + "”.");
    else if (j.status === "failed") notify("Splat failed: " + p.project, j.error);
    changed();
    setTimeout(() => { scan(); }, 50);
  }

  /* ---------- messages from the app window ---------- */
  function report(m) {
    const name = m && m.name, j = name && jobs[name];
    if (!j || running !== name) return { ok: false, why: "not the running job" };
    j.beat = now();
    if (m.kind === "progress") {
      const text = String(m.text || "Working").slice(0, 120), t = now();
      if (text !== j.progress && (!lastWrite[name] || t - lastWrite[name] > 15000 || /^(Solving|Finding|Matching|Saving)/.test(text) !== /^(Solving|Finding|Matching|Saving)/.test(j.progress || ""))) { j.progress = text; lastWrite[name] = t; writeStatus(name, true); changed(); }
      else j.progress = text;
      return { ok: true };
    }
    if (m.kind === "done") { finish(name, true, { project: String(m.project || ""), notes: m.notes || [] }); return { ok: true }; }
    if (m.kind === "failed") { finish(name, false, { error: String(m.error || "Unknown problem"), retry: !!m.retry, notes: m.notes || [] }); return { ok: true }; }
    if (m.kind === "blocked") {
      /* the app can't run jobs right now (project folder not connected, no WebGPU...). Put the job back and wait. Not a failure. */
      running = null; power.stop(); j.status = "queued"; j.starts = Math.max(0, (j.starts || 1) - 1); delete j.progress; delete j.beat;
      pause = String(m.reason || "the app can't run jobs right now").slice(0, 160); ready = false;
      saveQueue(); refreshStatuses(); writeStatus(name, true);
      notify("Splatbox inbox paused", pause);
      changed(); return { ok: true };
    }
    return { ok: false };
  }
  function readPhoto(name, file) {
    const j = jobs[name];
    if (!j || j.status !== "running" || running !== name || !j.photos || j.photos.indexOf(file) < 0) throw new Error("not allowed");
    return fs.readFileSync(path.join(cfg.dir, name, file));
  }

  /* ---------- stall watchdog ---------- */
  function watchdog() {
    if (!running) return;
    const j = jobs[running];
    if (j && now() - (j.beat || j.started || now()) > stallMs) {
      const name = running;
      try { o.abort && o.abort(name); } catch (e) {}
      finish(name, false, { error: "Nothing happened for " + Math.round(stallMs / 60000) + " minutes, so it was stopped. The photos may be too hard to solve, or the graphics card stopped responding." });
    }
  }

  /* ---------- public ---------- */
  function start() {
    load();
    if (timer) clearInterval(timer);
    timer = setInterval(() => { watchdog(); scan(); }, o.pollMs || 20000);
    if (timer.unref) timer.unref();
    return scan();
  }
  function stop() { if (timer) clearInterval(timer); timer = null; if (running) power.stop(); }
  function setConfig(p) {
    if (p && typeof p === "object") {
      if (typeof p.dir === "string") cfg.dir = p.dir;
      if (typeof p.enabled === "boolean") cfg.enabled = p.enabled;
      if (typeof p.quality === "string") cfg.quality = QUALS.indexOf(p.quality) >= 0 ? p.quality : "";
      if (typeof p.startWithWindows === "boolean") cfg.startWithWindows = p.startWithWindows;
    }
    saveCfg();
    if (p && (p.dir !== undefined || p.enabled !== undefined)) { jobs = running ? { [running]: jobs[running] } : {}; }
    return scan().then(() => state());
  }
  function hello(info) {
    /* a window that has just (re)loaded can't still be running the job it was given: put that job back in the queue */
    if (info && info.fresh && running) {
      const name = running, j = jobs[name];
      running = null; power.stop();
      if (j) {
        delete j.progress; delete j.beat;
        if ((j.starts || 0) >= MAX_STARTS) { j.status = "failed"; j.error = "The app window was reloaded or crashed " + j.starts + " times while working on this set, so it was given up on."; j.finished = now(); }
        else { j.status = "queued"; j.queued = now(); j.note = "Restarted because the app window was reloaded. Starting this set again from the beginning."; }
        saveQueue(); writeStatus(name, true);
      }
    }
    ready = !!(info && info.ready);
    if (ready) pause = (pause && /disk space/.test(pause)) ? pause : "";
    else if (info && info.reason) pause = String(info.reason).slice(0, 160);
    refreshStatuses(); changed();
    return scan();
  }
  function state() {
    return {
      config: Object.assign({}, cfg), ready, pause, problem, running,
      jobs: Object.keys(jobs).sort(byQueue).map((k) => ({ name: k, project: parseName(k).project, status: jobs[k].status, line: statusLine(k), count: jobs[k].count, error: jobs[k].error || "", at: jobs[k].finished || jobs[k].queued || jobs[k].added || 0 }))
    };
  }
  return { start, stop, scan, setConfig, hello, report, readPhoto, state, _jobs: () => jobs, _cfg: () => cfg };
}

module.exports = { create, parseName, MAX_STARTS, MIN_PHOTOS };
