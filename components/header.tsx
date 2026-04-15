"use client"

import { useEffect, useState } from "react"
import { ChevronDown, HelpCircle, Settings, User, Sun, Moon, Menu, RefreshCw, Wifi, WifiOff } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useApiConnectionState, useUIState } from "@/lib/store"
import { useApi } from "@/hooks/use-api"
import { cn } from "@/lib/utils"
import { Sidebar } from "./sidebar"
import { AlertPanel } from "./dashboard/alert-panel"
import Image from "next/image"
import { apiClient, type DesktopUser } from "@/lib/api-client"
import { isSingleModule, getModuleName } from "@/lib/module-config"

export function Header() {
  const { apiConnected, apiChecking, lastHealthCheck } = useApiConnectionState()
  const { isDarkMode, toggleDarkMode } = useUIState()
  const { checkHealth, startHealthCheck } = useApi()
  const [appVersion, setAppVersion] = useState("0.1.2")

  // DESKTOP MODE: Auto-login with real JWT token exchange
  const [currentUser, setCurrentUser] = useState<DesktopUser>({
    id: 1, name: "Lab User", email: "lab@biovaram.local", role: "researcher"
  })

  // Auto-login on mount: get real JWT token from backend
  useEffect(() => {
    apiClient.autoLogin().then((user) => {
      if (user) setCurrentUser(user)
    })
  }, [])

  // Start health check on mount
  useEffect(() => {
    const cleanup = startHealthCheck()
    return cleanup
  }, [startHealthCheck])

  // Resolve desktop runtime version from Electron main process.
  useEffect(() => {
    const desktopApi = (window as any)?.desktop
    desktopApi?.app?.getVersion?.()
      .then((result: { version?: string }) => {
        if (result?.version) {
          setAppVersion(result.version)
        }
      })
      .catch(() => {
        // Keep fallback version if desktop bridge is unavailable.
      })
  }, [])

  const formatLastCheck = () => {
    if (!lastHealthCheck) return "Never"
    const now = new Date()
    const diff = Math.floor((now.getTime() - lastHealthCheck.getTime()) / 1000)
    if (diff < 60) return `${diff}s ago`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    return lastHealthCheck.toLocaleTimeString()
  }

  const getInitials = (name?: string | null) => {
    if (!name) return "U"
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2)
  }

  return (
    <header className="h-16 border-b border-border/50 bg-card flex items-center justify-between px-3 md:px-6 shrink-0 shadow-sm">
      <div className="flex items-center gap-2 md:gap-4 min-w-0">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden h-8 w-8 shrink-0">
              <Menu className="h-4 w-4" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72 p-0">
            <Sidebar isMobile />
          </SheetContent>
        </Sheet>

        <div className="flex items-center gap-3 shrink-0">
          {/* PERFORMANCE: Use optimized WebP logo (16KB vs 1.8MB original) */}
          <div className="relative w-32 h-10 rounded-lg overflow-visible shadow-lg hover:shadow-xl transition-all">
            <Image 
              src="/logo-biovaram-optimized.webp" 
              alt="BioVaram" 
              fill 
              className="object-contain" 
              priority
              sizes="128px"
            />
          </div>
          <div className="hidden sm:flex flex-col">
            <span className="font-bold text-lg bg-linear-to-r from-orange-500 via-purple-500 to-green-500 bg-clip-text text-transparent">
              BioVaram
            </span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">
                {isSingleModule() ? getModuleName() : "EV Analysis Platform"}
              </span>
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-600 border border-emerald-500/30">
                v{appVersion}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-1.5 md:gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleDarkMode}
          className="relative h-9 w-9 rounded-xl bg-secondary/50 hover:bg-secondary transition-all duration-300 hover:scale-105"
        >
          {isDarkMode ? (
            <Sun className="h-4 w-4 text-amber-400 transition-transform" />
          ) : (
            <Moon className="h-4 w-4 text-blue-600 transition-transform" />
          )}
        </Button>

        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-secondary/50 border border-border/50">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-2 cursor-pointer" onClick={() => checkHealth()}>
                  {apiChecking ? (
                    <RefreshCw className="h-3 w-3 animate-spin text-muted-foreground" />
                  ) : apiConnected ? (
                    <Wifi className="h-3 w-3 text-emerald-500" />
                  ) : (
                    <WifiOff className="h-3 w-3 text-destructive" />
                  )}
                  <div
                    className={cn(
                      "w-2 h-2 rounded-full shrink-0",
                      apiConnected ? "bg-emerald-500 pulse-glow" : "bg-destructive",
                    )}
                  />
                  <span className="text-xs md:text-sm text-muted-foreground hidden md:block">
                    {apiChecking ? "Checking..." : apiConnected ? "API Connected" : "API Offline"}
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-xs">
                  {apiConnected ? "FastAPI backend connected" : "Cannot connect to backend"}
                </p>
                <p className="text-xs text-muted-foreground">Last check: {formatLastCheck()}</p>
                <p className="text-xs text-muted-foreground">Click to refresh</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>

        {/* CRMIT-003: Alert Panel - Dynamic alerts with timestamps */}
        <AlertPanel compact />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-1 md:gap-2 px-2 rounded-xl hover:bg-secondary/50">
              <Avatar className="h-8 w-8 ring-2 ring-primary/20">
                <AvatarFallback className="bg-linear-to-br from-primary/30 to-accent/30 text-sm font-semibold">
                  {getInitials(currentUser.name)}
                </AvatarFallback>
              </Avatar>
              <ChevronDown className="h-4 w-4 text-muted-foreground hidden sm:block" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">{currentUser.name}</p>
                <p className="text-xs leading-none text-muted-foreground">{currentUser.email}</p>
                <p className="text-xs leading-none text-muted-foreground capitalize">
                  {currentUser.role}
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              Profile
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuItem>
              <HelpCircle className="mr-2 h-4 w-4" />
              Help
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
