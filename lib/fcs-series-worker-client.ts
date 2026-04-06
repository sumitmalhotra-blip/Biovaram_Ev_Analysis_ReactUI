type ScatterPoint = {
  x: number
  y: number
  index?: number
  diameter?: number
}

type HistogramPoint = {
  bin: string
  binValue: number
  primary: number
  secondary: number
}

type BuildScatterSeriesRequest = {
  task: "buildScatterSeries"
  requestId: number
  payload: {
    points: ScatterPoint[]
    maxPoints?: number
  }
}

type BuildOverlayHistogramRequest = {
  task: "buildOverlayHistogram"
  requestId: number
  payload: {
    primaryValues: number[]
    secondaryValues: number[]
    primaryMean: number
    primaryStd: number
    secondaryMean: number
    secondaryStd: number
    bins?: number
  }
}

type FCSSeriesWorkerRequest = BuildScatterSeriesRequest | BuildOverlayHistogramRequest

type WorkerSuccessResponse = {
  task: FCSSeriesWorkerRequest["task"]
  requestId: number
  ok: true
  payload: unknown
}

type WorkerErrorResponse = {
  task: FCSSeriesWorkerRequest["task"]
  requestId: number
  ok: false
  error: string
}

type FCSSeriesWorkerResponse = WorkerSuccessResponse | WorkerErrorResponse

type PendingRequest = {
  resolve: (value: unknown) => void
  reject: (reason?: unknown) => void
  timeoutId: ReturnType<typeof setTimeout>
}

let workerInstance: Worker | null = null
const pendingRequests = new Map<number, PendingRequest>()

function rejectAllPending(reason: string): void {
  for (const [requestId, pending] of pendingRequests.entries()) {
    clearTimeout(pending.timeoutId)
    pending.reject(new Error(reason))
    pendingRequests.delete(requestId)
  }
}

function ensureWorker(): Worker {
  if (typeof window === "undefined" || typeof Worker === "undefined") {
    throw new Error("Web Worker is not available in this environment")
  }

  if (workerInstance) {
    return workerInstance
  }

  const worker = new Worker(new URL("./workers/fcs-series.worker.ts", import.meta.url))

  worker.onmessage = (event: MessageEvent<FCSSeriesWorkerResponse>) => {
    const response = event.data
    const pending = pendingRequests.get(response.requestId)
    if (!pending) {
      return
    }

    clearTimeout(pending.timeoutId)
    pendingRequests.delete(response.requestId)

    if (response.ok) {
      pending.resolve(response.payload)
    } else {
      pending.reject(new Error(response.error || "Worker task failed"))
    }
  }

  worker.onerror = () => {
    rejectAllPending("Worker encountered an error")
    worker.terminate()
    workerInstance = null
  }

  workerInstance = worker
  return worker
}

function postWorkerRequest<TPayload>(request: FCSSeriesWorkerRequest): Promise<TPayload> {
  const worker = ensureWorker()

  return new Promise<TPayload>((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      pendingRequests.delete(request.requestId)
      reject(new Error(`Worker request timed out: ${request.task}`))
    }, 15000)

    pendingRequests.set(request.requestId, {
      resolve: (value) => resolve(value as TPayload),
      reject,
      timeoutId,
    })

    worker.postMessage(request)
  })
}

export async function runScatterSeriesWorker(
  requestId: number,
  payload: BuildScatterSeriesRequest["payload"]
): Promise<{ points: ScatterPoint[] }> {
  return postWorkerRequest<{ points: ScatterPoint[] }>({
    task: "buildScatterSeries",
    requestId,
    payload,
  })
}

export async function runOverlayHistogramWorker(
  requestId: number,
  payload: BuildOverlayHistogramRequest["payload"]
): Promise<{ data: HistogramPoint[]; isApproximate: boolean }> {
  return postWorkerRequest<{ data: HistogramPoint[]; isApproximate: boolean }>({
    task: "buildOverlayHistogram",
    requestId,
    payload,
  })
}
