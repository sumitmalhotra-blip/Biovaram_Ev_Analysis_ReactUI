const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktop", {
  updater: {
    check: () => ipcRenderer.invoke("updater:check"),
    download: () => ipcRenderer.invoke("updater:download"),
    install: () => ipcRenderer.invoke("updater:install"),
    onEvent: (handler) => {
      const listener = (_, payload) => handler(payload);
      ipcRenderer.on("updater:event", listener);
      return () => ipcRenderer.removeListener("updater:event", listener);
    },
  },
  backend: {
    getStatus: () => ipcRenderer.invoke("backend:status"),
  },
  app: {
    getVersion: () => ipcRenderer.invoke("app:getVersion"),
  },
});
