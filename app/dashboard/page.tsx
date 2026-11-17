import { sql } from '@vercel/postgres';

export const dynamic = 'force-dynamic';

export default async function Dashboard({ searchParams }: { searchParams: { repo_hash?: string } }) {
  const repoHash = searchParams.repo_hash ?? '';
  const { rows } = await sql`
    SELECT id, record_id, status, pr_url FROM fix_attempts
    WHERE repo_hash = ${repoHash} ORDER BY created_at DESC LIMIT 50`;
  const done = rows.filter((a) => a.status === 'merged').length;
  const rate = rows.length ? ((done / rows.length) * 100).toFixed(1) : '0.0';
  return (
    <main>
      <h1>Driftless Dashboard</h1>
      <p>Accepted-PR rate: {rate}%</p>
      <ul>
        {rows.map((a) => (
          <li key={a.id}>
            {a.record_id} - {a.status} {a.pr_url && <a href={a.pr_url}>View PR</a>}
          </li>
        ))}
      </ul>
    </main>
  );
}
