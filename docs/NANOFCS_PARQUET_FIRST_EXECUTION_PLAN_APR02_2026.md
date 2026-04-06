# NanoFCS Parquet-First Execution Plan
## Date: April 2, 2026
## Scope: FCS ingestion, analysis read-path, UI performance impact, and AI-readiness

## 1. Executive Summary
This plan defines how to move NanoFCS from raw-FCS-on-demand parsing to a parquet-first runtime model without sacrificing scientific correctness.

Decision:
1. Keep raw FCS files as immutable source-of-truth.
2. Generate parquet at ingest time as a mandatory derived artifact.
3. Use parquet as the default read-path for analysis and compare workloads.
4. Keep safe fallback to raw FCS whenever parquet is missing or invalid.

Reason:
1. This improves backend read consistency and throughput.
2. It supports AI pipelines with stable schema and lower parsing overhead.
3. It does not by itself solve all UI lag; frontend rendering and payload controls remain mandatory.

## 2. Current State (Observed in Code)

### 2.1 Upload path (today)
1. FCS upload parses file and saves summary results to database.
2. The current upload path does not persist parquet during this flow.
3. Evidence:
   - backend/src/api/routers/upload.py (create_fcs_result call path)

### 2.2 Analysis read path (today)
1. Analysis endpoints often reopen raw FCS and parse again for event-level access.
2. Evidence:
   - backend/src/api/routers/analysis.py (FCSParser parse usage in data loading path)

### 2.3 Parquet support (today)
1. Parquet directory is configured and created.
2. Parser base and parquet writer utilities already exist.
3. Export endpoint can produce parquet output on demand.
4. Evidence:
   - backend/src/api/config.py
   - backend/src/parsers/base_parser.py
   - backend/src/parsers/parquet_writer.py
   - backend/src/api/routers/analysis.py (export/parquet)

### 2.4 Existing cache strategy (today)
1. In-memory caches reduce repeated parse cost for hot samples.
2. Evidence:
   - backend/src/api/cache.py

## 3. Problem Statement
The platform currently mixes:
1. Raw FCS parse-at-read for multiple runtime operations.
2. DB summary metrics for lightweight views.
3. Frontend point-heavy charting under compare workflows.

This causes:
1. Variable backend latency during cache misses.
2. Repeated parser work under concurrent compare use.
3. Harder AI integration due to non-uniform event data access.
4. Perceived UI lag that is partly backend and partly browser rendering.

## 4. Architecture Options and Honest Tradeoff

### Option A: Keep current raw-first runtime
Pros:
1. Minimal change risk and lower implementation cost.
2. FCS stays canonical and direct.

Cons:
1. Higher parse overhead under load.
2. Less deterministic response times.
3. Harder AI feature pipelines at scale.

### Option B: Full parquet-only, no raw fallback
Pros:
1. Fastest runtime reads if conversion always succeeds.
2. Strongly standardized analytics path.

Cons:
1. Operational risk if conversion fails or schema drifts.
2. Hard failure mode without fallback.
3. Not acceptable for reliability.

### Option C (Selected): Hybrid parquet-first with raw fallback
Pros:
1. Performance and AI benefits of parquet.
2. Reliability preserved by fallback.
3. Controlled migration and easy rollback.

Cons:
1. Additional complexity in ingestion and storage governance.
2. Requires strict parity tests and schema versioning discipline.

## 5. Target Architecture

### 5.1 Ingestion flow
1. Upload raw FCS file to storage.
2. Parse once with current parser.
3. Write canonical parquet event file with metadata header.
4. Persist both file_path_fcs and parquet_file_path plus parquet metadata version/hash.
5. Save summary metrics from parsed event frame as today.

### 5.2 Analysis flow
1. Default event reads from parquet.
2. If parquet missing/invalid/outdated, fallback to raw FCS parse.
3. Optionally trigger async parquet repair job after fallback success.

### 5.3 UI/API flow
1. API continues to return chart-ready subsets (point-capped/default bins).
2. No full event dump by default to frontend.
3. Keep workerized frontend transforms and runtime LRU caches.

### 5.4 AI flow
1. AI services consume parquet-backed event schema or derived feature tables.
2. Schema contract is versioned and validated at ingestion.
3. Feature extraction is deterministic across runs.

## 6. Data Contract and Schema Governance

### 6.1 Required parquet metadata keys
1. source_file
2. parser_version
3. parquet_schema_version
4. generated_at_utc
5. fcs_channel_map
6. calibration_context
7. upload_sample_id
8. file_checksum_sha256

### 6.2 Required event columns (minimum)
1. event_index
2. fsc_value
3. ssc_value
4. selected_scatter_channel
5. computed_size_nm (if available)
6. quality_flags

### 6.3 Backward compatibility
1. Never remove or rename columns without schema version bump.
2. Additive columns are allowed across minor versions.
3. Readers must tolerate unknown metadata keys.

## 7. File-Level Change Plan

### 7.1 Backend ingestion and persistence
1. backend/src/api/routers/upload.py
   - Add parquet write call after successful parse.
   - Save parquet_file_path and metadata version.
   - Add explicit error handling and fallback behavior.
2. backend/src/database/crud.py
   - Extend create_fcs_result calls to pass parquet metadata fields.
3. backend/src/database/models.py
   - Keep parquet_file_path nullable for transition.
   - Add parquet_schema_version and parquet_checksum fields.
4. backend/alembic/versions/*
   - New migration for added parquet tracking columns.

### 7.2 Backend read-path migration
1. backend/src/api/routers/analysis.py
   - Introduce helper load_fcs_events(sample) with order:
     a. parquet read
     b. raw fallback
   - Replace direct parser usage in event-read endpoints with helper.
2. backend/src/api/cache.py
   - Add cache key components including schema version and calibration context.
   - Add counters for parquet_hit, parquet_miss, raw_fallback.

### 7.3 Parser and utilities
1. backend/src/parsers/base_parser.py
   - Ensure to_parquet metadata includes schema/version/checksum fields.
2. backend/src/parsers/parquet_writer.py
   - Add strict schema validation on read and clear exception types.

### 7.4 Frontend contract checks
1. hooks/use-api.ts
   - No breaking contract expected; verify payload assumptions remain unchanged.
2. components/flow-cytometry/*
   - Keep current worker/cache improvements; storage format is backend concern.

## 8. Performance Reality Check
Parquet-first helps:
1. Cold-read latency on backend.
2. Repeat analytics throughput.
3. AI and batch extraction workflows.

Parquet-first does not automatically solve:
1. Browser jank from rendering too many points.
2. Main-thread transform blocking.
3. Over-sized API payloads.

Therefore performance work must remain dual-track:
1. Backend data access optimization (this plan).
2. Frontend rendering optimization (already in WS-B and WS-C tracker items).

## 9. Accuracy and Scientific Integrity Safeguards

### 9.1 Non-negotiable parity checks
For each migrated endpoint, compare parquet-read vs raw-read outputs on same sample set:
1. Event count
2. FSC/SSC median and mean
3. Size distribution metrics (d10/d50/d90)
4. Debris percentage
5. Marker-positive percentages where applicable

### 9.2 Numeric tolerance gates
1. Exact match for integer counts.
2. Relative delta <= 0.1% for core scalar metrics.
3. KS test p-value >= 0.95 equivalence threshold for sampled distributions where practical.

### 9.3 Rollout blocker
If parity gate fails:
1. Keep endpoint on raw fallback.
2. Log and open defect with sample ID and schema version.
3. Do not proceed to next phase.

## 10. Rollout Phases

### Phase P0: Foundation and observability
1. Add schema version/checksum fields and migration.
2. Add parquet telemetry counters.
3. Add feature flag: PARQUET_PRIMARY_READ_ENABLED.

### Phase P1: Ingest-time parquet generation
1. Write parquet during FCS upload success path.
2. Persist parquet_file_path and metadata.
3. Keep all reads on current path.

### Phase P2: Read-path migration (shadow mode)
1. Read parquet first in shadow and compare to raw silently.
2. Emit parity logs and dashboards.
3. No user-visible behavior changes yet.

### Phase P3: Default parquet reads
1. Enable parquet-first reads for selected endpoints.
2. Keep raw fallback for all errors.
3. Monitor latency/error/parity counters for 7 days.

### Phase P4: Expansion and hardening
1. Migrate remaining heavy endpoints.
2. Add background parquet repair/rebuild jobs.
3. Document AI feature extraction contract and ownership.

## 11. Feature Flags
1. PARQUET_INGEST_WRITE_ENABLED
2. PARQUET_PRIMARY_READ_ENABLED
3. PARQUET_SHADOW_COMPARE_ENABLED
4. PARQUET_FALLBACK_TO_RAW_ENABLED

Default at rollout start:
1. Write enabled after P1 deploy.
2. Primary read disabled until P3.
3. Shadow compare enabled in P2.
4. Fallback always enabled.

## 12. Test Plan

### 12.1 Unit tests
1. Parquet metadata generation and schema stamping.
2. Parquet read helper fallback behavior.
3. Cache key versioning and invalidation.

### 12.2 Integration tests
1. Upload FCS -> parquet written -> DB path persisted.
2. Endpoint read from parquet and raw fallback on forced corruption.
3. Multi-file compare performance smoke tests.

### 12.3 Regression tests
1. Fixed reference sample set with expected metrics.
2. Cross-version schema reader compatibility.

### 12.4 Load tests
1. 5-file and 10-file compare request bursts.
2. p50/p95 latency for scatter and distribution endpoints.
3. CPU and memory profile under cache miss and hit scenarios.

## 13. Observability and Dashboards
Track at minimum:
1. parquet_read_hits
2. parquet_read_misses
3. raw_fallback_count
4. parquet_write_failures
5. parity_check_failures
6. endpoint_latency_p50_p95
7. chart_payload_size_bytes

Alert conditions:
1. raw_fallback_rate > 10% for 15 minutes
2. parity_check_failures > 0 on production path
3. parquet_write_failures spike above baseline

## 14. Risks and Mitigations
1. Risk: Schema drift breaks readers.
   - Mitigation: schema versioning and compatibility tests.
2. Risk: Hidden precision changes alter scientific metrics.
   - Mitigation: strict parity gates and tolerance checks.
3. Risk: Storage growth.
   - Mitigation: lifecycle policy and compression defaults.
4. Risk: UI still lags after backend migration.
   - Mitigation: continue frontend point-cap/worker/progressive render plan.

## 15. Rollback Strategy
1. Disable PARQUET_PRIMARY_READ_ENABLED to return to raw reads.
2. Keep PARQUET_INGEST_WRITE_ENABLED active to preserve generated artifacts.
3. Do not drop schema columns during rollback.
4. Re-enable after defect closure and parity revalidation.

## 16. Definition of Done
This migration is complete only when all are true:
1. Ingest writes parquet for new FCS uploads reliably.
2. Primary read-path for targeted endpoints is parquet-first with fallback.
3. Scientific parity gates pass across reference datasets.
4. p95 endpoint latency improves on compare-relevant endpoints.
5. Developer docs and AI execution guidance are current.

## 17. Developer and AI Execution Checklist
1. Read this plan and tracker before coding.
2. Implement by phase only, no cross-phase shortcuts.
3. Add tests and telemetry with each code change.
4. Prove parity before enabling primary parquet reads.
5. Keep raw fallback path healthy until post-stabilization signoff.

## 18. References
1. docs/NANOFCS_UNIFIED_MULTI_FILE_TASK_TRACKER_MAR31_2026.md
2. docs/NANOFCS_PRINCIPLES_ADOPTION_MASTER_PLAN_MAR31_2026.md
3. backend/src/api/routers/upload.py
4. backend/src/api/routers/analysis.py
5. backend/src/parsers/base_parser.py
6. backend/src/parsers/parquet_writer.py
7. backend/src/api/cache.py
