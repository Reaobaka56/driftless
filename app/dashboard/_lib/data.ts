import { sql } from '@vercel/postgres';

/** Every read returns this, so a page can show "not connected" instead of a 500. */
export type Db<T> = { ok: true; data: T } | { ok: false; reason: 'not_configured' | 'error' };

async function read<T>(fn: () => Promise<T>): Promise<Db<T>> {
  if (!process.env.POSTGRES_URL) return { ok: false, reason: 'not_configured' };
  try {
    return { ok: true, data: await fn() };
  } catch (e) {
    // Logged server-side only: driver errors can contain host names.
    console.error('dashboard query failed', e);
    return { ok: false, reason: 'error' };
  }
}

export type ScanStatus = 'running' | 'completed' | 'partial' | 'failed';
export type FixStatus = 'pending' | 'scanned' | 'success' | 'draft' | 'failed' | 'merged';
export const SCAN_STATUSES: ScanStatus[] = ['completed', 'partial', 'failed', 'running'];
export const FIX_STATUSES: FixStatus[] = ['success', 'draft', 'failed', 'merged', 'scanned', 'pending'];

export type ScanRow = {
  id: string;
  repo_hash: string;
  vendor: string;
  commit_sha: string;
  status: ScanStatus;
  finding_count: number;
  scanned_at: Date;
  error: string | null;
};

export type FixRow = {
  id: string;
  repo_hash: string;
  record_id: string | null;
  strategy: string;
  status: FixStatus;
  pr_url: string | null;
  created_at: Date;
};

export type RecordRow = {
  id: string;
  vendor: string;
  type: string;
  affects: Record<string, unknown>;
  effective: string;
  source_url: string;
  recipe: string | null;
  migration_note: string;
  review_status: string;
  reviewed_by: string | null;
  stats_attempts: number;
  stats_merged_unedited: number;
};

export type Finding = {
  rule_id: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  file: string;
  start_line: number;
  end_line: number;
  description: string;
  evidence: string;
  remediation: string;
  confidence: number;
  source: string;
};

export type ScanDetail = ScanRow & {
  findings: Finding[];
  analysis: {
    capabilities?: { name: string; status: string; detail: string }[];
    files_scanned?: number;
    parse_errors?: unknown[];
    skipped_files?: unknown[];
  };
};

/** `repo` is a repo_hash or null for all repositories. */
type Repo = string | null;

export const getRepos = () =>
  read(async () => {
    const { rows } = await sql`
      SELECT repo_hash FROM scan_results
      UNION
      SELECT repo_hash FROM fix_attempts
      ORDER BY repo_hash`;
    return rows.map((r) => r.repo_hash as string);
  });

export const getRecentScans = (repo: Repo, status: string | null, limit: number) =>
  read(async () => {
    const { rows } = await sql`
      SELECT id, repo_hash, vendor, commit_sha, status, error, scanned_at,
             jsonb_array_length(findings)::int AS finding_count
      FROM scan_results
      WHERE (${repo}::text IS NULL OR repo_hash = ${repo})
        AND (${status}::text IS NULL OR status = ${status})
      ORDER BY scanned_at DESC
      LIMIT ${limit}`;
    return rows as ScanRow[];
  });

/** Latest scan per repository and vendor: what the overview totals are built from. */
export const getLatestScans = (repo: Repo) =>
  read(async () => {
    const { rows } = await sql`
      SELECT DISTINCT ON (repo_hash, vendor)
             id, repo_hash, vendor, commit_sha, status, error, scanned_at,
             jsonb_array_length(findings)::int AS finding_count
      FROM scan_results
      WHERE (${repo}::text IS NULL OR repo_hash = ${repo})
      ORDER BY repo_hash, vendor, scanned_at DESC`;
    return rows as ScanRow[];
  });

export const getLatestSeverityCounts = (repo: Repo) =>
  read(async () => {
    const { rows } = await sql`
      WITH latest AS (
        SELECT DISTINCT ON (repo_hash, vendor) findings
        FROM scan_results
        WHERE (${repo}::text IS NULL OR repo_hash = ${repo})
        ORDER BY repo_hash, vendor, scanned_at DESC
      )
      SELECT f->>'severity' AS severity, COUNT(*)::int AS n
      FROM latest, jsonb_array_elements(latest.findings) AS f
      GROUP BY 1`;
    return Object.fromEntries(rows.map((r) => [r.severity as string, r.n as number])) as Record<string, number>;
  });

export const getScan = (id: string) =>
  read(async () => {
    const { rows } = await sql`
      SELECT id, repo_hash, vendor, commit_sha, status, error, scanned_at, findings, analysis,
             jsonb_array_length(findings)::int AS finding_count
      FROM scan_results WHERE id = ${id}::uuid`;
    return (rows[0] as ScanDetail | undefined) ?? null;
  });

export const getFixes = (repo: Repo, status: string | null, limit: number) =>
  read(async () => {
    const { rows } = await sql`
      SELECT id, repo_hash, record_id, strategy, status, pr_url, created_at
      FROM fix_attempts
      WHERE (${repo}::text IS NULL OR repo_hash = ${repo})
        AND (${status}::text IS NULL OR status = ${status})
      ORDER BY created_at DESC
      LIMIT ${limit}`;
    return rows as FixRow[];
  });

export const getFixCounts = (repo: Repo) =>
  read(async () => {
    const { rows } = await sql`
      SELECT status, COUNT(*)::int AS n, COUNT(pr_url)::int AS with_pr
      FROM fix_attempts
      WHERE (${repo}::text IS NULL OR repo_hash = ${repo})
      GROUP BY status`;
    const byStatus: Record<string, number> = {};
    let total = 0;
    let opened = 0;
    for (const r of rows) {
      byStatus[r.status as string] = r.n as number;
      total += r.n as number;
      opened += r.with_pr as number;
    }
    return { byStatus, total, opened, merged: byStatus.merged ?? 0 };
  });

export const getRecords = () =>
  read(async () => {
    const { rows } = await sql`
      SELECT id, vendor, type, affects, effective::text AS effective, source_url, recipe,
             migration_note, review_status, reviewed_by, stats_attempts, stats_merged_unedited
      FROM change_records
      ORDER BY effective ASC, id ASC`;
    return rows as RecordRow[];
  });

/** Accept the old `repo_hash` parameter too, so existing links keep working. */
export function repoParam(sp: { repo?: string; repo_hash?: string }): Repo {
  const v = sp.repo ?? sp.repo_hash;
  return v && /^[a-f0-9]{8,64}$/.test(v) ? v : null;
}

export function oneOf<T extends string>(v: string | undefined, allowed: readonly T[]): T | null {
  return allowed.includes(v as T) ? (v as T) : null;
}

export const isUuid = (v: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v);
