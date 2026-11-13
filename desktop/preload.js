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
  // SHARP: one photo -> 3D splats, run on this PC (model downloaded once on first use).
  sharp: {
    status: () => ipcRenderer.invoke("sharp:status"),
    download: () => ipcRenderer.invoke("sharp:download"),
    cancel: () => ipcRenderer.invoke("sharp:cancel"),
    run: (chw, info) => ipcRenderer.invoke("sharp:run", chw, info),
    onProgress: (fn) => { ipcRenderer.removeAllListeners("sharp:progress"); ipcRenderer.on("sharp:progress", (e, m) => fn(m)); }
  }
});
