import Link from 'next/link';
import { FixTable, ScanTable } from './_components/tables';
import { PageHead, SEVERITY_ORDER, Unavailable, daysUntil, describeDays } from './_components/ui';
import {
  getFixCounts,
  getFixes,
  getLatestScans,
  getLatestSeverityCounts,
  getRecentScans,
  getRecords,
  repoParam,
} from './_lib/data';

export const dynamic = 'force-dynamic';

type Props = { searchParams: Promise<{ repo?: string; repo_hash?: string }> };

export default async function Overview({ searchParams }: Props) {
  const repo = repoParam(await searchParams);

  const [latest, severities, fixCounts, scans, fixes, records] = await Promise.all([
    getLatestScans(repo),
    getLatestSeverityCounts(repo),
    getFixCounts(repo),
    getRecentScans(repo, null, 6),
    getFixes(repo, null, 6),
    getRecords(),
  ]);

  const failure = [latest, severities, fixCounts, scans, fixes].find((r) => !r.ok);
  if (failure && !failure.ok) {
    return (
      <>
        <PageHead title="Overview" />
        <Unavailable reason={failure.reason} />
      </>
    );
  }
  if (!latest.ok || !severities.ok || !fixCounts.ok || !scans.ok || !fixes.ok) return null;

  const scanStatus = (s: string) => latest.data.filter((x) => x.status === s).length;
  const totalFindings = Object.values(severities.data).reduce((a, b) => a + b, 0);
  const sevText = SEVERITY_ORDER.filter((s) => severities.data[s]).map((s) => `${severities.data[s]} ${s}`);
  const fc = fixCounts.data;
  const fixText = Object.entries(fc.byStatus).map(([s, n]) => `${n} ${s}`);
  const rate = fc.opened > 0 ? `${Math.round((fc.merged / fc.opened) * 100)}%` : '—';

  const reviewed = records.ok ? records.data.filter((r) => r.review_status === 'reviewed') : [];

  return (
    <>
      <PageHead title="Overview">
        {repo ? `Repository ${repo.slice(0, 12)}.` : 'All repositories.'} Totals use the latest scan for each repository
        and vendor.
      </PageHead>

      <dl className="stats">
        <div>
          <dt>Latest scans</dt>
          <dd className="stats__n">{latest.data.length}</dd>
          <dd className="stats__sub">
            {latest.data.length === 0
              ? 'None recorded'
              : `${scanStatus('completed')} completed, ${scanStatus('partial')} partial, ${scanStatus('failed')} failed`}
          </dd>
        </div>
        <div>
          <dt>Findings</dt>
          <dd className="stats__n">{totalFindings}</dd>
          <dd className="stats__sub">{sevText.length ? sevText.join(', ') : 'None in latest scans'}</dd>
        </div>
        <div>
          <dt>Fix attempts</dt>
          <dd className="stats__n">{fc.total}</dd>
          <dd className="stats__sub">{fixText.length ? fixText.join(', ') : 'None recorded'}</dd>
        </div>
        <div>
          <dt>Pull requests merged</dt>
          <dd className="stats__n">{rate}</dd>
          <dd className="stats__sub">
            {fc.opened > 0 ? `${fc.merged} of ${fc.opened} opened` : 'No pull requests opened yet'}
          </dd>
        </div>
      </dl>

      <div className="cols">
        <div className="cols__main">
          <section aria-labelledby="scans-h">
            <div className="sec-head">
              <h2 id="scans-h">Recent scans</h2>
              <Link href={repo ? `/dashboard/scans?repo=${repo}` : '/dashboard/scans'}>All scans</Link>
            </div>
            <div className="plate tbl-wrap">
              <ScanTable rows={scans.data} />
            </div>
          </section>

          <section aria-labelledby="fixes-h">
            <div className="sec-head">
              <h2 id="fixes-h">Recent fix attempts</h2>
              <Link href={repo ? `/dashboard/fixes?repo=${repo}` : '/dashboard/fixes'}>All fixes</Link>
            </div>
            <div className="plate tbl-wrap">
              <FixTable rows={fixes.data} />
            </div>
          </section>
        </div>

        <aside className="cols__side" aria-labelledby="records-h">
          <div className="sec-head">
            <h2 id="records-h">Vendor changes</h2>
            <Link href="/dashboard/registry">Registry</Link>
          </div>
          <div className="plate">
            {!records.ok ? (
              <p className="pad muted">Couldn’t read change records.</p>
            ) : reviewed.length === 0 ? (
              <p className="pad muted">
                No reviewed records in the database. The CLI reads <code>registry/*.yaml</code> from disk, and nothing
                copies those files into Postgres yet.
              </p>
            ) : (
              <ul className="changes">
                {reviewed.map((r) => {
                  const d = daysUntil(r.effective);
                  return (
                    <li key={r.id}>
                      <p className="changes__id">{r.id}</p>
                      <p className="muted">
                        {String(r.affects.symbol ?? r.type)}
                        {r.affects.param ? `: ${String(r.affects.param)} → ${String(r.affects.replacement_param ?? '')}` : ''}
                      </p>
                      <p className="changes__when">
                        Effective {r.effective.slice(0, 10)} <span className="muted">({describeDays(d)})</span>
                      </p>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </aside>
      </div>
    </>
  );
}
