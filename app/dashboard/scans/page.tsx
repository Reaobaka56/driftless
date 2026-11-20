import { ScanTable, StatusFilter } from '../_components/tables';
import { PageHead, Unavailable } from '../_components/ui';
import { SCAN_STATUSES, getRecentScans, oneOf, repoParam } from '../_lib/data';

export const dynamic = 'force-dynamic';

type Props = { searchParams: Promise<{ repo?: string; repo_hash?: string; status?: string }> };

export default async function Scans({ searchParams }: Props) {
  const sp = await searchParams;
  const repo = repoParam(sp);
  const status = oneOf(sp.status, SCAN_STATUSES);
  const scans = await getRecentScans(repo, status, 100);

  return (
    <>
      <PageHead title="Scans">Newest first, up to 100. One row per repository, vendor and commit.</PageHead>
      {!scans.ok ? (
        <Unavailable reason={scans.reason} />
      ) : (
        <>
          <StatusFilter base="/dashboard/scans" repo={repo} current={status} options={SCAN_STATUSES} />
          <div className="plate tbl-wrap">
            <ScanTable rows={scans.data} />
          </div>
        </>
      )}
    </>
  );
}
