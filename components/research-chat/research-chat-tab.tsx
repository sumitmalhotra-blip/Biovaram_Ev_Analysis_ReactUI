"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Send, Sparkles, Loader2, RotateCcw, Upload, FileUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAnalysisStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport } from "ai"

const suggestedQuestions = [
  "How do I interpret flow cytometry gating strategies?",
  "What are the key parameters for EV characterization?",
  "Help me analyze my uploaded FCS file",
  "Generate a size distribution graph for my data",
  "Guide me through cross-comparing datasets",
]

export function ResearchChatTab() {
  const { addSample, addPinnedChart } = useAnalysisStore()
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; type: string; size: number }>>([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { messages, sendMessage, isLoading, append } = useChat({
    transport: new DefaultChatTransport({ api: "/api/research/chat" }),
  })

  useEffect(() => {
    if (scrollRef.current) {
      const scrollElement = scrollRef.current.querySelector("[data-radix-scroll-area-viewport]")
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight
      }
    }
  }, [messages])

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
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

      // Send message about uploaded file
      append({
        role: "user",
        content: `I've uploaded a file: ${file.name}. It contains ${fileInfo.type.toUpperCase()} data. Please analyze it and provide insights about the particle distribution, concentration, and any anomalies.`,
      })
    })

    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const handleSuggestedQuestion = (question: string) => {
    append({ role: "user", content: question })
  }

  return (
    <div className="flex-1 flex flex-col h-full p-4 md:p-6 gap-4">
      {/* Header */}
      <div className="card-3d p-4 md:p-6 rounded-2xl">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl md:text-2xl font-bold">AI Research Assistant</h2>
            <p className="text-xs md:text-sm text-muted-foreground">Your intelligent guide for EV analysis</p>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-h-0 gap-4 card-3d p-4 md:p-6 rounded-2xl border border-border/50 overflow-hidden">
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-6 text-center min-h-full py-8">
              <div className="space-y-2">
                <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center">
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
            <div className="space-y-4 pb-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "flex gap-3 animate-in fade-in slide-in-from-bottom-2",
                    message.role === "user" ? "justify-end" : "justify-start",
                  )}
                >
                  <div
                    className={cn(
                      "card-3d max-w-md md:max-w-2xl p-4 rounded-xl",
                      message.role === "user"
                        ? "bg-primary/20 text-foreground rounded-bl-none"
                        : "bg-secondary/50 text-foreground rounded-tl-none border border-border/50",
                    )}
                  >
                    <div className="text-sm leading-relaxed space-y-2">
                      {message.parts?.map((part, idx) => {
                        if (part.type === "text") {
                          return <p key={idx}>{part.text}</p>
                        }
                        return null
                      })}
                    </div>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex gap-3">
                  <div className="card-3d bg-secondary/50 p-4 rounded-xl rounded-tl-none flex gap-2 items-center">
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    <span className="text-sm text-muted-foreground">AI Assistant analyzing...</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Uploaded Files Display */}
        {uploadedFiles.length > 0 && (
          <Card className="card-3d bg-secondary/30 border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Uploaded Files</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 max-h-24 overflow-y-auto custom-scrollbar">
              {uploadedFiles.map((file, idx) => (
                <div key={idx} className="flex items-center gap-2 text-sm">
                  <FileUp className="h-4 w-4 text-primary shrink-0" />
                  <span className="flex-1 truncate">{file.name}</span>
                  <span className="text-xs text-muted-foreground shrink-0">{(file.size / 1024).toFixed(2)} KB</span>
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Input Area */}
      <div className="space-y-3">
        {messages.length > 0 && (
          <div className="flex gap-2 flex-wrap">
            <Button
              variant="outline"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              className="gap-2 rounded-xl bg-transparent"
            >
              <Upload className="h-4 w-4" />
              Upload More Files
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setUploadedFiles([])
                // Clear messages by reloading
              }}
              className="gap-2 rounded-xl bg-transparent"
            >
              <RotateCcw className="h-4 w-4" />
              Start New Analysis
            </Button>
          </div>
        )}

        <div className="card-3d flex items-center gap-2 p-2 rounded-xl border border-border/50">
          <Input
            placeholder="Ask me anything about your data or analysis methodology..."
            className="flex-1 border-0 bg-transparent focus-visible:ring-0 text-sm md:text-base"
            disabled={isLoading}
            onKeyPress={(e) => {
              if (e.key === "Enter" && !isLoading) {
                const input = e.currentTarget
                if (input.value.trim()) {
                  append({ role: "user", content: input.value })
                  input.value = ""
                }
              }
            }}
          />
          <Button
            disabled={isLoading}
            size="icon"
            className="h-8 w-8 rounded-lg shrink-0"
            onClick={(e) => {
              const input = e.currentTarget.parentElement?.querySelector("input") as HTMLInputElement
              if (input?.value.trim() && !isLoading) {
                append({ role: "user", content: input.value })
                input.value = ""
              }
            }}
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </div>
  )
}
