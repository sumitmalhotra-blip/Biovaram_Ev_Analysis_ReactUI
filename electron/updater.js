const { dialog, ipcMain } = require("electron");
const { autoUpdater } = require("electron-updater");

function normalizeReleaseNotes(releaseNotes) {
  if (!releaseNotes) {
    return "No release notes were provided for this update.";
  }

  if (typeof releaseNotes === "string") {
    return releaseNotes;
  }

  if (Array.isArray(releaseNotes)) {
    return releaseNotes
      .map((entry) => {
        const version = entry?.version ? `v${entry.version}` : "version update";
        const note = entry?.note || "No details provided.";
        return `${version}\n${note}`;
      })
      .join("\n\n");
  }

  return String(releaseNotes);
}

function registerUpdater({ mainWindow, logger }) {
  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = true;

  autoUpdater.on("checking-for-update", () => {
    logger.info("Checking for updates...");
    mainWindow?.webContents.send("updater:event", {
      type: "checking-for-update",
    });
  });

  autoUpdater.on("update-available", (info) => {
    logger.info(`Update available: ${info.version}`);
    mainWindow?.webContents.send("updater:event", {
      type: "update-available",
      payload: info,
    });

    const notes = normalizeReleaseNotes(info.releaseNotes);

    dialog
      .showMessageBox(mainWindow, {
        type: "info",
        buttons: ["Download Update", "Later"],
        defaultId: 0,
        cancelId: 1,
        title: "Update Available",
        message: `Version ${info.version} is available.`,
        detail: `What changed:\n\n${notes}`,
      })
      .then((result) => {
        if (result.response === 0) {
          autoUpdater.downloadUpdate().catch((err) => {
            logger.error(`Update download failed: ${err?.message || err}`);
          });
        }
      })
      .catch((err) => {
        logger.error(`Update prompt failed: ${err?.message || err}`);
      });
  });

  autoUpdater.on("update-not-available", (info) => {
    logger.info("No updates available");
    mainWindow?.webContents.send("updater:event", {
      type: "update-not-available",
      payload: info,
    });
  });

  autoUpdater.on("download-progress", (progress) => {
    mainWindow?.webContents.send("updater:event", {
      type: "download-progress",
      payload: {
        percent: progress.percent,
        bytesPerSecond: progress.bytesPerSecond,
        transferred: progress.transferred,
        total: progress.total,
      },
    });
  });

  autoUpdater.on("update-downloaded", async (info) => {
    logger.info(`Update downloaded: ${info.version}`);
    mainWindow?.webContents.send("updater:event", {
      type: "update-downloaded",
      payload: info,
    });

    const choice = await dialog.showMessageBox(mainWindow, {
      type: "info",
      buttons: ["Install and Restart", "Later"],
      defaultId: 0,
      cancelId: 1,
      title: "Update Ready",
      message: `Version ${info.version} is ready to install.`,
      detail: "The app will restart to apply the update.",
    });

    if (choice.response === 0) {
      autoUpdater.quitAndInstall(false, true);
    }
  });

  autoUpdater.on("error", (err) => {
    logger.error(`Updater error: ${err?.message || err}`);
    mainWindow?.webContents.send("updater:event", {
      type: "error",
      payload: {
        message: err?.message || String(err),
      },
    });
  });

  ipcMain.handle("updater:check", async () => {
    return autoUpdater.checkForUpdates();
  });

  ipcMain.handle("updater:download", async () => {
    return autoUpdater.downloadUpdate();
  });

  ipcMain.handle("updater:install", async () => {
    autoUpdater.quitAndInstall(false, true);
    return { status: "installing" };
  });

  return {
    checkForUpdates: () => autoUpdater.checkForUpdates(),
  };
}

module.exports = {
  registerUpdater,
};
