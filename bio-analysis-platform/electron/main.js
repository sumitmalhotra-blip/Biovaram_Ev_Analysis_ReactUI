'use strict';

const { app, BrowserWindow, ipcMain, dialog, Menu, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const http = require('http');
const { autoUpdater } = require('electron-updater');

let backendProcess = null;
let backendPort = null;
let mainWindow = null;
let backendStderr = '';
let backendStdout = '';

// ---------------------------------------------------------------------------
// Poll GET /health until the backend is ready to accept requests.
// Called after BACKEND_PORT is announced (port is known but uvicorn may still
// be loading heavy imports like TensorFlow on slow machines).
// ---------------------------------------------------------------------------
function waitForBackend(port, maxWaitMs = 120000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();

    function check() {
      const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else {
          retry();
        }
        res.resume(); // drain response body
      });
      req.setTimeout(1000, () => { req.destroy(); });
      req.on('error', retry);
    }

    function retry() {
      if (Date.now() - start >= maxWaitMs) {
        reject(new Error(`Backend /health did not respond within ${maxWaitMs / 1000} s`));
        return;
      }
      setTimeout(check, 500);
    }

    check();
  });
}

// ---------------------------------------------------------------------------
// Backend spawn configuration
// Dev  : run backend_service.py directly with Python — no EXE rebuild needed
//        and stdout is always available.
// Prod : run the compiled BioLabBackend.exe (built with console=True so that
//        stdout is piped correctly; windowsHide keeps the window invisible).
// ---------------------------------------------------------------------------
function getBackendSpawn() {
  if (app.isPackaged) {
    return {
      cmd: path.join(process.resourcesPath, 'BioLabBackend', 'BioLabBackend.exe'),
      args: [],
    };
  }
  // Development — use the Python interpreter directly
  const script = path.join(__dirname, '..', 'backend', 'backend_service.py');
  return { cmd: 'python', args: [script] };
}

// ---------------------------------------------------------------------------
// Start the Python/FastAPI backend and wait for it to announce its port
// ---------------------------------------------------------------------------
function startBackend() {
  return new Promise((resolve, reject) => {
    const { cmd, args } = getBackendSpawn();

    // Dev : cwd must be the backend/ folder so backend_service.py can import local modules.
    // Prod: the EXE is self-contained (PyInstaller bundle); cwd can be anything writable.
    const cwd = app.isPackaged
      ? app.getPath('userData')                       // e.g. %APPDATA%\BioLab Suite
      : path.join(__dirname, '..', 'backend');

    // In packaged mode, verify the EXE exists before attempting to spawn.
    if (app.isPackaged && !fs.existsSync(cmd)) {
      reject(new Error(
        `BioLabBackend.exe not found at expected path:\n${cmd}\n\nresourcesPath: ${process.resourcesPath}\n\nThis installer may be corrupt — please re-download and reinstall.`
      ));
      return;
    }

    backendProcess = spawn(cmd, args, {
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
      cwd,
      env: { ...process.env, PYTHONUNBUFFERED: '1' }, // force Python stdout flush
    });

    // TensorFlow can take 60–90 s to load on a slow machine with a cold disk cache.
    // Give the backend 120 s to announce its port before giving up.
    const TIMEOUT_MS = 120000;
    const timeout = setTimeout(() => {
      reject(new Error(
        `Backend did not announce BACKEND_PORT within ${TIMEOUT_MS / 1000} s\n\nEXE path: ${cmd}\n\nStdout:\n${backendStdout || '(none)'}\n\nStderr:\n${backendStderr || '(none)'}\n\nIf this is the first run, Windows Defender may be scanning the EXE — please add the install folder to Defender exclusions and try again.`
      ));
    }, TIMEOUT_MS);

    // Track whether the health check has resolved so the exit handler
    // can reject immediately if the backend dies before becoming healthy.
    let healthResolved = false;

    backendProcess.stdout.on('data', (data) => {
      const text = data.toString();
      backendStdout += text;
      const match = text.match(/BACKEND_PORT:(\d+)/);
      if (match && !backendPort) {
        backendPort = parseInt(match[1], 10);
        clearTimeout(timeout);
        // Port is known — now wait until uvicorn is fully ready before
        // loading the frontend (heavy imports like TensorFlow can take time).
        waitForBackend(backendPort)
          .then(() => { healthResolved = true; resolve(backendPort); })
          .catch((err) => reject(new Error(
            `${err.message}\n\nStdout:\n${backendStdout || '(none)'}\n\nStderr:\n${backendStderr || '(none)'}`
          )));
      }
    });

    backendProcess.stderr.on('data', (data) => {
      backendStderr += data.toString();
    });

    backendProcess.on('error', (err) => {
      clearTimeout(timeout);
      reject(new Error(
        `Failed to start backend process: ${err.message}\n\nEXE path: ${cmd}\n\nStdout:\n${backendStdout || '(none)'}\n\nStderr:\n${backendStderr || '(none)'}`
      ));
    });

    backendProcess.on('exit', (code, signal) => {
      if (!backendPort) {
        // Died before ever announcing the port
        clearTimeout(timeout);
        reject(new Error(
          `Backend exited (code=${code} signal=${signal}) before announcing port.\n\nEXE path: ${cmd}\n\nThis is often caused by Windows Defender blocking the EXE on first run. Please add the install folder to Defender exclusions and try again.\n\nStdout:\n${backendStdout || '(none)'}\n\nStderr:\n${backendStderr || '(none)'}`
        ));
      } else if (!healthResolved) {
        // Port announced but backend crashed before /health passed (e.g. missing module)
        clearTimeout(timeout);
        reject(new Error(
          `Backend crashed during startup (code=${code}).\n\nEXE path: ${cmd}\n\nStdout:\n${backendStdout || '(none)'}\n\nStderr:\n${backendStderr || '(none)'}`
        ));
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Create the main BrowserWindow and load the bundled frontend
// ---------------------------------------------------------------------------
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      additionalArguments: [
        `--backend-url=http://127.0.0.1:${backendPort}`,
        `--app-version=${app.getVersion()}`,
      ],
    },
    show: false, // Show only after content is ready (prevents blank flash)
  });

  const frontendIndex = app.isPackaged
  ? path.join(process.resourcesPath, 'frontend', 'index.html')
  : path.join(__dirname, '..', 'frontend', 'western-blot-frontend', 'dist', 'index.html');

  mainWindow.loadFile(frontendIndex);

  // Show DevTools in dev mode to diagnose frontend errors
  if (!app.isPackaged) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.webContents.on('did-fail-load', (_e, code, desc) => {
    dialog.showErrorBox('Page failed to load', `${desc} (${code})\n\nPath: ${frontendIndex}`);
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });
}

// IPC handler kept for safety but URL is now passed via additionalArguments
ipcMain.on('get-backend-url', (event) => {
  event.returnValue = `http://127.0.0.1:${backendPort}`;
});

// Renderer requests install — triggered by "Restart Now" in UpdateBanner
ipcMain.on('install-update', () => {
  autoUpdater.quitAndInstall();
});

// ---------------------------------------------------------------------------
// Auto-updater — only active in packaged builds.
// State is cached so the renderer can fetch it any time (fixes race condition
// where update-available fires before UpdateBanner mounts its listeners).
// Also re-checks every 4 hours in case the app is left open all day.
// ---------------------------------------------------------------------------

// Cached update state — renderer reads this on mount
let _updateState = { status: 'idle', info: null, progress: null };

// Flag to distinguish manual "Check for Updates" click from background checks
let _manualCheck = false;

// Renderer calls this on mount to get current update state immediately
ipcMain.handle('get-update-state', () => _updateState);

function sendUpdate(channel, payload) {
  if (mainWindow) mainWindow.webContents.send(channel, payload);
}

function setupAutoUpdater() {
  if (!app.isPackaged) return;

  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;

  autoUpdater.on('checking-for-update', () => {
    console.log('[updater] Checking for update...');
  });

  autoUpdater.on('update-available', (info) => {
    console.log(`[updater] Update available: ${info.version}`);
    _updateState = { status: 'available', info, progress: null };
    sendUpdate('update-available', info);
  });

  autoUpdater.on('update-not-available', () => {
    console.log('[updater] App is up to date.');
    _updateState = { status: 'idle', info: null, progress: null };
    if (_manualCheck) {
      _manualCheck = false;
      dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: 'BioLab Suite',
        message: `You're on the latest version (v${app.getVersion()}).`,
      });
    }
  });

  autoUpdater.on('download-progress', (progress) => {
    const pct = Math.round(progress.percent);
    if (mainWindow) mainWindow.setProgressBar(pct / 100);
    _updateState = { status: 'downloading', info: _updateState.info, progress };
    sendUpdate('download-progress', progress);
    console.log(`[updater] Downloading: ${pct}%`);
  });

  autoUpdater.on('update-downloaded', (info) => {
    if (mainWindow) mainWindow.setProgressBar(-1);
    _updateState = { status: 'ready', info, progress: null };
    sendUpdate('update-downloaded', info);
    console.log(`[updater] Update downloaded: ${info.version}`);
  });

  autoUpdater.on('error', (err) => {
    console.error('[updater] Error:', err.message);
    _updateState = { status: 'idle', info: null, progress: null };
    sendUpdate('update-error', err.message);
  });

  // First check 5 s after startup; retry at 30 s in case first attempt
  // hits a transient network error or fires before React mounts listeners.
  // Then re-check every 4 hours for long-running sessions.
  setTimeout(() => autoUpdater.checkForUpdates(), 5000);
  setTimeout(() => autoUpdater.checkForUpdates(), 30000);
  setInterval(() => autoUpdater.checkForUpdates(), 4 * 60 * 60 * 1000);
}

// ---------------------------------------------------------------------------
// Application menu — provides "Help → Check for Updates" as a manual fallback
// so users are never stranded waiting for the background check.
// ---------------------------------------------------------------------------
function buildAppMenu() {
  const template = [
    {
      label: 'File',
      submenu: [{ role: 'quit', label: 'Exit' }],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'Bug Report',
          click() {
            shell.openExternal('https://docs.google.com/forms/d/e/1FAIpQLSdL7m2B3IB5RawcL_LSFlUuGfp-qm5p4U7ydUM0iMSHZBf3mg/viewform');
          },
        },
        { type: 'separator' },
        {
          label: 'Check for Updates',
          click() {
            if (!app.isPackaged) {
              dialog.showMessageBox(mainWindow, {
                type: 'info',
                title: 'Check for Updates',
                message: 'Auto-update is disabled in development mode.',
              });
              return;
            }
            _manualCheck = true;
            autoUpdater.checkForUpdates().catch((err) => {
              _manualCheck = false;
              dialog.showErrorBox('Update check failed', err.message);
            });
          },
        },
        { type: 'separator' },
        {
          label: `Version ${app.getVersion()}`,
          enabled: false,
        },
      ],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ---------------------------------------------------------------------------
// App lifecycle
// ---------------------------------------------------------------------------
app.whenReady().then(async () => {
  buildAppMenu();
  try {
    await startBackend();
    createWindow();
    setupAutoUpdater();
  } catch (err) {
    dialog.showErrorBox(
      'BioLab Suite — Backend failed to start',
      `Error: ${err.message}\n\nBackend output:\n${backendStderr || '(none)'}`
    );
    app.quit();
  }
});

app.on('window-all-closed', () => {
  killBackend();
  app.quit();
});

app.on('before-quit', () => {
  killBackend();
});

function killBackend() {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill('SIGTERM');
    backendProcess = null;
  }
}
