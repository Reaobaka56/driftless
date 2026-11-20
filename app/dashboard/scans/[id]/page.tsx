import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Empty, PageHead, RelTime, SEVERITY_ORDER, Severity, ShortHash, Status, Unavailable } from '../../_components/ui';
import { getScan, isUuid } from '../../_lib/data';

export const dynamic = 'force-dynamic';

type Props = { params: Promise<{ id: string }> };

export default async function ScanDetail({ params }: Props) {
  const { id } = await params;
  if (!isUuid(id)) notFound();

  const res = await getScan(id);
  if (!res.ok) {
    return (
      <>
        <PageHead title="Scan" />
        <Unavailable reason={res.reason} />
      </>
    );
  }
  const scan = res.data;
  if (!scan) notFound();

  const findings = [...(Array.isArray(scan.findings) ? scan.findings : [])].sort(
    (a, b) =>
      SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity) ||
      a.file.localeCompare(b.file) ||
      a.start_line - b.start_line,
  );
  const caps = scan.analysis?.capabilities ?? [];
  const parseErrors = scan.analysis?.parse_errors?.length ?? 0;
  const skipped = scan.analysis?.skipped_files?.length ?? 0;

  return (
    <>
      <p className="crumb">
        <Link href="/dashboard/scans">Scans</Link>
      </p>
      <PageHead title={`${scan.vendor} scan`}>
        Repository <ShortHash value={scan.repo_hash} length={12} />
        {scan.commit_sha && (
          <>
            {' '}
            at <ShortHash value={scan.commit_sha} length={7} />
          </>
        )}
        , scanned <RelTime value={scan.scanned_at} />.
      </PageHead>

      <div className="plate">
        <dl className="facts facts--row">
          <div>
            <dt>Status</dt>
            <dd>
              <Status value={scan.status} />
            </dd>
          </div>
          <div>
            <dt>Findings</dt>
            <dd>{scan.finding_count}</dd>
          </div>
          {scan.analysis?.files_scanned !== undefined && (
            <div>
              <dt>Files analysed</dt>
              <dd>{scan.analysis.files_scanned}</dd>
            </div>
          )}
          {(parseErrors > 0 || skipped > 0) && (
            <div>
              <dt>Not analysed</dt>
              <dd>
                {parseErrors} parse errors, {skipped} skipped
              </dd>
            </div>
          )}
        </dl>
        {scan.error && (
          <p className="pad error-line">
            <span className="visually-hidden">Error: </span>
            {scan.error}
          </p>
        )}
      </div>

      {caps.length > 0 && (
        <section aria-labelledby="caps-h">
          <div className="sec-head">
            <h2 id="caps-h">What ran</h2>
          </div>
          <div className="plate tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th scope="col">Scanner</th>
                  <th scope="col">Result</th>
                  <th scope="col">Detail</th>
                </tr>
              </thead>
              <tbody>
                {caps.map((c) => (
                  <tr key={c.name}>
                    <td data-label="Scanner">{c.name}</td>
                    <td data-label="Result">{c.status.replace('_', ' ')}</td>
                    <td data-label="Detail" className="break muted">
                      {c.detail || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section aria-labelledby="find-h">
        <div className="sec-head">
          <h2 id="find-h">Findings</h2>
        </div>
        {findings.length === 0 ? (
          <div className="plate">
            <Empty title={scan.status === 'completed' ? 'No findings' : 'No findings recorded'}>
              {scan.status === 'completed'
                ? 'Every scanner that applied ran to completion.'
                : 'This scan did not complete, so an empty list does not mean the code is clean. See what ran, above.'}
            </Empty>
          </div>
        ) : (
          <ol className="findings">
            {findings.map((f) => (
              <li key={`${f.rule_id}:${f.file}:${f.start_line}`} className="plate finding">
                <div className="finding__head">
                  <Severity value={f.severity} />
                  <code className="finding__rule">{f.rule_id}</code>
                  <code className="finding__loc">
                    {f.file}:{f.start_line}
                    {f.end_line !== f.start_line ? `-${f.end_line}` : ''}
                  </code>
                </div>
                <p>{f.description}</p>
                <pre className="finding__ev" tabIndex={0} aria-label="Evidence from the code">
                  <code>{f.evidence}</code>
                </pre>
                <p className="muted">
                  <span className="finding__k">Fix</span> {f.remediation}
                </p>
                <p className="finding__meta">
                  Source {f.source}, confidence {f.confidence.toFixed(2)}
                </p>
              </li>
            ))}
          </ol>
        )}
      </section>
    </>
  );
}
