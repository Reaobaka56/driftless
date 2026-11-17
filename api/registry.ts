import { sql } from '@vercel/postgres';

export const config = { runtime: 'edge' };

export default async function handler(req: Request) {
  if (req.method !== 'GET') return new Response('Method Not Allowed', { status: 405 });
  const vendor = new URL(req.url).searchParams.get('vendor');

  const { rows } = vendor
    ? await sql`SELECT * FROM change_records WHERE review_status = 'reviewed' AND vendor = ${vendor}`
    : await sql`SELECT * FROM change_records WHERE review_status = 'reviewed'`;

  return new Response(JSON.stringify(rows), {
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 's-maxage=60, stale-while-revalidate=300',
    },
  });
}
