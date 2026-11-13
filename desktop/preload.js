const { contextBridge } = require("electron");
contextBridge.exposeInMainWorld("splatboxDesktop", { isDesktop: true, platform: process.platform });
