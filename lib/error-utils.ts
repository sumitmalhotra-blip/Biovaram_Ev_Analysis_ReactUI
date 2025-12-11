/**
 * Retry utility with exponential backoff
 * Useful for handling transient network errors and server timeouts
 */

export interface RetryOptions {
  maxAttempts?: number
  initialDelay?: number
  maxDelay?: number
  backoffMultiplier?: number
  shouldRetry?: (error: unknown, attempt: number) => boolean
  onRetry?: (error: unknown, attempt: number) => void
}

const DEFAULT_RETRY_OPTIONS: Required<RetryOptions> = {
  maxAttempts: 3,
  initialDelay: 1000, // 1 second
  maxDelay: 10000, // 10 seconds
  backoffMultiplier: 2,
  shouldRetry: (error: unknown) => {
    // Retry on network errors and 5xx server errors
    if (error instanceof Response) {
      return error.status >= 500 && error.status < 600
    }
    // Retry on network errors (fetch failures)
    if (error instanceof TypeError && error.message.includes("fetch")) {
      return true
    }
    return false
  },
  onRetry: () => {
    // No-op by default
  },
}

/**
 * Retry a function with exponential backoff
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const opts = { ...DEFAULT_RETRY_OPTIONS, ...options }
  let lastError: unknown

  for (let attempt = 1; attempt <= opts.maxAttempts; attempt++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error

      // Don't retry if this is the last attempt
      if (attempt === opts.maxAttempts) {
        throw error
      }

      // Check if we should retry this error
      if (!opts.shouldRetry(error, attempt)) {
        throw error
      }

      // Calculate delay with exponential backoff
      const delay = Math.min(
        opts.initialDelay * Math.pow(opts.backoffMultiplier, attempt - 1),
        opts.maxDelay
      )

      // Call retry callback
      opts.onRetry(error, attempt)

      // Wait before retrying
      await new Promise((resolve) => setTimeout(resolve, delay))
    }
  }

  // This should never be reached, but TypeScript needs it
  throw lastError
}

/**
 * Create a retryable version of a fetch function
 */
export function createRetryableFetch(options: RetryOptions = {}) {
  return async <T>(fn: () => Promise<T>): Promise<T> => {
    return retryWithBackoff(fn, options)
  }
}

/**
 * Parse error message from various error types
 */
export function parseErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message
  }

  if (typeof error === "string") {
    return error
  }

  if (error && typeof error === "object" && "message" in error) {
    return String(error.message)
  }

  return "An unknown error occurred"
}

/**
 * Check if error is a network connectivity error
 */
export function isNetworkError(error: unknown): boolean {
  if (error instanceof TypeError && error.message.includes("fetch")) {
    return true
  }

  if (error instanceof Error) {
    const message = error.message.toLowerCase()
    return (
      message.includes("network") ||
      message.includes("connection") ||
      message.includes("offline") ||
      message.includes("failed to fetch")
    )
  }

  return false
}

/**
 * Check if error is a timeout error
 */
export function isTimeoutError(error: unknown): boolean {
  if (error instanceof Error) {
    const message = error.message.toLowerCase()
    return message.includes("timeout") || message.includes("timed out")
  }

  return false
}

/**
 * Check if error is a server error (5xx)
 */
export function isServerError(error: unknown): boolean {
  if (error instanceof Response) {
    return error.status >= 500 && error.status < 600
  }

  return false
}

/**
 * Check if error is a client error (4xx)
 */
export function isClientError(error: unknown): boolean {
  if (error instanceof Response) {
    return error.status >= 400 && error.status < 500
  }

  return false
}

/**
 * Get user-friendly error message based on error type
 */
export function getUserFriendlyErrorMessage(error: unknown): string {
  if (isNetworkError(error)) {
    return "Unable to connect to the server. Please check your internet connection and try again."
  }

  if (isTimeoutError(error)) {
    return "The request took too long to complete. Please try again with a smaller file or check your connection."
  }

  if (isServerError(error)) {
    return "The server encountered an error. Please try again later or contact support if the problem persists."
  }

  if (isClientError(error)) {
    if (error instanceof Response) {
      if (error.status === 400) {
        return "Invalid request. Please check your input and try again."
      }
      if (error.status === 401) {
        return "Authentication required. Please sign in and try again."
      }
      if (error.status === 403) {
        return "You don't have permission to perform this action."
      }
      if (error.status === 404) {
        return "The requested resource was not found."
      }
      if (error.status === 413) {
        return "The file is too large. Please try a smaller file."
      }
      if (error.status === 429) {
        return "Too many requests. Please wait a moment and try again."
      }
    }
    return "There was a problem with your request. Please check your input and try again."
  }

  return parseErrorMessage(error)
}

/**
 * Categorize error for logging/reporting
 */
export type ErrorCategory =
  | "network"
  | "timeout"
  | "server"
  | "client"
  | "validation"
  | "parsing"
  | "unknown"

export function categorizeError(error: unknown): ErrorCategory {
  if (isNetworkError(error)) return "network"
  if (isTimeoutError(error)) return "timeout"
  if (isServerError(error)) return "server"
  if (isClientError(error)) return "client"

  if (error instanceof Error) {
    const message = error.message.toLowerCase()
    if (message.includes("validation") || message.includes("invalid")) {
      return "validation"
    }
    if (message.includes("parse") || message.includes("json")) {
      return "parsing"
    }
  }

  return "unknown"
}
