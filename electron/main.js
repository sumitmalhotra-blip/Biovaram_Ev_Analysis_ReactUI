const { app, BrowserWindow, dialog, ipcMain, session } = require("electron");
const fs = require("fs");
const path = require("path");
const { BackendManager } = require("./backend-manager");
const { APP_NAME } = require("./constants");

let mainWindow = null;
let backendManager = null;
let updater = null;

const isDev = process.env.ELECTRON_DEV === "1";
const allowDevUpdates = process.env.ELECTRON_ENABLE_DEV_UPDATES === "1";

const logger = {
  info: (msg) => console.log(`[desktop] ${msg}`),
  error: (msg) => console.error(`[desktop] ${msg}`),
};

function createWindow(backendBaseUrl) {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1200,
    minHeight: 760,
    title: APP_NAME,
    show: false,
    backgroundColor: "#0f172a",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  const url = isDev
    ? process.env.ELECTRON_RENDERER_URL || "http://127.0.0.1:3000"
    : `${backendBaseUrl}?appVersion=${encodeURIComponent(app.getVersion())}`;

  logger.info(`Loading renderer: ${url}`);
  mainWindow.loadURL(url);
}

function getRendererCacheStatePath() {
  return path.join(app.getPath("userData"), "renderer-cache-state.json");
}

async function ensureRendererCacheFresh() {
  if (!app.isPackaged) {
    return;
  }

  const currentVersion = app.getVersion();
  const statePath = getRendererCacheStatePath();

  let lastVersion = null;
  try {
    if (fs.existsSync(statePath)) {
      const parsed = JSON.parse(fs.readFileSync(statePath, "utf8"));
      lastVersion = parsed?.lastVersion || null;
    }
  } catch {
    lastVersion = null;
  }

  if (lastVersion === currentVersion) {
    return;
  }

  logger.info(`Renderer version changed (${lastVersion || "none"} -> ${currentVersion}); clearing cache.`);
  try {
    await session.defaultSession.clearCache();
    await session.defaultSession.clearStorageData({
      storages: ["serviceworkers", "cachestorage"],
    });
  } catch (err) {
    logger.error(`Renderer cache clear failed: ${err?.message || err}`);
  }

  try {
    fs.writeFileSync(
      statePath,
      JSON.stringify(
        {
          lastVersion: currentVersion,
          updatedAt: new Date().toISOString(),
        },
        null,
        2
      ),
      "utf8"
    );
  } catch {
    // Non-fatal; cache clear should still take effect for this run.
  }
}

async function boot() {
  backendManager = new BackendManager({
    isPackaged: app.isPackaged,
    logger,
  });

  try {
    await backendManager.start();
    await ensureRendererCacheFresh();
    createWindow(backendManager.getBaseUrl());

    ipcMain.handle("backend:status", async () => ({
      running: true,
      baseUrl: backendManager.getBaseUrl(),
    }));

    ipcMain.handle("app:getVersion", async () => ({
      version: app.getVersion(),
    }));

    if (app.isPackaged || allowDevUpdates) {
      try {
        const { registerUpdater, checkPreviousUpdateAttempt } = require("./updater");
        updater = registerUpdater({ mainWindow, logger });

        await checkPreviousUpdateAttempt({
          mainWindow,
          currentVersion: app.getVersion(),
        });

        // Trigger a passive startup check; renderer can trigger manual checks too.
        updater.checkForUpdates().catch((err) => {
          logger.error(`Initial update check failed: ${err?.message || err}`);
        });
      } catch (err) {
        logger.error(`Updater initialization failed: ${err?.message || err}`);
        ipcMain.handle("updater:check", async () => ({ status: "error", message: err?.message || String(err) }));
        ipcMain.handle("updater:download", async () => ({ status: "error", message: err?.message || String(err) }));
        ipcMain.handle("updater:install", async () => ({ status: "error", message: err?.message || String(err) }));
      }
    } else {
      logger.info("Skipping auto-update checks in development mode");
      ipcMain.handle("updater:check", async () => ({ status: "disabled" }));
      ipcMain.handle("updater:download", async () => ({ status: "disabled" }));
      ipcMain.handle("updater:install", async () => ({ status: "disabled" }));
    }
  } catch (error) {
    logger.error(`Boot failed: ${error?.message || error}`);
    dialog.showErrorBox(
      "Application Startup Failed",
      `Failed to launch local services.\n\n${error?.message || error}`
    );
    await shutdown();
    app.quit();
  }
}

async function shutdown() {
  if (backendManager) {
    await backendManager.stop();
  }
}

const lock = app.requestSingleInstanceLock();
if (!lock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) {
        mainWindow.restore();
      }
      mainWindow.focus();
    }
  });

  app.whenReady().then(boot);
}

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  app.removeAllListeners("window-all-closed");
});

app.on("will-quit", (event) => {
  event.preventDefault();
  shutdown()
    .catch((err) => logger.error(`Shutdown error: ${err?.message || err}`))
    .finally(() => app.exit(0));
});
