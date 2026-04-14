const path = require("path");

const APP_NAME = "BioVaram EV Analysis";
const DEFAULT_BACKEND_PORT = 18000;
const BACKEND_HEALTH_TIMEOUT_MS = 90000;
const BACKEND_HEALTH_POLL_MS = 500;

function isDevMode() {
  return process.env.ELECTRON_DEV === "1" || !process.env.APPIMAGE && !process.resourcesPath?.includes("app.asar");
}

function getProjectRoot() {
  return path.resolve(__dirname, "..");
}

function getDevBackendPython() {
  return path.join(getProjectRoot(), "backend", "venv", "Scripts", "python.exe");
}

function getDevBackendEntry() {
  return path.join(getProjectRoot(), "backend", "run_desktop.py");
}

function getBundledBackendExe() {
  // Electron packaged app: resources/backend/BioVaram.exe
  return path.join(process.resourcesPath || "", "backend", "BioVaram.exe");
}

module.exports = {
  APP_NAME,
  DEFAULT_BACKEND_PORT,
  BACKEND_HEALTH_TIMEOUT_MS,
  BACKEND_HEALTH_POLL_MS,
  isDevMode,
  getProjectRoot,
  getDevBackendPython,
  getDevBackendEntry,
  getBundledBackendExe,
};
