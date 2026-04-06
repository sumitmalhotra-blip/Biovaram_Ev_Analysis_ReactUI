"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.normalizeCompareSampleIds = normalizeCompareSampleIds;
exports.normalizeVisibleSampleIds = normalizeVisibleSampleIds;
exports.buildScatterPriorityOrder = buildScatterPriorityOrder;
exports.clampCompareLoadConfig = clampCompareLoadConfig;
exports.isCurrentCompareRequestVersion = isCurrentCompareRequestVersion;
exports.deriveCompareSampleStatus = deriveCompareSampleStatus;
exports.deriveOverlayHistogramRenderState = deriveOverlayHistogramRenderState;
function normalizeCompareSampleIds(sampleIds, maxSamples = 10) {
    return Array.from(new Set(sampleIds.map((id) => id.trim()).filter(Boolean))).slice(0, maxSamples);
}
function normalizeVisibleSampleIds(sampleIds, allowedSampleIds) {
    const allowed = new Set(allowedSampleIds);
    return Array.from(new Set(sampleIds.map((id) => id.trim()).filter((id) => allowed.has(id))));
}
function buildScatterPriorityOrder(normalizedSampleIds, visibleSampleIds) {
    return [
        ...visibleSampleIds,
        ...normalizedSampleIds.filter((id) => !visibleSampleIds.includes(id)),
    ];
}
function clampCompareLoadConfig(options) {
    return {
        resultConcurrency: Math.max(1, Math.min(5, options?.resultConcurrency ?? 3)),
        scatterConcurrency: Math.max(1, Math.min(4, options?.scatterConcurrency ?? 2)),
        scatterPointLimit: Math.max(500, Math.min(10000, options?.scatterPointLimit ?? 2000)),
    };
}
function isCurrentCompareRequestVersion(currentVersion, requestVersion) {
    return currentVersion === requestVersion;
}
function deriveCompareSampleStatus(params) {
    const sampleId = params.sampleId || null;
    if (!sampleId)
        return "empty";
    if (params.loadingBySampleId[sampleId])
        return "loading";
    if (params.errorsBySampleId[sampleId])
        return "error";
    return params.hasResults ? "data" : "empty";
}
function deriveOverlayHistogramRenderState(params) {
    if (params.primaryLoading)
        return "loading";
    if (!params.hasPrimaryResults && params.primaryError)
        return "error";
    if (!params.hasPrimaryResults)
        return "empty";
    if (params.chartDataLength === 0)
        return "empty";
    return "data";
}
