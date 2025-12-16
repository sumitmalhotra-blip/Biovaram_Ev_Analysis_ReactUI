"use client"

import { useState, useRef, useEffect } from "react"
import { Send, Sparkles, X, Minimize2, Maximize2, FileUp, Loader2, Pin, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { useAnalysisStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport } from "ai"
import { useToast } from "@/hooks/use-toast"
import { downloadChatHistory, type ChatMessageForExport } from "@/lib/export-utils"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { FCSResult, NTAResult } from "@/lib/api-client"

interface DashboardAIChatProps {
  onMinimize?: () => void
  isMinimized?: boolean
}

export function DashboardAIChat({ onMinimize, isMinimized = false }: DashboardAIChatProps) {
  const { 
    pinnedCharts, 
    fcsAnalysis, 
    ntaAnalysis,
    apiSamples 
  } = useAnalysisStore()
  const { toast } = useToast()
  
  const [isExpanded, setIsExpanded] = useState(false)
  const [inputValue, setInputValue] = useState("")
  const [contextInfo, setContextInfo] = useState<string[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { messages, sendMessage, isLoading, append } = useChat({
    transport: new DefaultChatTransport({ api: "/api/research/chat" }),
    onFinish: () => {
      // Auto scroll to bottom after AI response
      scrollToBottom()
    }
  }) as any // Type assertion for compatibility

  const scrollToBottom = () => {
    if (scrollRef.current) {
      const viewport = scrollRef.current.querySelector("[data-radix-scroll-area-viewport]")
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight
      }
    }
  }

  const handleExportChat = (format: "json" | "txt" | "md") => {
    if (messages.length === 0) {
      toast({
        title: "No Messages",
        description: "There are no messages to export.",
        variant: "destructive",
      })
      return
    }

    // Convert messages to export format
    const exportMessages: ChatMessageForExport[] = messages.map((msg: any) => ({
      id: msg.id,
      role: msg.role,
      content: msg.content || "",
      parts: msg.parts,
      timestamp: new Date(),
    }))

    downloadChatHistory(exportMessages, format, "Dashboard Chat", {
      pinnedCharts: pinnedCharts.length,
      hasFcsData: !!fcsAnalysis.results,
      hasNtaData: !!ntaAnalysis.results,
      sessionDate: new Date().toLocaleDateString(),
    })

    toast({
      title: "Chat Exported",
      description: `Chat history has been exported as ${format.toUpperCase()}.`,
    })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Build context information from dashboard
  useEffect(() => {
    const context: string[] = []
    
    // Add pinned charts info
    if (pinnedCharts.length > 0) {
      context.push(`${pinnedCharts.length} chart(s) pinned on dashboard`)
    }
    
    // Add FCS data info
    if (fcsAnalysis.results) {
      const fcs = fcsAnalysis.results
      context.push(
        `FCS: ${fcs.total_events.toLocaleString()} events, ` +
        `size ${fcs.particle_size_median_nm?.toFixed(1) || 'N/A'} nm`
      )
    }
    
    // Add NTA data info
    if (ntaAnalysis.results) {
      const nta = ntaAnalysis.results
      context.push(
        `NTA: ${nta.total_particles || 'N/A'} particles, ` +
        `D50 ${nta.d50_nm?.toFixed(1) || 'N/A'} nm`
      )
    }
    
    // Add sample count
    if (apiSamples.length > 0) {
      context.push(`${apiSamples.length} sample(s) uploaded`)
    }
    
    setContextInfo(context)
  }, [pinnedCharts, fcsAnalysis, ntaAnalysis, apiSamples])

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return

    // Build context-aware message
    let contextualMessage = inputValue

    // If asking about data, include current analysis state
    if (inputValue.toLowerCase().includes("data") || 
        inputValue.toLowerCase().includes("analysis") ||
        inputValue.toLowerCase().includes("show")) {
      
      const contextDetails: string[] = []
      
      if (fcsAnalysis.results) {
        contextDetails.push(
          `FCS Data Available:\n` +
          `- Total Events: ${fcsAnalysis.results.total_events.toLocaleString()}\n` +
          `- Median Size: ${fcsAnalysis.results.particle_size_median_nm?.toFixed(1) || 'N/A'} nm\n` +
          `- FSC Median: ${fcsAnalysis.results.fsc_median?.toLocaleString() || 'N/A'}\n` +
          `- SSC Median: ${fcsAnalysis.results.ssc_median?.toLocaleString() || 'N/A'}\n` +
          `- Debris: ${fcsAnalysis.results.debris_pct?.toFixed(1) || 'N/A'}%`
        )
      }
      
      if (ntaAnalysis.results) {
        contextDetails.push(
          `NTA Data Available:\n` +
          `- Total Particles: ${ntaAnalysis.results.total_particles || 'N/A'}\n` +
          `- D50: ${ntaAnalysis.results.d50_nm?.toFixed(1) || 'N/A'} nm\n` +
          `- Concentration: ${ntaAnalysis.results.concentration_particles_ml?.toExponential(2) || 'N/A'} particles/ml`
        )
      }
      
      if (pinnedCharts.length > 0) {
        contextDetails.push(
          `Pinned Charts: ${pinnedCharts.map(c => c.title).join(", ")}`
        )
      }
      
      if (contextDetails.length > 0) {
        contextualMessage += "\n\nCurrent Dashboard Context:\n" + contextDetails.join("\n\n")
      }
    }

    await append({
      role: "user",
      content: contextualMessage,
    })

    setInputValue("")
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (files.length === 0) return

    for (const file of files) {
      const fileType = file.name.endsWith(".fcs") ? "FCS" : 
                      file.name.endsWith(".csv") || file.name.endsWith(".txt") ? "NTA" : 
                      "Unknown"
      
      await append({
        role: "user",
        content: `I've uploaded a ${fileType} file: ${file.name} (${(file.size / 1024).toFixed(1)} KB). Please analyze it and provide insights about the particle distribution, concentration, and any anomalies you detect.`,
      })
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const suggestedPrompts = [
    "Analyze my current FCS data",
    "Compare FCS and NTA results",
    "Show me particle size distribution",
    "What are the quality metrics?",
    "Generate a report summary",
  ]

  const handleSuggestedPrompt = (prompt: string) => {
    setInputValue(prompt)
  }

  if (isMinimized) {
    return (
      <Card className="card-3d cursor-pointer hover:scale-[1.02] transition-transform">
        <CardContent 
          className="p-6 flex items-center justify-between"
          onClick={onMinimize}
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-linear-to-br from-primary to-accent flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-sm">Dashboard AI Assistant</h3>
              <p className="text-xs text-muted-foreground">Click to open chat</p>
            </div>
          </div>
          {messages.length > 0 && (
            <Badge variant="default" className="ml-auto">
              {messages.length} message{messages.length !== 1 ? 's' : ''}
            </Badge>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={cn(
      "card-3d shadow-2xl border-2 border-primary/20 transition-all duration-300",
      isExpanded ? "h-[700px]" : "h-[600px]"
    )}>
      {/* Header */}
      <CardHeader className="p-4 border-b bg-linear-to-r from-primary/10 to-accent/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-linear-to-br from-primary to-accent flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-sm">Dashboard AI Assistant</h3>
              {contextInfo.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  {contextInfo[0]}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Download className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => handleExportChat("md")}>
                    Export as Markdown
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleExportChat("json")}>
                    Export as JSON
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleExportChat("txt")}>
                    Export as Text
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>
            {onMinimize && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={onMinimize}
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>

        {/* Context Pills */}
        {contextInfo.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {contextInfo.slice(0, 3).map((info, idx) => (
              <Badge key={idx} variant="secondary" className="text-xs">
                {info}
              </Badge>
            ))}
          </div>
        )}
      </CardHeader>

      {/* Chat Content */}
      <CardContent className="p-0 flex flex-col" style={{ height: isExpanded ? 'calc(700px - 140px)' : 'calc(600px - 140px)' }}>
        <ScrollArea ref={scrollRef} className="flex-1 p-4" style={{ height: '100%' }}>
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-4 text-center py-8">
              <div className="w-16 h-16 rounded-2xl bg-linear-to-br from-primary/20 to-accent/20 flex items-center justify-center">
                <Sparkles className="h-8 w-8 text-primary" />
              </div>
              <div>
                <h4 className="font-semibold mb-2">AI Dashboard Assistant</h4>
                <p className="text-sm text-muted-foreground max-w-sm">
                  I can analyze your data, explain results, generate visualizations, and answer questions about your EV analysis.
                </p>
              </div>
              
              {/* Suggested Prompts */}
              <div className="w-full mt-4">
                <p className="text-xs text-muted-foreground mb-2">Try asking:</p>
                <div className="grid grid-cols-1 gap-2">
                  {suggestedPrompts.map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSuggestedPrompt(prompt)}
                      className="text-left text-xs p-2 rounded-lg hover:bg-secondary/80 transition-colors border border-border/50"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>

              {/* Upload Option */}
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={() => fileInputRef.current?.click()}
              >
                <FileUp className="h-4 w-4 mr-2" />
                Upload File
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".fcs,.csv,.txt"
                onChange={handleFileUpload}
                className="hidden"
              />
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message: any, idx: number) => (
                <div
                  key={idx}
                  className={cn(
                    "flex gap-3",
                    message.role === "user" ? "justify-end" : "justify-start"
                  )}
                >
                  {message.role === "assistant" && (
                    <div className="w-8 h-8 rounded-lg bg-linear-to-br from-primary/20 to-accent/20 flex items-center justify-center shrink-0">
                      <Sparkles className="h-4 w-4 text-primary" />
                    </div>
                  )}
                  <div
                    className={cn(
                      "rounded-2xl p-3 max-w-[80%] text-sm",
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-secondary"
                    )}
                  >
                    <p className="whitespace-pre-wrap">{(message as any).content || ""}</p>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg bg-linear-to-br from-primary/20 to-accent/20 flex items-center justify-center">
                    <Loader2 className="h-4 w-4 text-primary animate-spin" />
                  </div>
                  <div className="rounded-2xl p-3 bg-secondary text-sm">
                    <span className="text-muted-foreground">Analyzing...</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </ScrollArea>

        {/* Input Area */}
        <div className="p-4 border-t bg-background/50 shrink-0">
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="icon"
              className="shrink-0"
              onClick={() => fileInputRef.current?.click()}
              title="Upload file"
            >
              <FileUp className="h-4 w-4" />
            </Button>
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder="Ask about your data..."
              className="flex-1"
              disabled={isLoading}
            />
            <Button
              onClick={handleSend}
              disabled={!inputValue.trim() || isLoading}
              className="shrink-0"
              title="Send message"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
