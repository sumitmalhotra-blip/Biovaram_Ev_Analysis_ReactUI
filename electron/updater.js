const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const { autoUpdater } = require("electron-updater");
const fs = require("fs");
const path = require("path");

let progressWindow = null;
let isDownloadingUpdate = false;
let lastKnownUpdateVersion = null;
const RELEASE_NOTES_FALLBACK =
  "No release notes were attached to this release. This update includes stability fixes and production rollout improvements.";

function getStatePath() {
  return path.join(app.getPath("userData"), "updater-state.json");
}

function isFaultEnabled(name) {
  return String(process.env[name] || "").trim() === "1";
}

function readUpdateState() {
  try {
    const statePath = getStatePath();
    if (!fs.existsSync(statePath)) {
      return null;
    }
    return JSON.parse(fs.readFileSync(statePath, "utf8"));
  } catch {
    return null;
  }
}

function writeUpdateState(patch) {
  const existing = readUpdateState() || {};
  const next = {
    ...existing,
    ...patch,
    updatedAt: new Date().toISOString(),
  };

  const statePath = getStatePath();
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  fs.writeFileSync(statePath, JSON.stringify(next, null, 2), "utf8");
}

function clearUpdateState() {
  try {
    const statePath = getStatePath();
    if (fs.existsSync(statePath)) {
      fs.unlinkSync(statePath);
    }
  } catch {
    // Ignore state cleanup issues; they are non-fatal.
  }
}

async function checkPreviousUpdateAttempt({ mainWindow, currentVersion }) {
  const state = readUpdateState();
  if (!state) {
    return;
  }

  // If install was attempted but version did not advance, we are still on last good build.
  if (state.stage === "install-started" && state.targetVersion && state.targetVersion !== currentVersion) {
    if (isFaultEnabled("CRMIT_TEST_AUTO_ACK_DIALOGS")) {
      clearUpdateState();
      return;
    }

    await dialog.showMessageBox(mainWindow, {
      type: "warning",
      buttons: ["OK"],
      defaultId: 0,
      cancelId: 0,
      noLink: true,
      title: "Update Failed - Reverted",
      message: `Update to v${state.targetVersion} failed.`,
      detail:
        `The app is running the last successful version (v${currentVersion}).\n\n` +
        `Failure stage: install\n` +
        `Last known detail: ${state.lastError || "Installer did not complete."}`,
    });
    clearUpdateState();
    return;
  }

  // Successful version transition after previously started install.
  if (state.stage === "install-started" && state.targetVersion === currentVersion) {
    clearUpdateState();
    return;
  }

  // Surface prior download/check failures once.
  if (state.stage === "error" && state.lastError) {
    if (isFaultEnabled("CRMIT_TEST_AUTO_ACK_DIALOGS")) {
      clearUpdateState();
      return;
    }

    await dialog.showMessageBox(mainWindow, {
      type: "warning",
      buttons: ["OK"],
      defaultId: 0,
      cancelId: 0,
      noLink: true,
      title: "Update Error",
      message: "The previous update attempt failed.",
      detail: `Failure stage: ${state.failedStage || "unknown"}\nError: ${state.lastError}`,
    });
    clearUpdateState();
  }
}

function createProgressWindow(mainWindow) {
  if (progressWindow && !progressWindow.isDestroyed()) {
    return progressWindow;
  }

  progressWindow = new BrowserWindow({
    width: 440,
    height: 180,
    title: "Downloading Update",
    resizable: false,
    minimizable: false,
    maximizable: false,
    show: false,
    parent: mainWindow || undefined,
    modal: !!mainWindow,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const html = `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Downloading Update</title>
    <style>
      body { font-family: Segoe UI, sans-serif; margin: 16px; color: #111827; }
      .title { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
      .bar { width: 100%; height: 14px; border-radius: 7px; background: #e5e7eb; overflow: hidden; }
      .fill { height: 100%; width: 0%; background: linear-gradient(90deg, #10b981, #3b82f6); transition: width .2s ease; }
      .meta { margin-top: 8px; font-size: 13px; color: #374151; }
    </style>
  </head>
  <body>
    <div class="title">Downloading required update...</div>
    <div class="bar"><div id="fill" class="fill"></div></div>
    <div id="meta" class="meta">Preparing download...</div>
    <script>
      window.__setProgress = function(percent, transferred, total) {
        document.getElementById('fill').style.width = percent + '%';
        document.getElementById('meta').textContent = percent.toFixed(1) + '%  (' + transferred + ' / ' + total + ')';
      };
    </script>
  </body>
</html>`;

  progressWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
  progressWindow.once("ready-to-show", () => progressWindow?.show());
  progressWindow.on("closed", () => {
    progressWindow = null;
  });

  return progressWindow;
}

function closeProgressWindow() {
  if (progressWindow && !progressWindow.isDestroyed()) {
    progressWindow.close();
  }
  progressWindow = null;
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

async function startMandatoryDownload(mainWindow, logger) {
  if (isDownloadingUpdate) {
    return;
  }

  isDownloadingUpdate = true;
  writeUpdateState({
    stage: "download-started",
    targetVersion: lastKnownUpdateVersion,
    failedStage: null,
    lastError: null,
  });
  createProgressWindow(mainWindow);

  try {
    if (isFaultEnabled("CRMIT_TEST_CORRUPT_DOWNLOAD")) {
      throw new Error("Simulated corrupt download package for controlled resilience test.");
    }
    await autoUpdater.downloadUpdate();
  } catch (err) {
    isDownloadingUpdate = false;
    closeProgressWindow();
    mainWindow?.setProgressBar(-1);
    logger.error(`Update download failed: ${err?.message || err}`);
    writeUpdateState({
      stage: "error",
      targetVersion: lastKnownUpdateVersion,
      failedStage: "download",
      lastError: err?.message || String(err),
    });
    dialog.showErrorBox("Update Download Failed", `Could not download the update.\n\n${err?.message || err}`);
  }
}

function decodeHtmlEntities(text) {
  return text
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"');
}

function extractReleaseNoteLines(rawText) {
  if (!rawText) {
    return [];
  }

  const normalized = String(rawText)
    .replace(/<\s*code[^>]*>\s*\\?n\s*<\s*\/\s*code\s*>/gi, "\n")
    .replace(/\\n/g, "\n")
    .replace(/\r\n/g, "\n");

  const withBreaks = normalized
    .replace(/<\s*br\s*\/?>/gi, "\n")
    .replace(/<\s*\/\s*p\s*>/gi, "\n")
    .replace(/<\s*p[^>]*>/gi, "\n")
    .replace(/<\s*\/\s*li\s*>/gi, "\n")
    .replace(/<\s*li[^>]*>/gi, "- ")
    .replace(/<\s*\/\s*code\s*>/gi, "")
    .replace(/<\s*code[^>]*>/gi, "")
    .replace(/<[^>]+>/g, " ");

  const decoded = decodeHtmlEntities(withBreaks).replace(/\r/g, "");

  return decoded
    .split("\n")
    .map((line) => line.trim())
    .map((line) => line.replace(/^[-*]\s*/, "").replace(/^\d+\.\s*/, "").trim())
    .filter((line) => line.length > 0)
    .filter((line) => !/^what changed:?$/i.test(line))
    .filter((line) => !/^version\s+\S+\s+is\s+required/i.test(line));
}

function normalizeReleaseNotes(releaseNotes) {
  if (!releaseNotes) {
    return RELEASE_NOTES_FALLBACK;
  }

  const lines = [];

  if (typeof releaseNotes === "string") {
    lines.push(...extractReleaseNoteLines(releaseNotes));
  } else if (Array.isArray(releaseNotes)) {
    releaseNotes.forEach((entry) => {
      const versionLabel = entry?.version ? `Version ${entry.version}` : null;
      if (versionLabel) {
        lines.push(versionLabel);
      }
      lines.push(...extractReleaseNoteLines(entry?.note || ""));
    });
  } else {
    lines.push(...extractReleaseNoteLines(String(releaseNotes)));
  }

  const uniqueLines = [];
  const seen = new Set();
  lines.forEach((line) => {
    const key = line.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      uniqueLines.push(line);
    }
  });

  if (uniqueLines.length === 0) {
    return RELEASE_NOTES_FALLBACK;
  }

  return uniqueLines.slice(0, 10).map((line) => `- ${line}`).join("\n");
}

function registerUpdater({ mainWindow, logger }) {
  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = false;

  autoUpdater.on("checking-for-update", () => {
    logger.info("Checking for updates...");
    writeUpdateState({ stage: "check-started", failedStage: null, lastError: null });
    mainWindow?.webContents.send("updater:event", {
      type: "checking-for-update",
    });
  });

  autoUpdater.on("update-available", (info) => {
    logger.info(`Update available: ${info.version}`);
    lastKnownUpdateVersion = info.version;
    writeUpdateState({ stage: "available", targetVersion: info.version, failedStage: null, lastError: null });
    mainWindow?.webContents.send("updater:event", {
      type: "update-available",
      payload: info,
    });

    const notes = normalizeReleaseNotes(info.releaseNotes);

    dialog
      .showMessageBox(mainWindow, {
        type: "info",
        buttons: ["Download Update"],
        defaultId: 0,
        cancelId: 0,
        noLink: true,
        title: "Update Available",
        message: `Version ${info.version} is required for internal testing.`,
        detail: `What changed:\n\n${notes}\n\nThe update will download now and must be installed.`,
      })
      .then(() => {
        startMandatoryDownload(mainWindow, logger);
      })
      .catch((err) => {
        logger.error(`Update prompt failed: ${err?.message || err}`);
      });
  });

  autoUpdater.on("update-not-available", (info) => {
    logger.info("No updates available");
    clearUpdateState();
    mainWindow?.webContents.send("updater:event", {
      type: "update-not-available",
      payload: info,
    });
  });

  autoUpdater.on("download-progress", (progress) => {
    const percent = Math.max(0, Math.min(100, progress.percent || 0));
    mainWindow?.setProgressBar(percent / 100);

    const progressHost = createProgressWindow(mainWindow);
    if (progressHost && !progressHost.isDestroyed()) {
      const transferred = formatBytes(progress.transferred || 0);
      const total = formatBytes(progress.total || 0);
      const script = `window.__setProgress(${percent.toFixed(2)}, ${JSON.stringify(transferred)}, ${JSON.stringify(total)});`;
      progressHost.webContents.executeJavaScript(script).catch(() => {});
    }

    mainWindow?.webContents.send("updater:event", {
      type: "download-progress",
      payload: {
        percent,
        bytesPerSecond: progress.bytesPerSecond,
        transferred: progress.transferred,
        total: progress.total,
      },
    });
  });

  autoUpdater.on("update-downloaded", async (info) => {
    isDownloadingUpdate = false;
    logger.info(`Update downloaded: ${info.version}`);
    writeUpdateState({ stage: "downloaded", targetVersion: info.version, failedStage: null, lastError: null });
    closeProgressWindow();
    mainWindow?.setProgressBar(-1);
    mainWindow?.webContents.send("updater:event", {
      type: "update-downloaded",
      payload: info,
    });

    const choice = await dialog.showMessageBox(mainWindow, {
      type: "info",
      buttons: ["Install and Restart"],
      defaultId: 0,
      cancelId: 0,
      noLink: true,
      title: "Update Ready",
      message: `Version ${info.version} is ready to install.`,
      detail: "Installation is required. The app will restart to apply the update.",
    });

    if (choice.response === 0) {
      writeUpdateState({
        stage: "install-started",
        targetVersion: info.version,
        attemptedFromVersion: app.getVersion(),
        failedStage: null,
        lastError: null,
      });
      autoUpdater.quitAndInstall(false, true);
    }
  });

  autoUpdater.on("error", (err) => {
    isDownloadingUpdate = false;
    closeProgressWindow();
    mainWindow?.setProgressBar(-1);
    logger.error(`Updater error: ${err?.message || err}`);
    writeUpdateState({
      stage: "error",
      targetVersion: lastKnownUpdateVersion,
      failedStage: isDownloadingUpdate ? "download" : "check-or-install",
      lastError: err?.message || String(err),
    });
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
    await startMandatoryDownload(mainWindow, logger);
    return { status: "downloading" };
  });

  ipcMain.handle("updater:install", async () => {
    autoUpdater.quitAndInstall(false, true);
    return { status: "installing" };
  });

  return {
    checkForUpdates: async () => {
      if (isFaultEnabled("CRMIT_TEST_UNREACHABLE_PROVIDER")) {
        const simulated = new Error("Simulated unreachable update provider for deterministic resilience test.");
        writeUpdateState({
          stage: "error",
          targetVersion: lastKnownUpdateVersion,
          failedStage: "check-or-install",
          lastError: simulated.message,
        });
        throw simulated;
      }

      if (isFaultEnabled("CRMIT_TEST_CORRUPT_DOWNLOAD")) {
        await startMandatoryDownload(mainWindow, logger);
        return { status: "simulated-corrupt-download" };
      }

      return autoUpdater.checkForUpdates();
    },
  };
}

module.exports = {
  registerUpdater,
  checkPreviousUpdateAttempt,
};
