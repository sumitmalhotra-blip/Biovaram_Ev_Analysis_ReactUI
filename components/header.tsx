"use client"

import { useEffect } from "react"
import { useSession, signOut } from "next-auth/react"
import { useRouter } from "next/navigation"
import { ChevronDown, HelpCircle, LogIn, LogOut, Settings, User, Sun, Moon, Menu, RefreshCw, Wifi, WifiOff } from "lucide-react"
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
import { useAnalysisStore } from "@/lib/store"
import { useApi } from "@/hooks/use-api"
import { cn } from "@/lib/utils"
import { Sidebar } from "./sidebar"
import { AlertPanel } from "./dashboard/alert-panel"
import Image from "next/image"

export function Header() {
  const { apiConnected, apiChecking, isDarkMode, toggleDarkMode, lastHealthCheck } = useAnalysisStore()
  const { checkHealth, startHealthCheck } = useApi()
  const { data: session, status } = useSession()
  const router = useRouter()

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

  const handleSignOut = async () => {
    await signOut({ redirect: false })
    router.push("/login")
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

        {/* CRMIT-003: Alert Panel - Dynamic alerts with timestamps */}
        <AlertPanel compact />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-1 md:gap-2 px-2 rounded-xl hover:bg-secondary/50">
              {status === "authenticated" && session?.user ? (
                <Avatar className="h-8 w-8 ring-2 ring-primary/20">
                  <AvatarFallback className="bg-linear-to-br from-primary/30 to-accent/30 text-sm font-semibold">
                    {getInitials(session.user.name)}
                  </AvatarFallback>
                </Avatar>
              ) : (
                <div className="w-8 h-8 rounded-lg bg-linear-to-br from-primary/30 to-accent/30 flex items-center justify-center ring-2 ring-primary/20">
                  <User className="h-4 w-4 text-primary" />
                </div>
              )}
              <ChevronDown className="h-4 w-4 text-muted-foreground hidden sm:block" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            {status === "authenticated" && session?.user ? (
              <>
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">{session.user.name}</p>
                    <p className="text-xs leading-none text-muted-foreground">{session.user.email}</p>
                    {session.user.role && (
                      <p className="text-xs leading-none text-muted-foreground capitalize">
                        {session.user.role.replace("_", " ")}
                      </p>
                    )}
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
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-destructive" onClick={handleSignOut}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign Out
                </DropdownMenuItem>
              </>
            ) : (
              <>
                <DropdownMenuItem onClick={() => router.push("/login")}>
                  <LogIn className="mr-2 h-4 w-4" />
                  Sign In
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => router.push("/signup")}>
                  <User className="mr-2 h-4 w-4" />
                  Create Account
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem>
                  <HelpCircle className="mr-2 h-4 w-4" />
                  Help
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
