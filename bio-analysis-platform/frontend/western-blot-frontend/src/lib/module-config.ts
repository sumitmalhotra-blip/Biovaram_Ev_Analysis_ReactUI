export type ModuleType = "tem_wb" | "all";

export const MODULE_TABS: Record<ModuleType, string[]> = {
  tem_wb: ["tem", "westernblot"],
  all: ["tem", "westernblot", "nta", "nanofacs"],
};

export const MODULE_DEFAULT_TAB: Record<ModuleType, string> = {
  tem_wb: "tem",
  all: "tem",
};

export function getActiveModule(): ModuleType {
  return (import.meta.env.VITE_MODULE || "all") as ModuleType;
}

export function isTabEnabled(tab: string): boolean {
  const profile = getActiveModule();
  return MODULE_TABS[profile]?.includes(tab) ?? false;
}