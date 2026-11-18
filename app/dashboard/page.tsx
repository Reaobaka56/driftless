import { sql } from '@vercel/postgres';

export const dynamic = 'force-dynamic';

type DashboardProps = {
  searchParams: Promise<{ repo_hash?: string }>;
};

export default async function Dashboard({ searchParams }: DashboardProps) {
  const { repo_hash: repoHash = '' } = await searchParams;

  const { rows } = await sql`
    SELECT id, record_id, status, pr_url FROM fix_attempts
    WHERE repo_hash = ${repoHash} ORDER BY created_at DESC LIMIT 50`;
  const done = rows.filter((a) => a.status === 'merged').length;
  const rate = rows.length ? ((done / rows.length) * 100).toFixed(1) : '0.0';

  return (
    <main className="dash">
      <h1>Driftless Dashboard</h1>
      <p className="dash__stat">Accepted-PR rate: {rate}%</p>
      {rows.length === 0 && <p className="dash__empty">No fix attempts recorded for this repository yet.</p>}
      <ul className="dash__list">
        {rows.map((a) => (
          <li key={a.id}>
            {a.record_id} - {a.status} {a.pr_url && <a href={a.pr_url}>View PR</a>}
          </li>
        ))}
      </ul>
    </main>
  );
}

// Next.js 15: searchParams is asynchronous and must be awaited.
