# Driftless

Self-maintaining API integrations. Detects call sites broken by a vendor API change,
applies a registry recipe, verifies, and (hosted mode, not built yet) opens a draft PR. Humans merge.

## Setup
    pip install -e ".[dev,worker]"
    (cd src/driftless/scanners/ts && npm install)     # TypeScript Compiler API for the TS/JS scanner
    pytest && ruff check . && mypy src worker server

## CLI
    driftless registry-validate
    driftless scan path/to/repo --vendor stripe        # registry-driven Python call sites
    driftless analyze path/to/repo [--no-llm] [--config cfg.json] [--format json]
    driftless fix stripe-2026-11-17-charge-source path/to/repo [--dry-run]

`analyze` is read-only: registry scan + TypeScript/JavaScript scanner + optional LLM analysis.
Exit codes: 0 clean, 1 findings, 3 scan failed (never "0 findings" when a scanner could not run).

## Architecture
- `issues.py`: one normalized `Issue` schema (rule, severity, file, start/end line, description,
  evidence, remediation, confidence, source). Invalid states raise.
- `discover.py`: file discovery. Honours nested `.gitignore`, skips deps/build output/symlinks/oversized/generated.
- `scanners/typescript.py` + `scanners/ts/scan.mjs`: TS Compiler API rules (eval/Function, command injection,
  HTML injection, hardcoded secrets, TLS verification off, weak hashes, empty catch, async forEach,
  unexplained @ts-ignore). Files with syntax errors are reported, not analysed. Secrets are redacted in evidence.
- `llm/`: provider-independent fallback. Order: primary -> secondary -> deterministic rules -> explicit
  "unavailable" record. Bounded retries (2/provider), per-call timeout, overall deadline, capped Retry-After.
  Output is untrusted data: JSON-parsed, schema-validated, and every finding must cite real lines whose
  text contains its evidence. Findings record their provider in `source`.
  Env: `ANTHROPIC_API_KEY` (+`DRIFTLESS_ANTHROPIC_MODEL`), `OPENAI_API_KEY` + `DRIFTLESS_OPENAI_MODEL`
  (+`OPENAI_BASE_URL`), `DRIFTLESS_LLM_PRIMARY=openai` to swap priority.
- `pipeline.py`: `scan_repository()` -> `ScanReport` (completed | partial | failed + per-capability status).
- `fix/recipes.py`: validated, deterministic `rename_keyword`; refuses ambiguous calls, symlinks, files outside
  the repo; atomic writes. Only the Stripe record exists in the registry.
- `worker/tasks.py`: scan-only. Shallow https clone, run `scan_repository`, persist to `scan_results`
  (unique per repo/vendor/commit). It never fixes, branches, commits or opens PRs.
  TODO: separate fix-and-PR workflow consuming `scan_results`.

## Hosted layer (build only after the I3/I4 gates pass)
- Vercel: `api/registry.ts`, `api/webhooks/github.ts`, `app/dashboard`.
- Render: `render.yaml` (FastAPI `server/main.py`, RQ workers by vendor, Postgres, Redis).
  Migrations: `migrations/001_init.sql`, `002_scan_analysis.sql` (rollbacks: `*_down.sql`).
- Load test: `locust -f tests/load/locustfile.py --users 1000 --spawn-rate 50`
