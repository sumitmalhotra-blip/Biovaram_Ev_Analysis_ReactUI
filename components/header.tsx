"use client"

import { useEffect } from "react"
import { Bell, ChevronDown, HelpCircle, LogOut, Settings, User, Sun, Moon, Menu, RefreshCw, Wifi, WifiOff } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useAnalysisStore } from "@/lib/store"
import { useApi } from "@/hooks/use-api"
import { cn } from "@/lib/utils"
import { Sidebar } from "./sidebar"
import Image from "next/image"

export function Header() {
  const { apiConnected, apiChecking, isDarkMode, toggleDarkMode, lastHealthCheck } = useAnalysisStore()
  const { checkHealth, startHealthCheck } = useApi()

  // Start health check on mount
  useEffect(() => {
    const cleanup = startHealthCheck()
    return cleanup
  }, [startHealthCheck])

  const formatLastCheck = () => {
    if (!lastHealthCheck) return "Never"
    const now = new Date()
    const diff = Math.floor((now.getTime() - lastHealthCheck.getTime()) / 1000)
    if (diff < 60) return `${diff}s ago`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    return lastHealthCheck.toLocaleTimeString()
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
          <div className="relative w-32 h-10 rounded-lg overflow-visible shadow-lg hover:shadow-xl transition-all">
            <Image src="/logo-biovaram.png" alt="BioVaram" fill className="object-contain" priority />
          </div>
          <div className="hidden sm:flex flex-col">
            <span className="font-bold text-lg bg-gradient-to-r from-orange-500 via-purple-500 to-green-500 bg-clip-text text-transparent">
              BioVaram
            </span>
            <span className="text-xs text-muted-foreground">EV Analysis Platform</span>
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
                  {apiConnected ? "FastAPI backend at localhost:8000" : "Cannot connect to backend"}
                </p>
                <p className="text-xs text-muted-foreground">Last check: {formatLastCheck()}</p>
                <p className="text-xs text-muted-foreground">Click to refresh</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="relative h-9 w-9 hidden sm:flex rounded-xl hover:bg-secondary/50"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-primary rounded-full text-[10px] flex items-center justify-center text-primary-foreground font-bold">
            3
          </span>
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-1 md:gap-2 px-2 rounded-xl hover:bg-secondary/50">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/30 to-accent/30 flex items-center justify-center ring-2 ring-primary/20">
                <User className="h-4 w-4 text-primary" />
              </div>
              <ChevronDown className="h-4 w-4 text-muted-foreground hidden sm:block" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuItem>
              <HelpCircle className="mr-2 h-4 w-4" />
              Help
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive">
              <LogOut className="mr-2 h-4 w-4" />
              Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
