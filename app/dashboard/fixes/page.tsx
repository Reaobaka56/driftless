import { FixTable, StatusFilter } from '../_components/tables';
import { PageHead, Unavailable } from '../_components/ui';
import { FIX_STATUSES, getFixes, oneOf, repoParam } from '../_lib/data';

export const dynamic = 'force-dynamic';

type Props = { searchParams: Promise<{ repo?: string; repo_hash?: string; status?: string }> };

export default async function Fixes({ searchParams }: Props) {
  const sp = await searchParams;
  const repo = repoParam(sp);
  const status = oneOf(sp.status, FIX_STATUSES);
  const fixes = await getFixes(repo, status, 100);

  return (
    <>
      <PageHead title="Fixes">Newest first, up to 100. Driftless never merges; “merged” means a person did.</PageHead>
      {!fixes.ok ? (
        <Unavailable reason={fixes.reason} />
      ) : (
        <>
          <StatusFilter base="/dashboard/fixes" repo={repo} current={status} options={FIX_STATUSES} />
          <div className="plate tbl-wrap">
            <FixTable rows={fixes.data} />
          </div>
        </>
      )}
    </>
  );
}
