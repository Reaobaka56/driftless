DROP INDEX IF EXISTS uq_scan_repo_vendor_commit;
ALTER TABLE scan_results
    DROP COLUMN IF EXISTS error,
    DROP COLUMN IF EXISTS analysis,
    DROP COLUMN IF EXISTS status,
    DROP COLUMN IF EXISTS commit_sha;
