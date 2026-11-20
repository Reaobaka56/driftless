import type { ReactNode } from 'react';

type Tone = 'ok' | 'warn' | 'bad' | 'wait';

const STATUS_TONE: Record<string, Tone> = {
  completed: 'ok',
  success: 'ok',
  merged: 'ok',
  partial: 'warn',
  draft: 'warn',
  failed: 'bad',
  running: 'wait',
  pending: 'wait',
  scanned: 'wait',
};

/** Shape plus word. Colour is a bonus, never the only signal. */
function Glyph({ tone }: { tone: Tone }) {
  return (
    <svg className={`glyph glyph--${tone}`} viewBox="0 0 12 12" aria-hidden="true" focusable="false">
      {tone === 'ok' && <circle cx="6" cy="6" r="4.5" fill="currentColor" />}
      {tone === 'warn' && (
        <>
          <circle cx="6" cy="6" r="4.25" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <path d="M6 1.75a4.25 4.25 0 0 1 0 8.5Z" fill="currentColor" />
        </>
      )}
      {tone === 'bad' && (
        <>
          <circle cx="6" cy="6" r="4.25" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <path d="M4.2 4.2l3.6 3.6M7.8 4.2L4.2 7.8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
        </>
      )}
      {tone === 'wait' && <circle cx="6" cy="6" r="4.25" fill="none" stroke="currentColor" strokeWidth="1.5" />}
    </svg>
  );
}

export function Status({ value }: { value: string }) {
  return (
    <span className="status">
      <Glyph tone={STATUS_TONE[value] ?? 'wait'} />
      {value[0].toUpperCase() + value.slice(1)}
    </span>
  );
}

const SEVERITY_TONE: Record<string, Tone> = { critical: 'bad', high: 'bad', medium: 'warn', low: 'wait', info: 'wait' };

export function Severity({ value }: { value: string }) {
  return (
    <span className="status">
      <Glyph tone={SEVERITY_TONE[value] ?? 'wait'} />
      {value[0].toUpperCase() + value.slice(1)}
    </span>
  );
}

export const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info'];

export function ShortHash({ value, length = 8 }: { value: string; length?: number }) {
  return (
    <code className="hash" title={value}>
      {value.slice(0, length)}
    </code>
  );
}

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['day', 86_400_000],
  ['hour', 3_600_000],
  ['minute', 60_000],
];
const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });

export function relativeTime(d: Date, now = Date.now()): string {
  const diff = d.getTime() - now;
  for (const [unit, ms] of UNITS) {
    if (Math.abs(diff) >= ms) return rtf.format(Math.round(diff / ms), unit);
  }
  return 'just now';
}

export function RelTime({ value }: { value: Date | string }) {
  const d = new Date(value);
  return (
    <time dateTime={d.toISOString()} title={d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC'}>
      {relativeTime(d)}
    </time>
  );
}

/** Days from today (UTC date) to a YYYY-MM-DD string. */
export function daysUntil(isoDate: string, now = new Date()): number {
  const target = Date.parse(isoDate.slice(0, 10) + 'T00:00:00Z');
  const today = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  return Math.round((target - today) / 86_400_000);
}

export function describeDays(n: number): string {
  if (n === 0) return 'today';
  if (n === 1) return 'tomorrow';
  if (n === -1) return 'yesterday';
  return n > 0 ? `in ${n} days` : `${-n} days ago`;
}

export function PageHead({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <header className="page-head">
      <h1>{title}</h1>
      {children && <p>{children}</p>}
    </header>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <p className="empty__title">{title}</p>
      {children && <p>{children}</p>}
    </div>
  );
}

/** Shown instead of data when the database can't be read. Says what to do, not just what broke. */
export function Unavailable({ reason }: { reason: 'not_configured' | 'error' }) {
  if (reason === 'error') {
    return (
      <div className="plate notice" role="status">
        <p className="notice__title">Couldn’t read from the database</p>
        <p>
          The connection is configured but the query failed. The error is in the server log. Check that migrations{' '}
          <code>001_init.sql</code> and <code>002_scan_analysis.sql</code> have been applied.
        </p>
      </div>
    );
  }
  return (
    <div className="plate notice" role="status">
      <p className="notice__title">No database connected</p>
      <p>
        The dashboard reads scan and fix records from Postgres. Set <code>POSTGRES_URL</code> and apply{' '}
        <code>migrations/001_init.sql</code> and <code>migrations/002_scan_analysis.sql</code>. Nothing is shown here
        until then, because there is nothing real to show.
      </p>
    </div>
  );
}
