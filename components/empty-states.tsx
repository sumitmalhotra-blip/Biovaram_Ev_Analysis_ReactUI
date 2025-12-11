"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  FileX,
  Database,
  WifiOff,
  AlertCircle,
  Upload,
  RefreshCw,
  Search,
  Inbox,
  FileQuestion,
  ServerOff,
  Clock,
  Ban,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
    variant?: "default" | "outline" | "secondary"
  }
  secondaryAction?: {
    label: string
    onClick: () => void
  }
  className?: string
  compact?: boolean
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  secondaryAction,
  className,
  compact = false,
}: EmptyStateProps) {
  return (
    <Card className={cn("card-3d", className)}>
      <CardContent className={cn("flex flex-col items-center justify-center text-center", compact ? "py-8" : "py-12 md:py-16")}>
        <div className={cn(
          "rounded-full bg-muted/50 p-4 mb-4",
          compact ? "p-3" : "p-4"
        )}>
          <Icon className={cn("text-muted-foreground", compact ? "h-8 w-8" : "h-12 w-12")} />
        </div>
        <h3 className={cn("font-semibold mb-2", compact ? "text-base" : "text-lg")}>{title}</h3>
        <p className={cn("text-muted-foreground mb-6 max-w-md", compact ? "text-sm mb-4" : "text-sm md:text-base")}>
          {description}
        </p>
        {(action || secondaryAction) && (
          <div className="flex gap-3">
            {action && (
              <Button onClick={action.onClick} variant={action.variant || "default"}>
                {action.label}
              </Button>
            )}
            {secondaryAction && (
              <Button onClick={secondaryAction.onClick} variant="outline">
                {secondaryAction.label}
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Pre-built empty states for common scenarios

export function NoDataEmptyState({ onUpload }: { onUpload?: () => void }) {
  return (
    <EmptyState
      icon={Database}
      title="No Data Available"
      description="There's no data to display yet. Upload a file to get started with your analysis."
      action={onUpload ? { label: "Upload File", onClick: onUpload } : undefined}
    />
  )
}

export function NoResultsEmptyState({ onReset }: { onReset?: () => void }) {
  return (
    <EmptyState
      icon={Search}
      title="No Results Found"
      description="We couldn't find any results matching your criteria. Try adjusting your filters or search terms."
      action={onReset ? { label: "Clear Filters", onClick: onReset, variant: "outline" } : undefined}
    />
  )
}

export function NoFileUploadedEmptyState({ onUpload }: { onUpload: () => void }) {
  return (
    <EmptyState
      icon={Upload}
      title="No File Uploaded"
      description="Upload an FCS or NTA file to begin analyzing your extracellular vesicle data."
      action={{ label: "Choose File", onClick: onUpload }}
    />
  )
}

export function OfflineEmptyState({ onRetry }: { onRetry: () => void }) {
  return (
    <EmptyState
      icon={WifiOff}
      title="No Connection"
      description="Unable to connect to the analysis backend. Please check that the server is running and try again."
      action={{ label: "Retry Connection", onClick: onRetry }}
    />
  )
}

export function ServerErrorEmptyState({ onRetry, onHome }: { onRetry: () => void; onHome?: () => void }) {
  return (
    <EmptyState
      icon={ServerOff}
      title="Server Error"
      description="The server encountered an error while processing your request. Please try again or contact support if the problem persists."
      action={{ label: "Try Again", onClick: onRetry }}
      secondaryAction={onHome ? { label: "Go to Dashboard", onClick: onHome } : undefined}
    />
  )
}

export function FileParsingErrorEmptyState({ fileName, onTryAnother }: { fileName?: string; onTryAnother: () => void }) {
  return (
    <EmptyState
      icon={FileQuestion}
      title="File Parsing Failed"
      description={
        fileName
          ? `Unable to parse ${fileName}. Please ensure the file is a valid FCS or NTA file and try again.`
          : "Unable to parse the uploaded file. Please ensure it's a valid FCS or NTA file format."
      }
      action={{ label: "Try Another File", onClick: onTryAnother }}
    />
  )
}

export function TimeoutEmptyState({ onRetry }: { onRetry: () => void }) {
  return (
    <EmptyState
      icon={Clock}
      title="Request Timeout"
      description="The request took too long to complete. This might be due to a large file or slow connection. Please try again."
      action={{ label: "Retry", onClick: onRetry }}
    />
  )
}

export function AccessDeniedEmptyState({ onGoBack }: { onGoBack?: () => void }) {
  return (
    <EmptyState
      icon={Ban}
      title="Access Denied"
      description="You don't have permission to access this resource. Please contact your administrator if you believe this is an error."
      action={onGoBack ? { label: "Go Back", onClick: onGoBack, variant: "outline" } : undefined}
    />
  )
}

export function NoPinnedChartsEmptyState() {
  return (
    <EmptyState
      icon={Inbox}
      title="No Pinned Charts"
      description="Pin charts from your analyses to see them here for quick access and comparison."
      compact
    />
  )
}

export function NoSamplesEmptyState({ onUpload }: { onUpload: () => void }) {
  return (
    <EmptyState
      icon={FileX}
      title="No Samples Yet"
      description="Get started by uploading your first FCS or NTA sample file for analysis."
      action={{ label: "Upload Sample", onClick: onUpload }}
    />
  )
}

export function NoComparisonDataEmptyState() {
  return (
    <EmptyState
      icon={AlertCircle}
      title="Insufficient Data for Comparison"
      description="You need both FCS and NTA analysis results to perform a cross-comparison. Please upload and analyze files from both methods."
      compact
    />
  )
}

// Generic error display with custom message
export function ErrorDisplay({
  title = "Error",
  message,
  details,
  onRetry,
  className,
}: {
  title?: string
  message: string
  details?: string
  onRetry?: () => void
  className?: string
}) {
  return (
    <Alert variant="destructive" className={className}>
      <AlertCircle className="h-4 w-4" />
      <div className="space-y-2">
        <div className="font-medium">{title}</div>
        <AlertDescription>
          <p>{message}</p>
          {details && (
            <details className="mt-2">
              <summary className="cursor-pointer text-xs opacity-80 hover:opacity-100">
                Technical Details
              </summary>
              <p className="mt-2 text-xs font-mono bg-background/50 p-2 rounded">
                {details}
              </p>
            </details>
          )}
        </AlertDescription>
        {onRetry && (
          <Button onClick={onRetry} variant="outline" size="sm" className="mt-3 gap-2">
            <RefreshCw className="h-3 w-3" />
            Retry
          </Button>
        )}
      </div>
    </Alert>
  )
}
