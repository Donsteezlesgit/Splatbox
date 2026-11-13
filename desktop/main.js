// Splatbox desktop shell. Serves the released app from an app:// origin (stable storage, secure context)
// and updates itself in place from GitHub Releases.
const { app, BrowserWindow, protocol, session, shell, dialog, Menu, ipcMain } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const { Readable } = require("stream");

protocol.registerSchemesAsPrivileged([
  { scheme: "app", privileges: { standard: true, secure: true, supportFetchAPI: true, stream: true, corsEnabled: true } }
]);
app.commandLine.appendSwitch("ignore-gpu-blocklist");

const WWW = path.join(__dirname, "www");
const MIME = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
  ".wasm": "application/wasm", ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml",
  ".css": "text/css; charset=utf-8", ".webmanifest": "application/manifest+json"
};
let win = null, updateReady = false, manualCheck = false;

function serve(req) {
  let rel;
  try { rel = decodeURIComponent(new URL(req.url).pathname); } catch (e) { return new Response("bad url", { status: 400 }); }
  if (rel === "/") rel = "/index.html";
  if (rel === "/sw.js") return new Response("", { status: 404 }); // no service worker in the desktop app
  const file = path.normalize(path.join(WWW, rel));
  if (!file.startsWith(WWW + path.sep)) return new Response("forbidden", { status: 403 });
  let st;
  try { st = fs.statSync(file); } catch (e) { return new Response("not found", { status: 404 }); }
  if (!st.isFile()) return new Response("not found", { status: 404 });
  return new Response(Readable.toWeb(fs.createReadStream(file)), {
    status: 200,
    headers: { "Content-Type": MIME[path.extname(file).toLowerCase()] || "application/octet-stream", "Content-Length": String(st.size) }
  });
}

/* ---------- video encoding: PNG frames in, ProRes / DNxHR / H.264 out (bundled ffmpeg) ---------- */
const TESTING = !!process.env.SPLATBOX_TEST;
const BT709 = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"];
const FORMATS = {
  prores4444: { ext: "mov", label: "ProRes 4444", args: (t) => ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", t ? "yuva444p10le" : "yuv444p10le", "-vendor", "apl0"].concat(t ? ["-alpha_bits", "16"] : []) },
  prores422: { ext: "mov", label: "ProRes 422 HQ", args: () => ["-c:v", "prores_ks", "-profile:v", "hq", "-pix_fmt", "yuv422p10le", "-vendor", "apl0"] },
  dnxhr: { ext: "mov", label: "DNxHR HQX", args: () => ["-c:v", "dnxhd", "-profile:v", "dnxhr_hqx", "-pix_fmt", "yuv422p10le"] },
  mp4: { ext: "mp4", label: "H.264 MP4", args: () => ["-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", "-movflags", "+faststart"] }
};
const encoders = new Map();
let encSeq = 0;
function ffmpegPath() { return require("@ffmpeg-installer/ffmpeg").path.replace("app.asar" + path.sep, "app.asar.unpacked" + path.sep); }
function encWrite(e, buf) {
  return new Promise((res, rej) => {
    if (e.dead) return rej(new Error(e.err || "ffmpeg stopped"));
    e.pend = () => (e.dead ? rej(new Error(e.err || "ffmpeg stopped")) : res());
    if (e.p.stdin.write(buf)) { e.pend = null; res(); }
    else e.p.stdin.once("drain", () => { const f = e.pend; e.pend = null; if (f) f(); });
  });
}
ipcMain.handle("enc:start", async (ev, o) => {
  const f = FORMATS[o && o.fmt];
  if (!f) throw new Error("Unknown format");
  const base = String(o.name || "splatbox").replace(/[^\w-]+/g, "_");
  let out;
  if (process.env.SPLATBOX_TEST_OUT) out = path.join(process.env.SPLATBOX_TEST_OUT, base + "." + f.ext);
  else {
    const r = await dialog.showSaveDialog(win || undefined, { title: "Save " + f.label, defaultPath: path.join(app.getPath("videos"), base + "." + f.ext), filters: [{ name: f.label, extensions: [f.ext] }] });
    if (r.canceled || !r.filePath) return null;
    out = r.filePath;
  }
  const fps = Math.max(1, Math.min(240, +o.fps || 30));
  const args = ["-y", "-hide_banner", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "png", "-i", "-",
    "-vf", "scale=out_color_matrix=bt709:out_range=tv"].concat(BT709, f.args(!!o.transp), ["-an", out]);
  const p = spawn(ffmpegPath(), args, { stdio: ["pipe", "ignore", "pipe"], windowsHide: true });
  const e = { p, out, err: "", dead: false, pend: null, closed: null, bytes: 0 };
  e.closed = new Promise((res) => p.on("close", (code) => { e.dead = true; e.code = code; if (e.pend) e.pend(); res(code); }));
  p.on("error", (er) => { e.dead = true; e.err = String(er.message || er); if (e.pend) e.pend(); });
  p.stderr.on("data", (d) => { e.err = (e.err + d).slice(-2000); });
  p.stdin.on("error", () => { e.dead = true; if (e.pend) e.pend(); });
  const id = ++encSeq;
  encoders.set(id, e);
  return id;
});
ipcMain.handle("enc:frame", (ev, id, bytes) => {
  const e = encoders.get(id);
  if (!e) throw new Error("No such encode");
  return encWrite(e, Buffer.from(bytes.buffer, bytes.byteOffset, bytes.byteLength));
});
ipcMain.handle("enc:finish", async (ev, id) => {
  const e = encoders.get(id);
  if (!e) throw new Error("No such encode");
  encoders.delete(id);
  if (!e.dead) e.p.stdin.end();
  const code = await e.closed;
  if (code !== 0) { try { fs.unlinkSync(e.out); } catch (er) {} throw new Error("ffmpeg failed: " + (e.err || "code " + code).trim()); }
  const size = fs.statSync(e.out).size;
  if (!TESTING) shell.showItemInFolder(e.out);
  return { path: e.out, name: path.basename(e.out), bytes: size };
});
ipcMain.handle("enc:cancel", async (ev, id) => {
  const e = encoders.get(id);
  if (!e) return false;
  encoders.delete(id);
  try { e.p.kill(); } catch (er) {}
  await e.closed;
  try { fs.unlinkSync(e.out); } catch (er) {}
  return true;
});
app.on("before-quit", () => { encoders.forEach((e) => { try { e.p.kill(); } catch (er) {} }); });

function createWindow() {
  win = new BrowserWindow({
    width: 1500, height: 920, minWidth: 900, minHeight: 600, backgroundColor: "#000000", autoHideMenuBar: true,
    icon: path.join(__dirname, "icon.png"),
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, nodeIntegration: false }
  });
  win.loadURL("app://splatbox/index.html");
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/i.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (e, url) => {
    if (!url.startsWith("app://splatbox/")) { e.preventDefault(); if (/^https?:/i.test(url)) shell.openExternal(url); }
  });
  win.on("closed", () => { win = null; });
}

function buildMenu() {
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    { label: "File", submenu: [{ role: "quit" }] },
    { label: "View", submenu: [{ role: "reload" }, { role: "togglefullscreen" }, { role: "toggleDevTools" }, { type: "separator" }, { role: "resetZoom" }, { role: "zoomIn" }, { role: "zoomOut" }] },
    { label: "Help", submenu: [
      { label: "Check for updates", click: () => checkUpdates(true) },
      { label: "About Splatbox", click: () => dialog.showMessageBox({ message: "Splatbox desktop " + app.getVersion(), detail: "Updates install automatically from GitHub." }) }
    ] }
  ]));
}

function setupUpdater() {
  if (!app.isPackaged) return;
  const { autoUpdater } = require("electron-updater");
  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;
  autoUpdater.on("update-downloaded", (info) => {
    updateReady = true;
    dialog.showMessageBox(win || undefined, {
      type: "info", buttons: ["Restart now", "Later"], defaultId: 0, cancelId: 1,
      message: "Splatbox " + info.version + " is ready",
      detail: "Restart to finish updating. It will also install next time you close the app."
    }).then((r) => { if (r.response === 0) autoUpdater.quitAndInstall(true, true); });
  });
  autoUpdater.on("update-not-available", () => {
    if (manualCheck) dialog.showMessageBox(win || undefined, { message: "You're up to date", detail: "Splatbox desktop " + app.getVersion() });
    manualCheck = false;
  });
  autoUpdater.on("error", (err) => {
    if (manualCheck) dialog.showMessageBox(win || undefined, { type: "warning", message: "Couldn't check for updates", detail: String(err && err.message || err) });
    manualCheck = false;
  });
  checkUpdates(false);
  setInterval(() => checkUpdates(false), 4 * 60 * 60 * 1000);
}
function checkUpdates(manual) {
  if (!app.isPackaged) { if (manual) dialog.showMessageBox({ message: "Updates only work in the installed app." }); return; }
  if (updateReady) return;
  manualCheck = !!manual;
  require("electron-updater").autoUpdater.checkForUpdates().catch(() => {});
}

if (!app.requestSingleInstanceLock()) { app.quit(); }
else {
  app.on("second-instance", () => { if (win) { if (win.isMinimized()) win.restore(); win.focus(); } });
  app.whenReady().then(() => {
    protocol.handle("app", serve);
    const ses = session.defaultSession;
    const ok = new Set(["fileSystem", "fullscreen", "clipboard-sanitized-write", "clipboard-read", "pointerLock", "window-management"]);
    ses.setPermissionRequestHandler((wc, perm, cb) => cb(ok.has(perm)));
    ses.setPermissionCheckHandler((wc, perm) => ok.has(perm));
    buildMenu();
    createWindow();
    setupUpdater();
    app.on("activate", () => { if (!BrowserWindow.getAllWindows().length) createWindow(); });
  });
  app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
}
