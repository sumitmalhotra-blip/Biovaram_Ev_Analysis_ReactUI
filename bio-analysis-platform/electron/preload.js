'use strict';

const { contextBridge, ipcRenderer } = require('electron');

// Backend URL injected by main.js via additionalArguments
const arg = process.argv.find(a => a.startsWith('--backend-url='));
const backendUrl = arg ? arg.replace('--backend-url=', '') : 'http://127.0.0.1:8000';

// App version injected by main.js via additionalArguments
const verArg = process.argv.find(a => a.startsWith('--app-version='));
const appVersion = verArg ? verArg.replace('--app-version=', '') : '';

contextBridge.exposeInMainWorld('electronBridge', {
  backendUrl,
  appVersion,

  updater: {
    onUpdateAvailable:  (cb) => ipcRenderer.on('update-available',  (_, info)     => cb(info)),
    onUpdateDownloaded: (cb) => ipcRenderer.on('update-downloaded', (_, info)     => cb(info)),
    onDownloadProgress: (cb) => ipcRenderer.on('download-progress', (_, progress) => cb(progress)),
    onUpdateError:      (cb) => ipcRenderer.on('update-error',      (_, msg)      => cb(msg)),
    installUpdate:      ()   => ipcRenderer.send('install-update'),
    // Fetch cached state so UpdateBanner catches updates that fired before mount
    getUpdateState: () => ipcRenderer.invoke('get-update-state'),
  },
});
