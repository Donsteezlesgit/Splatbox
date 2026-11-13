// Splatbox desktop shell. Serves the released app from an app:// origin (stable storage, secure context)
// and updates itself in place from GitHub Releases.
const { app, BrowserWindow, protocol, session, shell, dialog, Menu } = require("electron");
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
