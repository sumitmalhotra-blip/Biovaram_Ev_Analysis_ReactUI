// In Electron, preload.js exposes window.electronBridge.backendUrl via additionalArguments.
// In plain browser dev mode, use "" so requests are relative and Vite's proxy forwards them
// to http://127.0.0.1:8000 without any cross-origin restrictions.
const API_BASE: string =
  (typeof window !== "undefined" &&
    (window as Window & { electronBridge?: { backendUrl: string } }).electronBridge?.backendUrl) ||
  "";

export const TEM_API = `${API_BASE}/tem`;
export const WESTERN_API = `${API_BASE}/western`;
export const STATIC_BASE = API_BASE;