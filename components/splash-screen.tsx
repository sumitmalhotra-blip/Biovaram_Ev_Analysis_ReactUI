"use client"

import { useEffect, useState } from "react"
import { apiClient } from "@/lib/api-client"
import { Loader2, CheckCircle2, XCircle, Wifi } from "lucide-react"

interface SplashScreenProps {
  onReady: () => void
}

type StartupStep = {
  label: string
  status: "pending" | "active" | "done" | "error"
}

export function SplashScreen({ onReady }: SplashScreenProps) {
  const [steps, setSteps] = useState<StartupStep[]>([
    { label: "Connecting to backend", status: "active" },
    { label: "Authenticating", status: "pending" },
    { label: "Loading platform", status: "pending" },
  ])
  const [error, setError] = useState<string | null>(null)
  const [retrying, setRetrying] = useState(false)

  const updateStep = (index: number, status: StartupStep["status"]) => {
    setSteps((prev) => {
      const next = [...prev]
      next[index] = { ...next[index], status }
      return next
    })
  }

  const runStartup = async () => {
    setError(null)
    setRetrying(false)

    // Step 1: Wait for backend to be reachable
    updateStep(0, "active")
    updateStep(1, "pending")
    updateStep(2, "pending")

    let backendReady = false
    for (let attempt = 0; attempt < 15; attempt++) {
      try {
        await apiClient.checkHealth()
        backendReady = true
        break
      } catch {
        // Backend not ready yet — wait and retry
        await new Promise((r) => setTimeout(r, 1000))
      }
    }

    if (!backendReady) {
      updateStep(0, "error")
      setError("Could not connect to backend. Make sure the server is running on localhost:8000.")
      return
    }
    updateStep(0, "done")

    // Step 2: Auto-login
    updateStep(1, "active")
    try {
      await apiClient.autoLogin()
      updateStep(1, "done")
    } catch {
      // Non-fatal — continue with fallback user
      updateStep(1, "done")
    }

    // Step 3: Ready
    updateStep(2, "active")
    await new Promise((r) => setTimeout(r, 400)) // Brief pause for visual feedback
    updateStep(2, "done")

    // Small delay then transition to app
    await new Promise((r) => setTimeout(r, 300))
    onReady()
  }

  useEffect(() => {
    runStartup()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleRetry = () => {
    setRetrying(true)
    runStartup()
  }

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-linear-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="flex flex-col items-center gap-8 max-w-md px-6">
        {/* Logo / Brand */}
        <div className="flex flex-col items-center gap-3">
          <div className="relative">
            <div className="w-20 h-20 rounded-2xl bg-linear-to-br from-orange-500 via-purple-500 to-green-500 flex items-center justify-center shadow-2xl shadow-purple-500/20">
              <span className="text-3xl font-black text-white tracking-tighter">BV</span>
            </div>
            <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-slate-900 flex items-center justify-center ring-2 ring-slate-800">
              <Wifi className="h-3 w-3 text-emerald-400" />
            </div>
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold bg-linear-to-r from-orange-400 via-purple-400 to-green-400 bg-clip-text text-transparent">
              BioVaram
            </h1>
            <p className="text-sm text-slate-400 mt-1">EV Analysis Platform — Desktop Edition</p>
          </div>
        </div>

        {/* Progress Steps */}
        <div className="w-full space-y-3 bg-slate-900/50 rounded-xl p-5 border border-slate-800">
          {steps.map((step, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="w-5 h-5 flex items-center justify-center shrink-0">
                {step.status === "active" && (
                  <Loader2 className="h-4 w-4 animate-spin text-purple-400" />
                )}
                {step.status === "done" && (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                )}
                {step.status === "error" && (
                  <XCircle className="h-4 w-4 text-red-400" />
                )}
                {step.status === "pending" && (
                  <div className="w-2 h-2 rounded-full bg-slate-600" />
                )}
              </div>
              <span
                className={`text-sm ${
                  step.status === "active"
                    ? "text-white"
                    : step.status === "done"
                    ? "text-emerald-300"
                    : step.status === "error"
                    ? "text-red-300"
                    : "text-slate-500"
                }`}
              >
                {step.label}
              </span>
            </div>
          ))}
        </div>

        {/* Error State */}
        {error && (
          <div className="w-full space-y-3 text-center">
            <p className="text-sm text-red-300">{error}</p>
            <button
              onClick={handleRetry}
              disabled={retrying}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-purple-600/30 text-purple-200 hover:bg-purple-600/50 border border-purple-500/30 transition-colors disabled:opacity-50"
            >
              {retrying ? "Retrying..." : "Retry Connection"}
            </button>
          </div>
        )}

        {/* Version */}
        <p className="text-xs text-slate-600">v1.0.0</p>
      </div>
    </div>
  )
}
