               # Audit Roadmap Status Reconciliation (March 20, 2026)

Source baseline: [COMPREHENSIVE_AUDIT_REPORT_MARCH_2026.md](COMPREHENSIVE_AUDIT_REPORT_MARCH_2026.md#L583)

This checklist maps each of the 28 roadmap tasks from the audit report to current codebase status.

## Summary

- Total roadmap tasks: 28
- Resolved: 16
- Open: 11
- Partial: 1

## Phase 1 - Critical Security Fixes

| # | Task | Status | Evidence |
|---|---|---|---|
| 1 | Add auth middleware to backup router | Resolved | [backup.py](backend/src/api/routers/backup.py#L102), [backup.py](backend/src/api/routers/backup.py#L155), [backup.py](backend/src/api/routers/backup.py#L254), [backup.py](backend/src/api/routers/backup.py#L341) |
| 2 | Add ownership validation to /auth/me/{id} and /auth/profile/{id} | Resolved | [auth.py](backend/src/api/routers/auth.py#L285), [auth.py](backend/src/api/routers/auth.py#L334) |
| 3 | Add admin-only check to GET /auth/users | Resolved | [auth.py](backend/src/api/routers/auth.py#L401) |
| 4 | Fix CORS wildcard + credentials | Resolved | [main.py](backend/src/api/main.py#L172), [main.py](backend/src/api/main.py#L173) |
| 5 | Auto-generate JWT secret key if not set | Resolved | [config.py](backend/src/api/config.py#L66), [config.py](backend/src/api/config.py#L71) |

## Phase 2 - Fake Data Elimination

| # | Task | Status | Evidence |
|---|---|---|---|
| 6 | Fix cross-compare overlay histogram fallback | Resolved | [overlay-histogram-chart.tsx](components/cross-compare/charts/overlay-histogram-chart.tsx#L96) |
| 7 | Fix cross-compare KDE fallback | Resolved | [kde-comparison-chart.tsx](components/cross-compare/charts/kde-comparison-chart.tsx#L85), [kde-comparison-chart.tsx](components/cross-compare/charts/kde-comparison-chart.tsx#L170) |
| 8 | Fix correlation scatter fallback | Resolved | [correlation-scatter-chart.tsx](components/cross-compare/charts/correlation-scatter-chart.tsx#L151), [correlation-scatter-chart.tsx](components/cross-compare/charts/correlation-scatter-chart.tsx#L163) |
| 9 | Fix FCS size distribution fake histogram fallback | Resolved | [size-distribution-chart.tsx](components/flow-cytometry/charts/size-distribution-chart.tsx#L65) |
| 10 | Fix NTA concentration profile mock data fallback | Resolved | [concentration-profile-chart.tsx](components/nta/charts/concentration-profile-chart.tsx#L18), [concentration-profile-chart.tsx](components/nta/charts/concentration-profile-chart.tsx#L105) |
| 11 | Fix dashboard AI chat dead endpoint | Resolved | [dashboard-ai-chat.tsx](components/dashboard/dashboard-ai-chat.tsx#L45) |

## Phase 3 - Code Quality

| # | Task | Status | Evidence |
|---|---|---|---|
| 12 | Wire cross-compare sidebar file selects | Resolved | [sidebar.tsx](components/sidebar.tsx#L1309), [sidebar.tsx](components/sidebar.tsx#L1310), [sidebar.tsx](components/sidebar.tsx#L1332), [sidebar.tsx](components/sidebar.tsx#L1333) |
| 13 | Convert distribution-analysis to cached parser path | Resolved | [samples.py](backend/src/api/routers/samples.py#L2435), [samples.py](backend/src/api/routers/samples.py#L2539) |
| 14 | Add NTA upload cache invalidation | Open | [api-client.ts](lib/api-client.ts#L1208), [api-client.ts](lib/api-client.ts#L1248) |
| 15 | Delete empty src/fusion and src/preprocessing dirs | Resolved | [backend/src](backend/src) |
| 16 | Remove/archive broken backend scripts | Resolved | [backend/src](backend/src), [COMPREHENSIVE_AUDIT_REPORT_MARCH_2026.md](COMPREHENSIVE_AUDIT_REPORT_MARCH_2026.md#L338) |
| 17 | Delete or deprecate dead API client methods | Open | [api-client.ts](lib/api-client.ts#L1147) |
| 18 | Clean dead store actions and state | Partial | [store.ts](lib/store.ts#L381), [store.ts](lib/store.ts#L445), [use-api.ts](hooks/use-api.ts#L29) |
| 19 | Delete unused empty-states and loading-skeletons components | Resolved | [components](components) |

## Phase 4 - Testing

| # | Task | Status | Evidence |
|---|---|---|---|
| 20 | Add frontend chart rendering tests | Open | [circle_tem/circle-tem/src/App.test.js](circle_tem/circle-tem/src/App.test.js#L1) |
| 21 | Complete backend parser test stubs | Open | [backend/tests/test_parser.py](backend/tests/test_parser.py#L20) |
| 22 | Add auth endpoint tests | Open | [backend/tests](backend/tests) |
| 23 | Add backup endpoint tests | Open | [backend/tests](backend/tests) |
| 24 | Set ignoreBuildErrors false and fix resulting errors | Open | [next.config.mjs](next.config.mjs#L12) |

## Phase 5 - Dependency and Config Maintenance

| # | Task | Status | Evidence |
|---|---|---|---|
| 25 | Add upper version bounds to requirements.txt | Open | [backend/requirements.txt](backend/requirements.txt#L13) |
| 26 | Update README for pnpm, SQLite, and current routes | Open | [README.md](README.md#L44), [README.md](README.md#L34), [README.md](README.md#L110) |
| 27 | Purge archived calibration configs before packaging | Open | [backend/config/calibration](backend/config/calibration) |
| 28 | Move in-memory password reset tokens to database | Open | [auth.py](backend/src/api/routers/auth.py#L439), [auth.py](backend/src/api/routers/auth.py#L484), [auth.py](backend/src/api/routers/auth.py#L526) |

## Notes

- Status values are derived from current code behavior, not historical tracker text.
- Evidence links point to current workspace files and 1-based line references where applicable.
- For cleanup tasks involving file removal, evidence is directory-level because line evidence does not exist for deleted files.
