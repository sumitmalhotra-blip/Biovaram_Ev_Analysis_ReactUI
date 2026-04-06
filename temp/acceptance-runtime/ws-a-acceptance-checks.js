const {
  normalizeCompareSampleIds,
  normalizeVisibleSampleIds,
  buildScatterPriorityOrder,
  clampCompareLoadConfig,
  isCurrentCompareRequestVersion,
  deriveCompareSampleStatus,
  deriveOverlayHistogramRenderState,
} = require('./fcs-compare-acceptance-helpers.js')

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

// A1 acceptance proxy: compare queue + normalization behavior for 5-file scenario
const selected = ['s1','s2','s3','s4','s5']
const normalized = normalizeCompareSampleIds(selected)
assert(normalized.length === 5, 'A1 failed: normalized 5-file selection not preserved')
const visible = normalizeVisibleSampleIds(['s3','s2','ghost'], normalized)
assert(visible.join(',') === 's3,s2', 'A1 failed: visible filtering/order incorrect')
const priority = buildScatterPriorityOrder(normalized, visible)
assert(priority.join(',') === 's3,s2,s1,s4,s5', 'A1 failed: scatter priority order incorrect')
const cfg = clampCompareLoadConfig({ resultConcurrency: 99, scatterConcurrency: 99, scatterPointLimit: 99999 })
assert(cfg.resultConcurrency === 5 && cfg.scatterConcurrency === 4 && cfg.scatterPointLimit === 10000, 'A1 failed: config clamp guardrail not enforced')

// A2 acceptance proxy: stale response rejection
assert(isCurrentCompareRequestVersion(7, 7) === true, 'A2 failed: current request not recognized')
assert(isCurrentCompareRequestVersion(8, 7) === false, 'A2 failed: stale request not rejected')

// A3 acceptance proxy: explicit deterministic states
assert(deriveCompareSampleStatus({ sampleId: null, loadingBySampleId: {}, errorsBySampleId: {}, hasResults: false }) === 'empty', 'A3 failed: compare empty state')
assert(deriveCompareSampleStatus({ sampleId: 's1', loadingBySampleId: { s1: true }, errorsBySampleId: {}, hasResults: false }) === 'loading', 'A3 failed: compare loading state')
assert(deriveCompareSampleStatus({ sampleId: 's1', loadingBySampleId: {}, errorsBySampleId: { s1: 'boom' }, hasResults: false }) === 'error', 'A3 failed: compare error state')
assert(deriveCompareSampleStatus({ sampleId: 's1', loadingBySampleId: {}, errorsBySampleId: {}, hasResults: true }) === 'data', 'A3 failed: compare data state')

assert(deriveOverlayHistogramRenderState({ primaryLoading: true, hasPrimaryResults: false, primaryError: undefined, chartDataLength: 0 }) === 'loading', 'A3 failed: overlay loading state')
assert(deriveOverlayHistogramRenderState({ primaryLoading: false, hasPrimaryResults: false, primaryError: 'err', chartDataLength: 0 }) === 'error', 'A3 failed: overlay error state')
assert(deriveOverlayHistogramRenderState({ primaryLoading: false, hasPrimaryResults: false, primaryError: undefined, chartDataLength: 0 }) === 'empty', 'A3 failed: overlay empty state')
assert(deriveOverlayHistogramRenderState({ primaryLoading: false, hasPrimaryResults: true, primaryError: undefined, chartDataLength: 5 }) === 'data', 'A3 failed: overlay data state')

console.log('WS-A acceptance runtime checks passed: A1, A2, A3')

