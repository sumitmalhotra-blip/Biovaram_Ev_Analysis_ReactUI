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

type FCSSeriesWorkerResponse = {
  task: FCSSeriesWorkerRequest["task"]
  requestId: number
  ok: true
  payload: unknown
}

type FCSSeriesWorkerError = {
  task: FCSSeriesWorkerRequest["task"]
  requestId: number
  ok: false
  error: string
}

const finiteNumber = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value)

function sampleScatterPoints(points: ScatterPoint[], maxPoints?: number): ScatterPoint[] {
  const filtered = points
    .filter((point) => finiteNumber(point.x) && finiteNumber(point.y))
    .map((point, idx) => ({
      x: point.x,
      y: point.y,
      index: finiteNumber(point.index) ? point.index : idx,
      diameter: finiteNumber(point.diameter) ? point.diameter : undefined,
    }))

  const capped = Math.max(1, Math.min(10000, maxPoints ?? filtered.length))
  if (filtered.length <= capped) {
    return filtered
  }

  const step = Math.ceil(filtered.length / capped)
  const sampled: ScatterPoint[] = []
  for (let idx = 0; idx < filtered.length; idx += step) {
    sampled.push(filtered[idx])
  }

  return sampled.slice(0, capped)
}

function buildHistogramSeries(payload: BuildOverlayHistogramRequest["payload"]): {
  data: HistogramPoint[]
  isApproximate: boolean
} {
  const primaryValues = payload.primaryValues.filter(finiteNumber)
  const secondaryValues = payload.secondaryValues.filter(finiteNumber)

  const hasRealPrimary = primaryValues.length > 0
  const hasRealSecondary = secondaryValues.length > 0
  const hasRealData = hasRealPrimary || hasRealSecondary

  const bins = Math.max(10, Math.min(200, payload.bins ?? 50))

  const allValues = [...primaryValues, ...secondaryValues]
  let minVal: number
  let maxVal: number

  if (allValues.length > 0) {
    const sorted = [...allValues].sort((a, b) => a - b)
    const q01 = sorted[Math.floor(sorted.length * 0.01)] ?? sorted[0]
    const q99 = sorted[Math.floor(sorted.length * 0.99)] ?? sorted[sorted.length - 1]
    minVal = q01
    maxVal = q99

    if (!hasRealPrimary) {
      minVal = Math.min(minVal, payload.primaryMean - 3 * payload.primaryStd)
      maxVal = Math.max(maxVal, payload.primaryMean + 3 * payload.primaryStd)
    }
    if (!hasRealSecondary) {
      minVal = Math.min(minVal, payload.secondaryMean - 3 * payload.secondaryStd)
      maxVal = Math.max(maxVal, payload.secondaryMean + 3 * payload.secondaryStd)
    }
  } else {
    minVal = Math.min(payload.primaryMean - 3 * payload.primaryStd, payload.secondaryMean - 3 * payload.secondaryStd)
    maxVal = Math.max(payload.primaryMean + 3 * payload.primaryStd, payload.secondaryMean + 3 * payload.secondaryStd)
  }

  if (!Number.isFinite(minVal) || !Number.isFinite(maxVal) || maxVal <= minVal) {
    return { data: [], isApproximate: true }
  }

  const binSize = (maxVal - minVal) / bins
  const data: HistogramPoint[] = []

  for (let i = 0; i < bins; i += 1) {
    const binStart = minVal + i * binSize
    const binEnd = binStart + binSize
    const binMid = binStart + binSize / 2

    const primaryValue = hasRealPrimary
      ? primaryValues.filter((value) => value >= binStart && value < binEnd).length
      : Math.exp(-0.5 * Math.pow((binMid - payload.primaryMean) / payload.primaryStd, 2)) * 100

    const secondaryValue = hasRealSecondary
      ? secondaryValues.filter((value) => value >= binStart && value < binEnd).length
      : Math.exp(-0.5 * Math.pow((binMid - payload.secondaryMean) / payload.secondaryStd, 2)) * 100

    data.push({
      bin: binMid.toFixed(0),
      binValue: binMid,
      primary: Math.round(primaryValue),
      secondary: Math.round(secondaryValue),
    })
  }

  if (hasRealPrimary !== hasRealSecondary && data.length > 0) {
    const realSide = hasRealPrimary ? "primary" : "secondary"
    const gaussSide = hasRealPrimary ? "secondary" : "primary"

    const maxReal = Math.max(...data.map((entry) => entry[realSide]), 1)
    const maxGauss = Math.max(...data.map((entry) => entry[gaussSide]), 1)
    const scale = maxReal / maxGauss

    data.forEach((entry) => {
      entry[gaussSide] = Math.round(entry[gaussSide] * scale)
    })
  }

  return { data, isApproximate: !hasRealData }
}

function postWorkerMessage(message: FCSSeriesWorkerResponse | FCSSeriesWorkerError): void {
  self.postMessage(message)
}

self.onmessage = (event: MessageEvent<FCSSeriesWorkerRequest>) => {
  const request = event.data

  try {
    if (request.task === "buildScatterSeries") {
      const points = sampleScatterPoints(request.payload.points, request.payload.maxPoints)
      postWorkerMessage({
        task: request.task,
        requestId: request.requestId,
        ok: true,
        payload: { points },
      })
      return
    }

    if (request.task === "buildOverlayHistogram") {
      const histogram = buildHistogramSeries(request.payload)
      postWorkerMessage({
        task: request.task,
        requestId: request.requestId,
        ok: true,
        payload: histogram,
      })
      return
    }

  } catch (error) {
    postWorkerMessage({
      task: request.task,
      requestId: request.requestId,
      ok: false,
      error: error instanceof Error ? error.message : "Worker execution failed",
    })
  }
}
