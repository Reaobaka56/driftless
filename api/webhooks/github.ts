import { sql } from '@vercel/postgres';

export const config = { runtime: 'edge' };

async function hmacHex(secret: string, body: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(body));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}

export default async function handler(req: Request) {
  if (req.method !== 'POST') return new Response('Method Not Allowed', { status: 405 });
  const body = await req.text();
  const expected = 'sha256=' + (await hmacHex(process.env.GITHUB_WEBHOOK_SECRET!, body));
  if (!safeEqual(req.headers.get('x-hub-signature-256') ?? '', expected)) {
    return new Response('Unauthorized', { status: 401 });
  }

  const event = JSON.parse(body);
  if (event.action === 'closed' && event.pull_request) {
    const id = event.pull_request.body?.match(/^record: (\S+)/m)?.[1];
    if (id) {
      const merged = !!event.pull_request.merged;
      await sql`
        UPDATE change_records
        SET stats_attempts = stats_attempts + 1,
            stats_merged_unedited = stats_merged_unedited + ${merged ? 1 : 0}
        WHERE id = ${id}`;
    }
  }
  return new Response('OK', { status: 200 });
}
