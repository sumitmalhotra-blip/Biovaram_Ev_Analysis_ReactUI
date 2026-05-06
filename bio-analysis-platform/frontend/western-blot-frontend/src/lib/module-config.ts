export type ModuleType = "tem_wb";

export const MODULE_TABS: Record<ModuleType, string[]> = {
  tem_wb: ["tem", "westernblot"],
};

export const MODULE_DEFAULT_TAB: Record<ModuleType, string> = {
  tem_wb: "tem",
};

export function getActiveModule(): ModuleType {
  return (import.meta.env.VITE_MODULE || "tem_wb") as ModuleType;
}

export function isTabEnabled(tab: string): boolean {
  const profile = getActiveModule();
  return MODULE_TABS[profile]?.includes(tab) ?? false;
}