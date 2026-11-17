CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE change_records (
    id TEXT PRIMARY KEY,
    vendor TEXT NOT NULL,
    type TEXT NOT NULL,
    affects JSONB NOT NULL,
    effective DATE NOT NULL,
    source_url TEXT NOT NULL,
    recipe TEXT,
    migration_note TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'draft',
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    stats_attempts INT NOT NULL DEFAULT 0,
    stats_merged_unedited INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_records_vendor ON change_records(vendor) WHERE review_status = 'reviewed';

CREATE TABLE scan_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_hash TEXT NOT NULL,
    vendor TEXT NOT NULL,
    findings JSONB NOT NULL,
    scanned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_scan_repo ON scan_results(repo_hash, scanned_at DESC);

CREATE TABLE fix_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_hash TEXT NOT NULL,
    record_id TEXT REFERENCES change_records(id),
    strategy TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','scanned','success','draft','failed','merged')),
    pr_url TEXT,
    idempotency_key TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_attempts_repo ON fix_attempts(repo_hash, created_at DESC);
