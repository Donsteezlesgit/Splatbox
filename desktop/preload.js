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
  // Image to splat (V057): one photo -> a splat on this PC's NVIDIA card. The log is image-to-splat.log in the app's data folder.
  i2s: {
    status: () => ipcRenderer.invoke("i2s:status"),
    setup: () => ipcRenderer.invoke("i2s:setup"),
    generate: (o) => ipcRenderer.invoke("i2s:generate", o),
    cancel: () => ipcRenderer.invoke("i2s:cancel"),
    tail: () => ipcRenderer.invoke("i2s:tail"),
    openLog: () => ipcRenderer.invoke("i2s:openLog"),
    onProgress: (cb) => { ipcRenderer.on("i2s:progress", (ev, p) => cb(p)); }
  },
});
