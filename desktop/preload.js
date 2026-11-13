const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("splatboxDesktop", {
  isDesktop: true, platform: process.platform,
  // Frame-by-frame video encoding through the bundled ffmpeg (ProRes, DNxHR, H.264).
  encode: {
    start: (o) => ipcRenderer.invoke("enc:start", o),
    frame: (id, bytes) => ipcRenderer.invoke("enc:frame", id, bytes),
    finish: (id) => ipcRenderer.invoke("enc:finish", id),
    cancel: (id) => ipcRenderer.invoke("enc:cancel", id)
  },
  // Inbox (V039): a watch folder of photo sets. The queue lives in the desktop shell; the app window runs one job at a time.
  inbox: {
    state: () => ipcRenderer.invoke("inbox:state"),
    config: (p) => ipcRenderer.invoke("inbox:config", p),
    scan: () => ipcRenderer.invoke("inbox:scan"),
    pick: () => ipcRenderer.invoke("inbox:pick"),
    hello: (info) => ipcRenderer.invoke("inbox:hello", info),
    read: (name, file) => ipcRenderer.invoke("inbox:read", name, file),
    report: (m) => ipcRenderer.invoke("inbox:report", m),
    onJob: (cb) => { ipcRenderer.on("inbox:job", (ev, j) => cb(j)); },
    onAbort: (cb) => { ipcRenderer.on("inbox:abort", (ev, n) => cb(n)); },
    onState: (cb) => { ipcRenderer.on("inbox:state", (ev, s) => cb(s)); }
  },
});
