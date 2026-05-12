const { app, BrowserWindow, dialog, ipcMain, session, Menu, shell } = require("electron");
const fs = require("fs");
const path = require("path");
const { BackendManager } = require("./backend-manager");
const { APP_NAME } = require("./constants");

let mainWindow = null;
let backendManager = null;
let updater = null;
const BUG_REPORT_FORM_URL =
  "https://docs.google.com/forms/d/e/1FAIpQLSdL7m2B3IB5RawcL_LSFlUuGfp-qm5p4U7ydUM0iMSHZBf3mg/viewform?usp=preview";

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

function getAppDataRoot() {
  // Mirror backend/run_desktop.py: %APPDATA%/BioVaram on Windows.
  if (process.platform === "win32") {
    return path.join(process.env.APPDATA || app.getPath("appData"), "BioVaram");
  }
  if (process.platform === "darwin") {
    return path.join(app.getPath("home"), "Library", "Application Support", "BioVaram");
  }
  return path.join(app.getPath("home"), ".biovaram");
}

async function resetAppData() {
  const win = mainWindow ?? BrowserWindow.getFocusedWindow();
  const choice = await dialog.showMessageBox(win ?? undefined, {
    type: "warning",
    buttons: ["Cancel", "Reset and Restart"],
    defaultId: 0,
    cancelId: 0,
    title: "Reset App Data",
    message: "Reset BioVaram to a fresh state?",
    detail:
      "This will permanently delete the local database, all uploaded FCS / NTA files, parquet caches, " +
      "and any pinned charts or settings. The platform will then restart so you can begin again.\n\n" +
      "Cloud / gateway credentials shipped with the app are not affected.",
  });
  if (choice.response !== 1) return;

  const dataRoot = getAppDataRoot();
  const userDataRoot = app.getPath("userData");
  logger.info(`Reset App Data: clearing ${dataRoot} and ${userDataRoot}`);

  // Stop the backend so its sqlite handle is released before we delete files.
  try {
    if (backendManager?.stop) {
      await backendManager.stop();
    }
  } catch (err) {
    logger.error(`Backend stop during reset failed: ${err?.message || err}`);
  }

  const removalErrors = [];
  for (const target of [dataRoot, userDataRoot]) {
    try {
      if (fs.existsSync(target)) {
        fs.rmSync(target, { recursive: true, force: true });
      }
    } catch (err) {
      removalErrors.push(`${target}: ${err?.message || err}`);
    }
  }

  if (removalErrors.length > 0) {
    logger.error(`Reset App Data partial failure: ${removalErrors.join(" | ")}`);
    await dialog.showMessageBox(win ?? undefined, {
      type: "error",
      buttons: ["OK"],
      title: "Reset App Data — Partial Failure",
      message: "Some files could not be removed.",
      detail:
        removalErrors.join("\n\n") +
        "\n\nClose any other apps that may have these files open and try again.",
    });
    return;
  }

  // Restart so the backend re-initialises a clean database on next boot.
  app.relaunch();
  app.exit(0);
}

function configureApplicationMenu() {
  const baseTemplate = [];

  if (process.platform === "darwin") {
    baseTemplate.push({ role: "appMenu" });
  }

  baseTemplate.push(
    {
      label: "File",
      submenu: [
        {
          label: "Reset App Data…",
          click: () => {
            resetAppData().catch((err) => {
              logger.error(`Reset App Data failed: ${err?.message || err}`);
              dialog.showErrorBox(
                "Reset App Data Failed",
                `Could not reset app data.\n\n${err?.message || err}`
              );
            });
          },
        },
        { type: "separator" },
        process.platform === "darwin" ? { role: "close" } : { role: "quit" },
      ],
    },
    { role: "editMenu" },
    { role: "viewMenu" },
    { role: "windowMenu" },
    {
      label: "Bug Report",
      submenu: [
        {
          label: "Report an Issue",
          click: () => {
            shell.openExternal(BUG_REPORT_FORM_URL).catch((err) => {
              logger.error(`Failed to open bug report form: ${err?.message || err}`);
              dialog.showErrorBox(
                "Bug Report Link Failed",
                `Could not open the bug report form.\n\n${err?.message || err}`
              );
            });
          },
        },
      ],
    },
    { role: "help" }
  );

  const menu = Menu.buildFromTemplate(baseTemplate);
  Menu.setApplicationMenu(menu);
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
    configureApplicationMenu();
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
