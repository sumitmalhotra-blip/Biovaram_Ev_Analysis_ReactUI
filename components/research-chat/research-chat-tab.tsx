"use client"

import type React from "react"

import { useState, useRef, useEffect, useCallback, useMemo } from "react"
import { Send, Sparkles, Loader2, RotateCcw, Upload, FileUp, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAnalysisStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/hooks/use-toast"
import { downloadChatHistory, type ChatMessageForExport } from "@/lib/export-utils"
import { getApiBaseUrl } from "@/lib/module-config"
import { DefaultChatTransport, useChat } from "ai/react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

function getMessageMarkdown(message: any): string {
  const parts = Array.isArray(message?.parts) ? (message.parts as any[]) : []
  const textParts = parts.filter((part) => part?.type === "text" && typeof part.text === "string" && part.text.trim())

  if (textParts.length > 0) {
  }

  const content = message?.content
  if (typeof content === "string" && content.trim()) {
    return content
  }

  return ""
}

function MarkdownMessage({ markdown }: { markdown: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }: any) => <p className="whitespace-pre-wrap wrap-break-word">{children}</p>,
        ul: ({ children }: any) => <ul className="list-disc pl-5 space-y-1">{children}</ul>,
        ol: ({ children }: any) => <ol className="list-decimal pl-5 space-y-1">{children}</ol>,
        li: ({ children }: any) => <li className="whitespace-pre-wrap wrap-break-word">{children}</li>,
        a: ({ children, href }: any) => (
          <a
            className="underline underline-offset-2"
            href={href}
            target="_blank"
            rel="noreferrer"
          >
            {children}
          </a>
        ),
        code: ({ inline, children }: any) => {
          if (inline) {
            return <code className="rounded bg-muted/40 px-1 py-0.5 font-mono text-xs">{children}</code>
          }
          return <code className="font-mono text-xs">{children}</code>
        },
        pre: ({ children }: any) => (
          <pre className="overflow-x-auto rounded-lg bg-muted/30 p-3">{children}</pre>
        ),
      }}
    >
      {markdown}
    </ReactMarkdown>
  )
}

const suggestedQuestions = [
  "How do I interpret flow cytometry gating strategies?",
  "What are the key parameters for EV characterization?",
  "Help me analyze my uploaded FCS file",
  "Generate a size distribution graph for my data",
  "Guide me through cross-comparing datasets",
]

export function ResearchChatTab() {
  const { addSample, pinChart } = useAnalysisStore()
  const { toast } = useToast()
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; type: string; size: number }>>([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [chatStatusMessage, setChatStatusMessage] = useState<string>("")
  const [chatAvailable, setChatAvailable] = useState<boolean>(true)
  const scrollRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [localInput, setLocalInput] = useState('')

  // DESKTOP: Chat endpoint on FastAPI backend
  const chatApiUrl = `${getApiBaseUrl()}/api/v1/chat`

  const chatTransport = useMemo(() => {
    return new DefaultChatTransport({ api: chatApiUrl })
  }, [chatApiUrl])

  const handleChatError = useCallback((error: Error) => {
    const message = error instanceof Error ? error.message : "Chat request failed."
    toast({
      title: "Chat request failed",
      description: message,
      variant: "destructive",
    })
  }, [])

  const { messages, sendMessage, status, setMessages } = useChat({
    transport: chatTransport,
    // Throttle UI updates to max once per 50 ms during streaming to prevent
    // React from exceeding its nested-update limit on fast AI responses.
    experimental_throttle: 50,
    onError: handleChatError,
  })

  // Derive isLoading from status
  const isLoading = status === 'streaming' || status === 'submitted'
  
  const sendUserMessage = (text: string, files?: File[] | FileList) => {
    const hasText = Boolean(text && text.trim())
    const hasFiles = Array.isArray(files) ? files.length > 0 : Boolean(files && files.length > 0)
    if (!hasText && !hasFiles) return
    void sendMessage({ text, files } as any)
  }
  const sendMessage = sendUserMessage

  useEffect(() => {
    if (scrollRef.current) {
      const scrollElement = scrollRef.current.querySelector("[data-radix-scroll-area-viewport]")
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight
      }
    }
  }, [messages])

  useEffect(() => {
    let cancelled = false

    const checkChatStatus = async () => {
      try {
        const response = await fetch(`${chatApiUrl}/status`)
        const data = await response.json()
        if (cancelled) return

        const available = Boolean(data?.available)
        setChatAvailable(available)
        setChatStatusMessage(data?.message || "")

        if (!available && data?.message) {
          toast({
            title: "AI chat unavailable",
            description: data.message,
            variant: "destructive",
          })
        }
      } catch {
        if (cancelled) return
        setChatAvailable(false)
        setChatStatusMessage("Could not reach chat backend status endpoint.")
      }
    }

    void checkChatStatus()
    return () => {
      cancelled = true
    }
  }, [chatApiUrl])

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files
    const files = Array.from(fileList || [])
    files.forEach((file) => {
      const fileInfo = {
        name: file.name,
        type: file.name.endsWith(".fcs") ? "fcs" : file.name.endsWith(".csv") ? "csv" : "nta",
        size: file.size,
      }
      setUploadedFiles((prev) => [...prev, fileInfo])

      // Add sample to store
      addSample({
        id: `sample-${Date.now()}`,
        name: file.name,
        type: fileInfo.type as "fcs" | "nta",
        uploadedAt: new Date(),
        analyzed: false,
      })

    })

    // Send a single message containing all attachments.
    if (fileList && fileList.length > 0) {
      const summary = files
        .map((f) => {
          const t = f.name.endsWith(".fcs") ? "FCS" : f.name.endsWith(".csv") ? "CSV" : "NTA"
          return `${f.name} (${t})`
        })
        .join(", ")

      sendUserMessage(
        `I've uploaded file(s): ${summary}. Please analyze them and provide insights about the particle distribution, concentration, and any anomalies.`,
        fileList,
      )
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const handleSuggestedQuestion = (question: string) => {
    sendUserMessage(question)
  }

  const handleResetTab = () => {
    setUploadedFiles([])
    setMessages([])
    setIsAnalyzing(false)
    toast({
      title: "Research Chat Reset",
      description: "All messages and uploaded files have been cleared.",
    })
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

    downloadChatHistory(exportMessages, format, "Research Chat", {
      uploadedFiles: uploadedFiles.length,
      sessionDate: new Date().toLocaleDateString(),
    })

    toast({
      title: "Chat Exported",
      description: `Chat history has been exported as ${format.toUpperCase()}.`,
    })
  }

  return (
    <div className="flex-1 flex flex-col h-full p-2 md:p-3 gap-2">
      {/* Header */}
      <div className="card-3d p-3 md:p-4 rounded-2xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg bg-linear-to-br from-primary to-accent flex items-center justify-center flex-shrink-0">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <div className="min-w-0">
              <h2 className="text-lg md:text-xl font-bold">AI Research Assistant</h2>
              <p className="text-xs text-muted-foreground hidden md:block">Your intelligent guide for EV analysis</p>
            </div>
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            {messages.length > 0 && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="gap-2">
                    <Download className="h-4 w-4" />
                    Export
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
            <Button variant="outline" size="sm" onClick={handleResetTab} className="gap-2">
              <RotateCcw className="h-4 w-4" />
              Reset Tab
            </Button>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-h-0 gap-2 card-3d p-3 md:p-4 rounded-2xl border border-border/50 overflow-hidden">
        {!chatAvailable && (
          <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-2 text-xs text-destructive">
            <p className="font-medium">AI chat is currently unavailable</p>
            <p className="mt-0.5">{chatStatusMessage || "Configure provider and API key, then retry."}</p>
          </div>
        )}

        <div className="flex-1 overflow-y-auto custom-scrollbar min-h-0">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-6 text-center min-h-full py-8">
              <div className="space-y-2">
                <div className="w-16 h-16 mx-auto rounded-2xl bg-linear-to-br from-primary/20 to-accent/20 flex items-center justify-center">
                  <Sparkles className="h-8 w-8 text-primary" />
                </div>
                <h3 className="text-lg md:text-xl font-semibold">Start Your Research Analysis</h3>
                <p className="text-sm text-muted-foreground max-w-md">
                  Upload your data files and let me guide you through comprehensive EV analysis with AI-powered
                  insights.
                </p>
              </div>

              {/* Upload Section */}
              <div className="w-full max-w-2xl">
                <div
                  className="card-3d border-2 border-dashed border-primary/30 p-6 md:p-8 rounded-xl hover:border-primary/60 transition-colors cursor-pointer"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                      <FileUp className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <p className="font-semibold text-sm">Drag and drop your files here</p>
                      <p className="text-xs text-muted-foreground mt-1">Supports FCS, CSV, and NTA formats</p>
                    </div>
                  </div>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".fcs,.csv"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </div>

              <div className="w-full">
                <p className="text-xs text-muted-foreground mb-3">Or ask me a question:</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 w-full">
                  {suggestedQuestions.map((question, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSuggestedQuestion(question)}
                      className="card-3d p-3 text-left text-sm hover:bg-secondary/80 transition-all rounded-xl group"
                    >
                      <p className="group-hover:text-primary transition-colors">{question}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-3 pb-3">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "flex gap-2 animate-in fade-in slide-in-from-bottom-2",
                    message.role === "user" ? "justify-end" : "justify-start",
                  )}
                >
                  <div
                    className={cn(
                      "card-3d max-w-sm md:max-w-3xl p-3 rounded-lg text-sm",
                      message.role === "user"
                        ? "bg-primary/20 text-foreground rounded-bl-none"
                        : "bg-secondary/50 text-foreground rounded-tl-none border border-border/50",
                    )}
                  >
                    <div className="leading-relaxed space-y-1">
                      {(() => {
                        const markdown = getMessageMarkdown(message as any)
                        if (!markdown) return null
                        return <MarkdownMessage markdown={markdown} />
                      })()}
                    </div>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex gap-2">
                  <div className="card-3d bg-secondary/50 p-2 rounded-lg rounded-tl-none flex gap-2 items-center">
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                    <span className="text-xs text-muted-foreground">AI Assistant analyzing...</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Uploaded Files Display - Compact */}
        {uploadedFiles.length > 0 && (
          <div className="card-3d bg-secondary/20 border border-border/30 rounded-lg p-2">
            <div className="text-xs font-medium text-muted-foreground mb-1">Files ({uploadedFiles.length})</div>
            <div className="space-y-0.5 max-h-16 overflow-y-auto custom-scrollbar">
              {uploadedFiles.map((file, idx) => (
                <div key={idx} className="flex items-center gap-1.5 text-xs">
                  <FileUp className="h-3 w-3 text-primary shrink-0" />
                  <span className="flex-1 truncate font-medium">{file.name}</span>
                  <span className="text-xs text-muted-foreground shrink-0">({(file.size / 1024).toFixed(0)}KB)</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="space-y-1.5">
        {messages.length > 0 && (
          <div className="flex gap-1 flex-wrap">
            <Button
              variant="ghost"
              size="xs"
              onClick={() => fileInputRef.current?.click()}
              className="gap-1.5 h-7 px-2 text-xs rounded-lg"
            >
              <Upload className="h-3 w-3" />
              <span className="hidden sm:inline">Add Files</span>
            </Button>
            <Button
              variant="ghost"
              size="xs"
              onClick={handleResetTab}
              className="gap-1.5 h-7 px-2 text-xs rounded-lg"
            >
              <RotateCcw className="h-3 w-3" />
              <span className="hidden sm:inline">New</span>
            </Button>
          </div>
        )}

        <div className="card-3d flex items-center gap-1.5 p-2 rounded-lg border border-border/50">
          <Input
            placeholder="Ask me anything about your data or analysis..."
            className="flex-1 border-0 bg-transparent focus-visible:ring-0 text-sm h-8"
            disabled={isLoading || !chatAvailable}
            onKeyPress={(e) => {
              if (e.key === "Enter" && !isLoading) {
                const inputEl = e.currentTarget
                if (inputEl.value.trim()) {
                  sendUserMessage(inputEl.value)
                  inputEl.value = ""
                }
              }
            }}
          />
          <Button
            disabled={isLoading || !chatAvailable}
            size="sm"
            className="h-7 w-7 rounded-md shrink-0 p-0"
            onClick={(e) => {
              const inputEl = e.currentTarget.parentElement?.querySelector("input") as HTMLInputElement
              if (inputEl?.value.trim() && !isLoading) {
                sendUserMessage(inputEl.value)
                inputEl.value = ""
              }
            }}
          >
            {isLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
          </Button>
        </div>
      </div>
    </div>
  )
}
