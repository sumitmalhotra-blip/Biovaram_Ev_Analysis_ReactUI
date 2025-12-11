"use client"

import React, { Component, type ErrorInfo, type ReactNode } from "react"
import { AlertTriangle, RefreshCw, Home } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log error to console in development
    if (process.env.NODE_ENV === "development") {
      console.error("ErrorBoundary caught an error:", error, errorInfo)
    }

    // Call optional error callback
    this.props.onError?.(error, errorInfo)

    this.setState({
      errorInfo,
    })

    // TODO: Send to error reporting service in production
    // Example: Sentry.captureException(error, { extra: errorInfo })
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
  }

  handleGoHome = (): void => {
    window.location.href = "/"
  }

  render(): ReactNode {
    if (this.state.hasError) {
      // Custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback
      }

      // Default error UI
      return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-background">
          <Card className="max-w-2xl w-full">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-destructive/10">
                  <AlertTriangle className="h-6 w-6 text-destructive" />
                </div>
                <CardTitle className="text-xl">Something Went Wrong</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Application Error</AlertTitle>
                <AlertDescription>
                  An unexpected error occurred while rendering this component. Our team has been notified.
                </AlertDescription>
              </Alert>

              {this.state.error && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">Error Details:</p>
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border">
                    <p className="text-sm font-mono text-destructive">
                      {this.state.error.toString()}
                    </p>
                  </div>
                </div>
              )}

              {process.env.NODE_ENV === "development" && this.state.errorInfo && (
                <details className="space-y-2">
                  <summary className="text-sm font-medium text-muted-foreground cursor-pointer hover:text-foreground">
                    Stack Trace (Development Only)
                  </summary>
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border overflow-x-auto">
                    <pre className="text-xs font-mono whitespace-pre-wrap">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </div>
                </details>
              )}

              <div className="flex gap-3 pt-4">
                <Button onClick={this.handleReset} className="gap-2">
                  <RefreshCw className="h-4 w-4" />
                  Try Again
                </Button>
                <Button onClick={this.handleGoHome} variant="outline" className="gap-2">
                  <Home className="h-4 w-4" />
                  Go to Dashboard
                </Button>
              </div>

              <p className="text-xs text-muted-foreground pt-2">
                If this problem persists, please contact support with the error details above.
              </p>
            </CardContent>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}
