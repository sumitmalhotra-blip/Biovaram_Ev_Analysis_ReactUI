# BioVaram EV Analysis ReactUI - Claude Memory

Use this file as the first stop for any task in this repo. Keep reads targeted, prefer the exact module that owns the behavior, and avoid broad scans unless the task genuinely crosses boundaries.

## Daily Usage Cheat Sheet

**Before you start coding:**
- Planning a new feature? → `/office-hours` (reframe the request) → `/autoplan` (full structured plan)
- Reviewing an idea? → `/plan-ceo-review` (strategic), `/plan-eng-review` (architecture), `/plan-design-review` (visual)

**While coding:**
- Use `code-review-graph` tools FIRST for exploring code, not grep/search (cheaper, faster, more context)
  - `query_graph` to trace callers/callees/imports
  - `get_impact_radius` to understand blast radius of changes
  - `get_affected_flows` to see which execution paths change

**Before landing changes:**
- `/review` — full pre-landing PR review (finds bugs that pass CI)
- `/qa https://url` — open real browser, find bugs, fix them, re-verify
- Browser work? → `/browse` (real Chromium, ~100ms/command, no MCP tools)

**When you ship:**
- `/ship` — runs tests, pushes, opens PR with workspace-aware version tracking
- `/land-and-deploy` — merges, waits for CI, deploys, verifies production health

**Safety & ops:**
- `/cso` — OWASP + STRIDE security audit
- `/health` — code quality dashboard (types, lint, tests, dead code)
- `/context-save` — save working state (git, decisions, remaining work)
- `/gstack-upgrade` — update gstack to latest

**Key principle:** gstack skills are global (in `~/.claude/skills/gstack/`). This repo runs code-review-graph for codebase-aware context. Together they replace manual searching and make Claude Code sessions ship like a team.

## Project Shape

- `app/` - Next.js App Router entry points, global layout, and app shell.
- `components/` - UI and feature components.
- `components/ui/` - shared shadcn-style primitives.
- `components/flow-cytometry/` - NanoFACS / FCS analysis UI.
- `components/nta/` - NTA analysis UI.
- `components/research-chat/` - AI chat UI.
- `hooks/` - shared React hooks.
- `lib/` - shared frontend utilities, store, API client, export helpers, AI client.
- `types/` - frontend TypeScript declarations.
- `backend/` - FastAPI + Python analysis backend.
- `backend/src/api/routers/` - HTTP endpoints and AI/chat routing.
- `backend/src/parsers/` - FCS, NTA, bead, and file parsing.
- `backend/src/physics/` - Mie scattering, bead calibration, sizing math.
- `backend/src/analysis/` - higher-level analysis logic.
- `backend/src/visualization/` - plot generation helpers.
- `backend/src/database/` - ORM models, CRUD, and DB connection.
- `backend/src/utils/` - backend helpers and caches.
- `backend/docs/` - backend architecture, API reference, onboarding, and technical guides.
- `docs/` - frontend and sizing documentation.
- `build/`, `dist-electron*/`, `dist/`, `repo-inspection/` - generated or inspection artifacts; do not treat these as source of truth unless the task is specifically about packaging or inspection history.

## High-Value Entry Points

- Frontend app shell: `app/layout.tsx`, `app/page.tsx`, `app/globals.css`.
- Main UI composition: `components/header.tsx`, `components/sidebar.tsx`, `components/tab-navigation.tsx`, `components/store-provider.tsx`, `components/theme-provider.tsx`.
- Flow cytometry workflow: `components/flow-cytometry/flow-cytometry-tab.tsx`, `components/flow-cytometry/full-analysis-dashboard.tsx`, `components/flow-cytometry/analysis-results.tsx`.
- NTA workflow: `components/nta/nta-tab.tsx`, `components/nta/nta-analysis-results.tsx`.
- Research chat UI: `components/research-chat/research-chat-tab.tsx`.
- Frontend data access: `lib/api-client.ts`, `lib/ai-chat-client.ts`, `hooks/use-api.ts`.
- Backend API entry: `backend/src/api/main.py`.
- Chat and AI routes: `backend/src/api/routers/chat.py`, `backend/src/api/routers/nanofacs_ai.py`, `backend/src/api/routers/nta_ai.py`, `backend/src/api/routers/ai_gateway.py`.
- Upload and sample routes: `backend/src/api/routers/upload.py`, `backend/src/api/routers/samples.py`, `backend/src/api/routers/analysis.py`, `backend/src/api/routers/calibration.py`.
- Core parsers: `backend/src/parsers/fcs_parser.py`, `backend/src/parsers/nta_parser.py`, `backend/src/parsers/bead_datasheet_parser.py`, `backend/src/parsers/parquet_writer.py`.
- Core physics: `backend/src/physics/mie_scatter.py`, `backend/src/physics/bead_calibration.py`, `backend/src/physics/size_distribution.py`, `backend/src/physics/statistics_utils.py`.
- Database layer: `backend/src/database/models.py`, `backend/src/database/crud.py`, `backend/src/database/connection.py`.

## Task Routing Rules

- If the task is UI behavior, start in `components/` or `app/` before searching backend code.
- If the task is file parsing, sizing, calibration, or AI-response shaping, start in `backend/src/parsers/`, `backend/src/physics/`, or `backend/src/api/routers/`.
- If the task is shared state or API calls, inspect `lib/` and `hooks/` before changing individual feature components.
- If the task is documentation or onboarding, prefer `docs/` or `backend/docs/` rather than duplicating content elsewhere.
- If the task is packaging or release, inspect `build/`, `dist-electron*/`, `packaging/`, and the release notes docs, but treat them as generated/output-focused.

## Token-Saving Workflow

- Read the smallest owning file first, then one nearby caller or test if needed.
- Prefer symbol-aware navigation over broad text search when the language server supports it.
- Use the docs in this repo before scanning code broadly: `docs/FRONTEND_ARCHITECTURE.md`, `backend/docs/BACKEND_ARCHITECTURE.md`, `backend/docs/API_REFERENCE.md`, `backend/docs/DEVELOPER_GUIDE.md`.
- Compact or clear between unrelated phases of work.
- Keep prompts specific to one component, route, parser, or bug.

## Local Conventions To Remember

- Frontend uses Next.js App Router and TypeScript.
- Backend uses FastAPI with Python modules under `backend/src/`.
- EV domain work centers on FCS, NTA, Mie scattering, bead calibration, and cross-comparison.
- AI chat behavior is controlled primarily in `backend/src/api/routers/chat.py` and the related AI routers.

## When This File Is Not Enough

- For detailed frontend architecture, read `docs/FRONTEND_ARCHITECTURE.md`.
- For backend architecture and module responsibilities, read `backend/docs/BACKEND_ARCHITECTURE.md`.
- For endpoint-specific behavior, read `backend/docs/API_REFERENCE.md`.
- For domain workflow and developer onboarding, read `backend/docs/DEVELOPER_GUIDE.md` and `backend/docs/ONBOARDING_GUIDE.md`.

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
