/**
 * Module Configuration for Desktop Module Splitting
 * ==================================================
 * 
 * Controls which tabs/features are available in each module build.
 * Set via NEXT_PUBLIC_MODULE environment variable at build time.
 * 
 * Module Values:
 *   "full"      — All tabs (default, full platform EXE)
 *   "nanofacs"  — NanoFACS + Dashboard + AI Chat
 *   "nta"       — NTA Analysis + Dashboard + AI Chat
 */

import type { TabType } from "./store"

export type ModuleType = "full" | "nanofacs" | "nta"

/** Current module (set at build time via env var) */
export const CURRENT_MODULE: ModuleType = 
  (process.env.NEXT_PUBLIC_MODULE as ModuleType) || "full"

/** Module display names */
export const MODULE_NAMES: Record<ModuleType, string> = {
  full: "EV Analysis Platform",
  nanofacs: "NanoFACS Analysis",
  nta: "NTA Analysis",
}

/** Default port per module (avoids conflicts if multiple modules run) */
export const MODULE_PORTS: Record<ModuleType, number> = {
  full: 8000,
  nanofacs: 8001,
  nta: 8002,
}

/** Which tabs are enabled for each module */
const MODULE_TABS: Record<ModuleType, TabType[]> = {
  full: ["dashboard", "flow-cytometry", "nta", "cross-compare", "research-chat"],
  nanofacs: ["dashboard", "flow-cytometry", "research-chat"],
  nta: ["dashboard", "nta", "research-chat"],
}

/** Default active tab for each module */
export const MODULE_DEFAULT_TAB: Record<ModuleType, TabType> = {
  full: "dashboard",
  nanofacs: "flow-cytometry",
  nta: "nta",
}

/** Check if a tab is enabled for the current module */
export function isTabEnabled(tab: TabType): boolean {
  return MODULE_TABS[CURRENT_MODULE].includes(tab)
}

/** Get all enabled tabs for the current module */
export function getEnabledTabs(): TabType[] {
  return MODULE_TABS[CURRENT_MODULE]
}

/** Get the module display name */
export function getModuleName(): string {
  return MODULE_NAMES[CURRENT_MODULE]
}

/** Check if we're running in a single-module mode (not full platform) */
export function isSingleModule(): boolean {
  return CURRENT_MODULE !== "full"
}

/**
 * Get the API base URL for the current module.
 *
 * Priority:
 *   1. NEXT_PUBLIC_API_URL env var (explicit override)
 *   2. Same-origin (when frontend is served by FastAPI — EXE mode)
 *   3. Module-specific port on localhost (dev mode fallback)
 */
export function getApiBaseUrl(): string {
  // Explicit override always wins
  const envUrl = process.env.NEXT_PUBLIC_API_URL
  if (envUrl) {
    return envUrl.replace(/\/api\/v1$/, "")
  }

  // In the browser: if NOT on the Next.js dev port (3000), the frontend is
  // served by FastAPI on the same origin → use same-origin (no CORS needed)
  if (typeof window !== "undefined") {
    const port = parseInt(window.location.port, 10)
    if (port !== 3000) {
      return window.location.origin
    }
  }

  // Dev mode fallback: use the module-specific port
  const port = MODULE_PORTS[CURRENT_MODULE]
  return `http://localhost:${port}`
}
