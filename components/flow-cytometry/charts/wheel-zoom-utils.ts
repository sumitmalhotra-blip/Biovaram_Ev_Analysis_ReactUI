export type ZoomWindow = {
  xMin: number | null
  xMax: number | null
  yMin: number | null
  yMax: number | null
}

export type PlotMargins = {
  top: number
  right: number
  bottom: number
  left: number
}

export type PlotRatios = {
  inPlot: boolean
  xRatio: number
  yRatio: number
}

const clamp = (value: number, min: number, max: number): number => Math.min(max, Math.max(min, value))

export function getPlotRatiosFromMouse(
  clientX: number,
  clientY: number,
  rect: DOMRect,
  margins: PlotMargins
): PlotRatios {
  const plotLeft = margins.left
  const plotRight = rect.width - margins.right
  const plotTop = margins.top
  const plotBottom = rect.height - margins.bottom

  const localX = clientX - rect.left
  const localY = clientY - rect.top

  const inPlot = localX >= plotLeft && localX <= plotRight && localY >= plotTop && localY <= plotBottom
  if (!inPlot) {
    return { inPlot: false, xRatio: 0.5, yRatio: 0.5 }
  }

  const plotWidth = Math.max(1, plotRight - plotLeft)
  const plotHeight = Math.max(1, plotBottom - plotTop)

  const xRatio = clamp((localX - plotLeft) / plotWidth, 0, 1)
  // Convert from SVG top-origin to data bottom-origin.
  const yRatio = clamp(1 - (localY - plotTop) / plotHeight, 0, 1)

  return { inPlot: true, xRatio, yRatio }
}

function zoomRangeAtRatio(min: number, max: number, ratio: number, zoomFactor: number): [number, number] {
  const span = max - min
  if (span <= 0) return [min, max]

  const focus = min + span * ratio
  const nextMin = focus - (focus - min) * zoomFactor
  const nextMax = focus + (max - focus) * zoomFactor

  return [nextMin, nextMax]
}

function fitRangeToBounds(
  min: number,
  max: number,
  boundsMin: number,
  boundsMax: number
): [number, number] {
  let nextMin = min
  let nextMax = max

  const span = nextMax - nextMin
  const boundsSpan = boundsMax - boundsMin

  if (span >= boundsSpan) {
    return [boundsMin, boundsMax]
  }

  if (nextMin < boundsMin) {
    const delta = boundsMin - nextMin
    nextMin += delta
    nextMax += delta
  }

  if (nextMax > boundsMax) {
    const delta = nextMax - boundsMax
    nextMin -= delta
    nextMax -= delta
  }

  return [nextMin, nextMax]
}

export function computeCursorZoomWindow(
  current: ZoomWindow,
  bounds: { minX: number; maxX: number; minY: number; maxY: number },
  ratios: { xRatio: number; yRatio: number },
  wheelDeltaY: number
): ZoomWindow {
  const zoomFactor = wheelDeltaY > 0 ? 1.2 : 0.8

  const xMin = current.xMin ?? bounds.minX
  const xMax = current.xMax ?? bounds.maxX
  const yMin = current.yMin ?? bounds.minY
  const yMax = current.yMax ?? bounds.maxY

  let [nextXMin, nextXMax] = zoomRangeAtRatio(xMin, xMax, ratios.xRatio, zoomFactor)
  let [nextYMin, nextYMax] = zoomRangeAtRatio(yMin, yMax, ratios.yRatio, zoomFactor)

  ;[nextXMin, nextXMax] = fitRangeToBounds(nextXMin, nextXMax, bounds.minX, bounds.maxX)
  ;[nextYMin, nextYMax] = fitRangeToBounds(nextYMin, nextYMax, bounds.minY, bounds.maxY)

  const almostFullX = Math.abs(nextXMin - bounds.minX) < 1e-6 && Math.abs(nextXMax - bounds.maxX) < 1e-6
  const almostFullY = Math.abs(nextYMin - bounds.minY) < 1e-6 && Math.abs(nextYMax - bounds.maxY) < 1e-6

  if (almostFullX && almostFullY) {
    return { xMin: null, xMax: null, yMin: null, yMax: null }
  }

  return {
    xMin: nextXMin,
    xMax: nextXMax,
    yMin: nextYMin,
    yMax: nextYMax,
  }
}

export function computePannedWindow(
  current: ZoomWindow,
  bounds: { minX: number; maxX: number; minY: number; maxY: number },
  deltaPixelX: number,
  deltaPixelY: number,
  plotWidth: number,
  plotHeight: number
): ZoomWindow {
  const xMin = current.xMin ?? bounds.minX
  const xMax = current.xMax ?? bounds.maxX
  const yMin = current.yMin ?? bounds.minY
  const yMax = current.yMax ?? bounds.maxY

  const xSpan = xMax - xMin
  const ySpan = yMax - yMin

  if (xSpan <= 0 || ySpan <= 0 || plotWidth <= 0 || plotHeight <= 0) {
    return current
  }

  // Dragging right moves the viewed domain left; dragging down moves viewed domain up.
  const shiftX = -(deltaPixelX / plotWidth) * xSpan
  const shiftY = (deltaPixelY / plotHeight) * ySpan

  let nextXMin = xMin + shiftX
  let nextXMax = xMax + shiftX
  let nextYMin = yMin + shiftY
  let nextYMax = yMax + shiftY

  ;[nextXMin, nextXMax] = fitRangeToBounds(nextXMin, nextXMax, bounds.minX, bounds.maxX)
  ;[nextYMin, nextYMax] = fitRangeToBounds(nextYMin, nextYMax, bounds.minY, bounds.maxY)

  const almostFullX = Math.abs(nextXMin - bounds.minX) < 1e-6 && Math.abs(nextXMax - bounds.maxX) < 1e-6
  const almostFullY = Math.abs(nextYMin - bounds.minY) < 1e-6 && Math.abs(nextYMax - bounds.maxY) < 1e-6

  if (almostFullX && almostFullY) {
    return { xMin: null, xMax: null, yMin: null, yMax: null }
  }

  return {
    xMin: nextXMin,
    xMax: nextXMax,
    yMin: nextYMin,
    yMax: nextYMax,
  }
}
