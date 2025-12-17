/**
 * Best Practices Knowledge Base for EV Analysis
 * TASK-016: Compare user's data against established best practices
 * 
 * Client Quote (Jagan, Nov 27, 2025):
 * "We find ourselves a distinguish factor... we can report to the user 
 * 'you are getting some anomaly here, look into this'"
 * 
 * This module provides:
 * 1. Knowledge base of EV analysis best practices
 * 2. Comparison functions to evaluate experimental data
 * 3. Recommendation generation for users
 */

// Best practice rule types
export type RuleSeverity = "info" | "warning" | "error"
export type RuleCategory = "sample-prep" | "antibody" | "instrument" | "analysis" | "quality"

export interface BestPracticeRule {
  id: string
  name: string
  category: RuleCategory
  description: string
  checkType: "range" | "threshold" | "boolean" | "pattern"
  // For range checks
  minValue?: number
  maxValue?: number
  optimalMin?: number
  optimalMax?: number
  unit?: string
  // For threshold checks
  threshold?: number
  comparison?: "less" | "greater" | "equal"
  // Severity and messages
  severity: RuleSeverity
  warningMessage: string
  recommendation: string
  reference?: string  // Scientific reference
}

export interface BestPracticeViolation {
  rule: BestPracticeRule
  actualValue: number | string | boolean
  severity: RuleSeverity
  message: string
  recommendation: string
}

export interface BestPracticesCheckResult {
  score: number  // 0-100 overall compliance score
  totalRules: number
  passed: number
  warnings: number
  errors: number
  violations: BestPracticeViolation[]
  recommendations: string[]
}

// ============================================================================
// BEST PRACTICES KNOWLEDGE BASE
// Based on ISEV 2023 guidelines and BioVaram protocols
// ============================================================================

export const BEST_PRACTICES_RULES: BestPracticeRule[] = [
  // -------------------------------------------------------------------------
  // Sample Preparation
  // -------------------------------------------------------------------------
  {
    id: "prep-001",
    name: "Antibody Concentration",
    category: "antibody",
    description: "Optimal antibody concentration for EV staining",
    checkType: "range",
    minValue: 0.1,
    maxValue: 5.0,
    optimalMin: 0.5,
    optimalMax: 2.0,
    unit: "µg",
    severity: "warning",
    warningMessage: "Antibody concentration is outside recommended range",
    recommendation: "Use 0.5-2.0 µg per 10^9 particles for optimal staining. Higher concentrations may cause non-specific binding.",
    reference: "ISEV 2023 Guidelines, Section 4.2",
  },
  {
    id: "prep-002",
    name: "Sample Dilution Factor",
    category: "sample-prep",
    description: "Dilution factor for NTA measurement",
    checkType: "range",
    minValue: 10,
    maxValue: 10000,
    optimalMin: 100,
    optimalMax: 1000,
    unit: "x",
    severity: "warning",
    warningMessage: "Dilution factor may affect measurement accuracy",
    recommendation: "Dilute sample to achieve 20-100 particles per frame for optimal NTA tracking. Typical dilution is 100-1000x.",
    reference: "NanoSight User Guide",
  },
  {
    id: "prep-003",
    name: "Incubation Time",
    category: "sample-prep",
    description: "Antibody incubation time for staining",
    checkType: "range",
    minValue: 5,
    maxValue: 120,
    optimalMin: 15,
    optimalMax: 60,
    unit: "minutes",
    severity: "info",
    warningMessage: "Incubation time is outside typical range",
    recommendation: "15-60 minutes incubation is recommended. Shorter times may result in incomplete staining, longer times may increase background.",
  },
  {
    id: "prep-004",
    name: "Sample Temperature",
    category: "sample-prep",
    description: "Sample storage/measurement temperature",
    checkType: "range",
    minValue: 4,
    maxValue: 37,
    optimalMin: 20,
    optimalMax: 25,
    unit: "°C",
    severity: "warning",
    warningMessage: "Temperature may affect EV stability",
    recommendation: "Measure at room temperature (20-25°C). Cold samples may cause condensation; warm samples may accelerate degradation.",
  },
  {
    id: "prep-005",
    name: "Sample pH",
    category: "sample-prep",
    description: "Buffer pH for EV samples",
    checkType: "range",
    minValue: 6.5,
    maxValue: 8.0,
    optimalMin: 7.2,
    optimalMax: 7.6,
    unit: "",
    severity: "warning",
    warningMessage: "pH outside physiological range may affect EV integrity",
    recommendation: "Use PBS at pH 7.4 or HEPES buffer. Extreme pH values can cause EV aggregation or lysis.",
  },
  
  // -------------------------------------------------------------------------
  // Size Distribution Analysis
  // -------------------------------------------------------------------------
  {
    id: "size-001",
    name: "Median Size (D50) in EV Range",
    category: "analysis",
    description: "Median particle size should be within typical EV range",
    checkType: "range",
    minValue: 30,
    maxValue: 500,
    optimalMin: 50,
    optimalMax: 200,
    unit: "nm",
    severity: "warning",
    warningMessage: "Median size is outside typical EV range",
    recommendation: "Exosomes typically range 30-150nm, microvesicles 100-1000nm. If median is >300nm, sample may contain aggregates or apoptotic bodies.",
  },
  {
    id: "size-002",
    name: "Size Distribution Span",
    category: "analysis",
    description: "D90-D10 span indicates polydispersity",
    checkType: "range",
    minValue: 20,
    maxValue: 300,
    optimalMin: 40,
    optimalMax: 150,
    unit: "nm",
    severity: "info",
    warningMessage: "Sample shows high polydispersity",
    recommendation: "A narrow size distribution (span < 100nm) indicates a homogeneous population. Wide spans may indicate mixed populations or aggregation.",
  },
  {
    id: "size-003",
    name: "Polydispersity Index",
    category: "analysis",
    description: "CV of size distribution",
    checkType: "threshold",
    threshold: 50,
    comparison: "less",
    unit: "%",
    severity: "warning",
    warningMessage: "High polydispersity may indicate sample heterogeneity",
    recommendation: "PDI > 50% suggests a heterogeneous sample. Consider SEC fractionation for more uniform populations.",
  },
  
  // -------------------------------------------------------------------------
  // Event Quality
  // -------------------------------------------------------------------------
  {
    id: "quality-001",
    name: "Anomaly Percentage",
    category: "quality",
    description: "Percentage of anomalous events detected",
    checkType: "threshold",
    threshold: 10,
    comparison: "less",
    unit: "%",
    severity: "warning",
    warningMessage: "High anomaly rate detected",
    recommendation: "Anomaly rate > 10% may indicate contamination, aggregation, or instrument issues. Review scatter plots for clusters.",
  },
  {
    id: "quality-002",
    name: "Valid Particles Percentage",
    category: "quality",
    description: "Percentage of events in valid size range (30-220nm)",
    checkType: "threshold",
    threshold: 70,
    comparison: "greater",
    unit: "%",
    severity: "warning",
    warningMessage: "Many particles outside valid size range",
    recommendation: "If < 70% of events are in valid range, sample may contain significant debris or non-EV particles.",
  },
  {
    id: "quality-003",
    name: "Event Count",
    category: "quality",
    description: "Total events for statistical significance",
    checkType: "threshold",
    threshold: 1000,
    comparison: "greater",
    unit: "events",
    severity: "warning",
    warningMessage: "Low event count may affect statistical reliability",
    recommendation: "Acquire at least 5,000-10,000 events for reliable statistics. Current count may not be representative.",
  },
  
  // -------------------------------------------------------------------------
  // FCS/NTA Cross-Comparison
  // -------------------------------------------------------------------------
  {
    id: "compare-001",
    name: "FCS-NTA Size Correlation",
    category: "analysis",
    description: "Median size difference between FCS and NTA",
    checkType: "threshold",
    threshold: 30,
    comparison: "less",
    unit: "% difference",
    severity: "warning",
    warningMessage: "Significant discrepancy between FCS and NTA measurements",
    recommendation: "FCS and NTA should agree within 20-30%. Large differences may indicate calibration issues or different particle populations being measured.",
  },
]

// ============================================================================
// BEST PRACTICES CHECKER FUNCTIONS
// ============================================================================

export interface ExperimentData {
  // Experimental conditions
  antibody_concentration_ug?: number
  dilution_factor?: number
  incubation_time_min?: number
  temperature_celsius?: number
  ph?: number
  
  // Size statistics
  median_size_nm?: number
  d10_nm?: number
  d50_nm?: number
  d90_nm?: number
  size_cv_pct?: number  // Coefficient of variation
  
  // Quality metrics
  total_events?: number
  valid_events_pct?: number
  anomaly_pct?: number
  
  // Cross-comparison
  fcs_median?: number
  nta_median?: number
}

/**
 * Check a single rule against experimental data
 */
function checkRule(rule: BestPracticeRule, data: ExperimentData): BestPracticeViolation | null {
  // Map rule IDs to data fields
  const valueMap: Record<string, number | undefined> = {
    "prep-001": data.antibody_concentration_ug,
    "prep-002": data.dilution_factor,
    "prep-003": data.incubation_time_min,
    "prep-004": data.temperature_celsius,
    "prep-005": data.ph,
    "size-001": data.median_size_nm ?? data.d50_nm,
    "size-002": data.d90_nm && data.d10_nm ? data.d90_nm - data.d10_nm : undefined,
    "size-003": data.size_cv_pct,
    "quality-001": data.anomaly_pct,
    "quality-002": data.valid_events_pct,
    "quality-003": data.total_events,
    "compare-001": data.fcs_median && data.nta_median 
      ? Math.abs(data.fcs_median - data.nta_median) / ((data.fcs_median + data.nta_median) / 2) * 100
      : undefined,
  }

  const value = valueMap[rule.id]
  
  // Skip if no data available for this rule
  if (value === undefined) return null

  let isViolation = false
  let message = ""

  if (rule.checkType === "range") {
    // Check if value is outside acceptable range
    if (rule.minValue !== undefined && value < rule.minValue) {
      isViolation = true
      message = `${rule.name}: ${value}${rule.unit || ""} is below minimum (${rule.minValue}${rule.unit || ""})`
    } else if (rule.maxValue !== undefined && value > rule.maxValue) {
      isViolation = true
      message = `${rule.name}: ${value}${rule.unit || ""} is above maximum (${rule.maxValue}${rule.unit || ""})`
    } else if (rule.optimalMin !== undefined && rule.optimalMax !== undefined) {
      // Check optimal range (less severe)
      if (value < rule.optimalMin || value > rule.optimalMax) {
        isViolation = true
        message = `${rule.name}: ${value}${rule.unit || ""} is outside optimal range (${rule.optimalMin}-${rule.optimalMax}${rule.unit || ""})`
      }
    }
  } else if (rule.checkType === "threshold") {
    const threshold = rule.threshold || 0
    
    if (rule.comparison === "less" && value >= threshold) {
      isViolation = true
      message = `${rule.name}: ${value}${rule.unit || ""} exceeds threshold (${threshold}${rule.unit || ""})`
    } else if (rule.comparison === "greater" && value <= threshold) {
      isViolation = true
      message = `${rule.name}: ${value}${rule.unit || ""} is below minimum (${threshold}${rule.unit || ""})`
    }
  }

  if (isViolation) {
    return {
      rule,
      actualValue: value,
      severity: rule.severity,
      message,
      recommendation: rule.recommendation,
    }
  }

  return null
}

/**
 * Check all best practices against experimental data
 */
export function checkBestPractices(data: ExperimentData): BestPracticesCheckResult {
  const violations: BestPracticeViolation[] = []
  let passed = 0
  let warnings = 0
  let errors = 0
  let checkedRules = 0

  for (const rule of BEST_PRACTICES_RULES) {
    const violation = checkRule(rule, data)
    
    if (violation === null) {
      // Rule passed or no data to check
      passed++
    } else {
      violations.push(violation)
      
      if (violation.severity === "error") {
        errors++
      } else if (violation.severity === "warning") {
        warnings++
      }
    }
    checkedRules++
  }

  // Calculate compliance score (0-100)
  const score = Math.round(((passed) / checkedRules) * 100)

  // Generate recommendations
  const recommendations = violations
    .filter(v => v.severity !== "info")
    .map(v => v.recommendation)

  return {
    score,
    totalRules: checkedRules,
    passed,
    warnings,
    errors,
    violations,
    recommendations,
  }
}

/**
 * Get best practices by category
 */
export function getRulesByCategory(category: RuleCategory): BestPracticeRule[] {
  return BEST_PRACTICES_RULES.filter(rule => rule.category === category)
}

/**
 * Get severity badge color
 */
export function getSeverityColor(severity: RuleSeverity): string {
  switch (severity) {
    case "error":
      return "#ef4444"  // Red
    case "warning":
      return "#f59e0b"  // Amber
    case "info":
      return "#3b82f6"  // Blue
    default:
      return "#6b7280"  // Gray
  }
}
