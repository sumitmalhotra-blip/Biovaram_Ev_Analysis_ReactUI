export interface FCSNormalizationSchema {
  sampleId: string
  nativeChannels: string[]
  canonicalToNative: Record<string, string>
  nativeToCanonical: Record<string, string>
  unitsByCanonical: Record<string, string>
  warnings: string[]
}

export interface FCSNormalizationSummary {
  schemasBySampleId: Record<string, FCSNormalizationSchema>
  warnings: string[]
}

const CANONICAL_RULES: Array<{
  canonical: string
  aliases: RegExp[]
  unit: string
}> = [
  { canonical: "FSC-A", aliases: [/^FSC([\s_-]?A)?$/i, /^FSCA$/i], unit: "a.u." },
  { canonical: "FSC-H", aliases: [/^FSC([\s_-]?H)$/i, /^FSCH$/i], unit: "a.u." },
  { canonical: "SSC-A", aliases: [/^SSC([\s_-]?A)?$/i, /^SSCA$/i], unit: "a.u." },
  { canonical: "SSC-H", aliases: [/^SSC([\s_-]?H)$/i, /^SSCH$/i], unit: "a.u." },
  { canonical: "VSSC1-A", aliases: [/^VSSC1([\s_-]?A)?$/i, /^VSSC([\s_-]?1)?([\s_-]?A)?$/i], unit: "a.u." },
  { canonical: "VSSC2-A", aliases: [/^VSSC2([\s_-]?A)?$/i, /^VSSC([\s_-]?2)?([\s_-]?A)?$/i], unit: "a.u." },
  { canonical: "BSSC-A", aliases: [/^BSSC([\s_-]?A)?$/i], unit: "a.u." },
]

function normalizeToken(value: string): string {
  return value.trim().replace(/\s+/g, " ")
}

function toCanonical(rawChannel: string): string | null {
  const channel = normalizeToken(rawChannel)

  for (const rule of CANONICAL_RULES) {
    if (rule.aliases.some((alias) => alias.test(channel))) {
      return rule.canonical
    }
  }

  return null
}

function inferUnit(canonicalChannel: string | null): string {
  if (!canonicalChannel) {
    return "unknown"
  }

  const matched = CANONICAL_RULES.find((rule) => rule.canonical === canonicalChannel)
  return matched?.unit ?? "unknown"
}

export function normalizeFCSChannels(sampleId: string, channels: string[]): FCSNormalizationSchema {
  const nativeChannels = Array.from(new Set(channels.map(normalizeToken).filter(Boolean)))
  const canonicalToNative: Record<string, string> = {}
  const nativeToCanonical: Record<string, string> = {}
  const unitsByCanonical: Record<string, string> = {}
  const warnings: string[] = []

  nativeChannels.forEach((nativeChannel) => {
    const canonical = toCanonical(nativeChannel)
    if (!canonical) {
      warnings.push(`Unsupported channel preserved as native only: ${nativeChannel}`)
      nativeToCanonical[nativeChannel] = nativeChannel
      return
    }

    nativeToCanonical[nativeChannel] = canonical
    unitsByCanonical[canonical] = inferUnit(canonical)

    if (!canonicalToNative[canonical]) {
      canonicalToNative[canonical] = nativeChannel
      return
    }

    if (canonicalToNative[canonical] !== nativeChannel) {
      warnings.push(`Multiple native channels mapped to ${canonical}: ${canonicalToNative[canonical]}, ${nativeChannel}`)
    }
  })

  if (!canonicalToNative["FSC-A"] && !canonicalToNative["FSC-H"]) {
    warnings.push("No FSC channel detected for normalized compare")
  }

  if (!canonicalToNative["SSC-A"] && !canonicalToNative["SSC-H"]) {
    warnings.push("No SSC channel detected for normalized compare")
  }

  return {
    sampleId,
    nativeChannels,
    canonicalToNative,
    nativeToCanonical,
    unitsByCanonical,
    warnings,
  }
}

export function resolveChannelForSample(requestedChannel: string, schema: FCSNormalizationSchema | null): string {
  if (!schema || !requestedChannel) {
    return requestedChannel
  }

  const canonicalRequested = toCanonical(requestedChannel) ?? requestedChannel
  if (schema.canonicalToNative[canonicalRequested]) {
    return schema.canonicalToNative[canonicalRequested]
  }

  if (schema.nativeChannels.includes(requestedChannel)) {
    return requestedChannel
  }

  const fallback =
    schema.canonicalToNative["FSC-A"]
    || schema.canonicalToNative["FSC-H"]
    || schema.canonicalToNative["SSC-A"]
    || schema.nativeChannels[0]

  return fallback || requestedChannel
}

export function getNormalizedChannelOptions(schema: FCSNormalizationSchema | null, fallbackChannels: string[]): string[] {
  if (!schema) {
    return Array.from(new Set(fallbackChannels))
  }

  const canonicalChannels = Object.keys(schema.canonicalToNative)
  if (canonicalChannels.length > 0) {
    return canonicalChannels
  }

  return schema.nativeChannels.length > 0 ? schema.nativeChannels : Array.from(new Set(fallbackChannels))
}

export function formatChannelMappingLabel(schema: FCSNormalizationSchema | null, canonicalChannel: string): string {
  if (!schema) {
    return canonicalChannel
  }

  const native = schema.canonicalToNative[canonicalChannel]
  const unit = schema.unitsByCanonical[canonicalChannel]

  if (!native) {
    return `${canonicalChannel} (native: unavailable)`
  }

  return `${canonicalChannel} -> ${native} (${unit})`
}

export function buildNormalizationSummary(schemas: FCSNormalizationSchema[]): FCSNormalizationSummary {
  const schemasBySampleId: Record<string, FCSNormalizationSchema> = {}
  const warnings: string[] = []

  schemas.forEach((schema) => {
    schemasBySampleId[schema.sampleId] = schema
    schema.warnings.forEach((warning) => {
      warnings.push(`${schema.sampleId}: ${warning}`)
    })
  })

  return {
    schemasBySampleId,
    warnings,
  }
}

export function buildReplicateGroups(
  sampleIds: string[],
  mode: "none" | "prefix"
): Array<{ id: string; label: string; sampleIds: string[] }> {
  if (mode === "none") {
    return sampleIds.map((sampleId) => ({
      id: sampleId,
      label: sampleId,
      sampleIds: [sampleId],
    }))
  }

  const grouped: Record<string, string[]> = {}
  sampleIds.forEach((sampleId) => {
    const prefix = sampleId.split(/[_-]/)[0] || sampleId
    if (!grouped[prefix]) {
      grouped[prefix] = []
    }
    grouped[prefix].push(sampleId)
  })

  return Object.entries(grouped).map(([id, ids]) => ({
    id,
    label: `${id} (${ids.length})`,
    sampleIds: ids,
  }))
}
