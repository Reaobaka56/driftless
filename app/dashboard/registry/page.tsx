import { Empty, PageHead, Unavailable, daysUntil, describeDays } from '../_components/ui';
import { getRecords } from '../_lib/data';

export const dynamic = 'force-dynamic';

export default async function Registry() {
  const records = await getRecords();

  return (
    <>
      <PageHead title="Registry">
        Vendor changes Driftless knows how to fix, soonest effective date first. Only records marked reviewed are ever
        applied.
      </PageHead>
      {!records.ok ? (
        <Unavailable reason={records.reason} />
      ) : records.data.length === 0 ? (
        <div className="plate">
          <Empty title="No change records in the database">
            The CLI reads <code>registry/*.yaml</code> from disk. Nothing copies those files into Postgres yet, so this
            table is empty until records are inserted.
          </Empty>
        </div>
      ) : (
        <ul className="records">
          {records.data.map((r) => {
            const d = daysUntil(r.effective);
            const a = r.affects as Record<string, string | undefined>;
            return (
              <li key={r.id} className="plate record">
                <div className="record__head">
                  <h2 className="record__id">{r.id}</h2>
                  <p className={`record__review ${r.review_status === 'reviewed' ? '' : 'record__review--draft'}`}>
                    {r.review_status === 'reviewed' ? 'Reviewed' : 'Not reviewed'}
                    {r.reviewed_by ? ` by ${r.reviewed_by}` : ''}
                  </p>
                </div>
                <p>{r.migration_note}</p>
                <dl className="facts">
                  <div>
                    <dt>Vendor</dt>
                    <dd>{r.vendor}</dd>
                  </div>
                  <div>
                    <dt>Change</dt>
                    <dd>{r.type}</dd>
                  </div>
                  <div>
                    <dt>Symbol</dt>
                    <dd className="mono">{a.symbol ?? '—'}</dd>
                  </div>
                  {a.param && (
                    <div>
                      <dt>Argument</dt>
                      <dd className="mono">
                        {a.param} → {a.replacement_param ?? '—'}
                      </dd>
                    </div>
                  )}
                  <div>
                    <dt>Effective</dt>
                    <dd>
                      {r.effective.slice(0, 10)} <span className="muted">({describeDays(d)})</span>
                    </dd>
                  </div>
                  <div>
                    <dt>Recipe</dt>
                    <dd className="mono">{r.recipe ?? 'none'}</dd>
                  </div>
                  <div>
                    <dt>Attempts</dt>
                    <dd>
                      {r.stats_attempts}, {r.stats_merged_unedited} merged unedited
                    </dd>
                  </div>
                </dl>
                {/^https:\/\//.test(r.source_url) && (
                  <a className="record__src" href={r.source_url} target="_blank" rel="noopener noreferrer">
                    Vendor notice<span className="visually-hidden"> (opens in a new tab)</span>
                  </a>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
