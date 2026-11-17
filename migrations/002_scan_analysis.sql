ALTER TABLE scan_results
    ADD COLUMN commit_sha TEXT NOT NULL DEFAULT '',
    ADD COLUMN status TEXT NOT NULL DEFAULT 'completed'
        CHECK (status IN ('running', 'completed', 'partial', 'failed')),
    ADD COLUMN analysis JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN error TEXT;
CREATE UNIQUE INDEX uq_scan_repo_vendor_commit ON scan_results (repo_hash, vendor, commit_sha);
