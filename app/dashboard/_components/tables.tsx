import Link from 'next/link';
import type { FixRow, ScanRow } from '../_lib/data';
import { Empty, RelTime, ShortHash, Status } from './ui';

export function ScanTable({ rows }: { rows: ScanRow[] }) {
  if (rows.length === 0) {
    return (
      <Empty title="No scans recorded">
        The scan worker writes one row per repository, vendor and commit. Nothing has been scanned against this
        database yet.
      </Empty>
    );
  }
  return (
    <table className="tbl">
      <thead>
        <tr>
          <th scope="col">Repository</th>
          <th scope="col">Vendor</th>
          <th scope="col">Commit</th>
          <th scope="col">Status</th>
          <th scope="col" className="num">
            Findings
          </th>
          <th scope="col">Scanned</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((s) => (
          <tr key={s.id}>
            <td data-label="Repository">
              <Link href={`/dashboard/scans/${s.id}`}>
                <ShortHash value={s.repo_hash} />
              </Link>
            </td>
            <td data-label="Vendor">{s.vendor}</td>
            <td data-label="Commit">{s.commit_sha ? <ShortHash value={s.commit_sha} length={7} /> : '—'}</td>
            <td data-label="Status">
              <Status value={s.status} />
            </td>
            <td data-label="Findings" className="num">
              {s.status === 'failed' || s.status === 'running' ? '—' : s.finding_count}
            </td>
            <td data-label="Scanned">
              <RelTime value={s.scanned_at} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function FixTable({ rows }: { rows: FixRow[] }) {
  if (rows.length === 0) {
    return (
      <Empty title="No fix attempts recorded">
        Nothing writes to this table yet. Fixes run from the CLI today and keep no state. Recording them belongs to the
        pull-request workflow, which isn’t built.
      </Empty>
    );
  }
  return (
    <table className="tbl">
      <thead>
        <tr>
          <th scope="col">Record</th>
          <th scope="col">Repository</th>
          <th scope="col">Strategy</th>
          <th scope="col">Status</th>
          <th scope="col">Pull request</th>
          <th scope="col">Created</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((f) => (
          <tr key={f.id}>
            <td data-label="Record" className="break">
              {f.record_id ?? '—'}
            </td>
            <td data-label="Repository">
              <ShortHash value={f.repo_hash} />
            </td>
            <td data-label="Strategy">{f.strategy}</td>
            <td data-label="Status">
              <Status value={f.status} />
            </td>
            <td data-label="Pull request">
              {f.pr_url && /^https:\/\//.test(f.pr_url) ? (
                <a href={f.pr_url} target="_blank" rel="noopener noreferrer">
                  Open<span className="visually-hidden"> pull request (opens in a new tab)</span>
                </a>
              ) : (
                '—'
              )}
            </td>
            <td data-label="Created">
              <RelTime value={f.created_at} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Filter chips as plain links, so they work without client JS and keep the repo selection. */
export function StatusFilter({
  base,
  repo,
  current,
  options,
}: {
  base: string;
  repo: string | null;
  current: string | null;
  options: readonly string[];
}) {
  const href = (status: string | null) => {
    const p = new URLSearchParams();
    if (repo) p.set('repo', repo);
    if (status) p.set('status', status);
    const q = p.toString();
    return q ? `${base}?${q}` : base;
  };
  return (
    <nav className="chips" aria-label="Filter by status">
      <Link href={href(null)} aria-current={current === null ? 'true' : undefined}>
        All
      </Link>
      {options.map((o) => (
        <Link key={o} href={href(o)} aria-current={current === o ? 'true' : undefined}>
          {o[0].toUpperCase() + o.slice(1)}
        </Link>
      ))}
    </nav>
  );
}
