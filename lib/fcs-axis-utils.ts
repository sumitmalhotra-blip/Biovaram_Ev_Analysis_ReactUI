const FSC_FALLBACK_ORDER = ["FSC-A", "VFSC-A", "FSC-H", "VFSC-H", "FSC-W", "FSC"]
const SSC_FALLBACK_ORDER = ["SSC-A", "VSSC1-A", "SSC-H", "VSSC1-H", "VSSC2-A", "SSC-W", "SSC"]

export interface FCSAxisResolution {
  requestedX: string
  requestedY: string
  resolvedX: string
  resolvedY: string
  usedFallback: boolean
  fallbackDetails: string[]
}

const normalize = (value?: string | null) => (value || "").trim()

const findExactChannel = (channels: string[], target: string): string | null => {
  const normalizedTarget = target.toLowerCase()
  const exact = channels.find((channel) => channel.toLowerCase() === normalizedTarget)
  return exact || null
}

const findChannelByPriority = (
  channels: string[],
  priorityList: string[],
  exclude: Set<string>
): string | null => {
  for (const preferred of priorityList) {
    const exact = channels.find(
      (channel) => !exclude.has(channel) && channel.toLowerCase() === preferred.toLowerCase()
    )
    if (exact) return exact

    const partial = channels.find(
      (channel) => !exclude.has(channel) && channel.toLowerCase().includes(preferred.toLowerCase())
    )
    if (partial) return partial
  }

  return null
}

const findFirstAvailable = (channels: string[], exclude: Set<string>): string | null => {
  return channels.find((channel) => !exclude.has(channel)) || null
}

export function resolveFCSAxes(params: {
  availableChannels?: string[]
  requestedX?: string
  requestedY?: string
}): FCSAxisResolution {
  const availableChannels = Array.from(new Set((params.availableChannels || []).map(normalize).filter(Boolean)))
  const requestedX = normalize(params.requestedX) || "FSC-A"
  const requestedY = normalize(params.requestedY) || "SSC-A"

  const fallbackDetails: string[] = []

  if (availableChannels.length === 0) {
    return {
      requestedX,
      requestedY,
      resolvedX: requestedX,
      resolvedY: requestedY,
      usedFallback: false,
      fallbackDetails,
    }
  }

  let resolvedX = findExactChannel(availableChannels, requestedX)
  if (!resolvedX) {
    fallbackDetails.push(`X-axis '${requestedX}' not found.`)
    resolvedX = findChannelByPriority(availableChannels, FSC_FALLBACK_ORDER, new Set())
      || findFirstAvailable(availableChannels, new Set())
      || requestedX
  }

  const excludeForY = new Set<string>([resolvedX])
  let resolvedY = findExactChannel(availableChannels, requestedY)
  if (!resolvedY || resolvedY === resolvedX) {
    if (!resolvedY) {
      fallbackDetails.push(`Y-axis '${requestedY}' not found.`)
    } else {
      fallbackDetails.push(`Y-axis '${requestedY}' duplicates X-axis.`)
    }

    resolvedY = findChannelByPriority(availableChannels, SSC_FALLBACK_ORDER, excludeForY)
      || findFirstAvailable(availableChannels, excludeForY)
      || resolvedX
  }

  const usedFallback = resolvedX !== requestedX || resolvedY !== requestedY

  return {
    requestedX,
    requestedY,
    resolvedX,
    resolvedY,
    usedFallback,
    fallbackDetails,
  }
}