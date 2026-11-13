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
});
