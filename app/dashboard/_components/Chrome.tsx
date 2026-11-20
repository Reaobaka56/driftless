'use client';

import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

const ITEMS = [
  { href: '/dashboard', label: 'Overview', exact: true },
  { href: '/dashboard/scans', label: 'Scans' },
  { href: '/dashboard/fixes', label: 'Fixes' },
  { href: '/dashboard/registry', label: 'Registry' },
];

/** Navigation keeps the selected repository when moving between sections. */
export function SideNav() {
  const pathname = usePathname();
  const sp = useSearchParams();
  const repo = sp.get('repo') ?? sp.get('repo_hash');
  const qs = repo ? `?repo=${encodeURIComponent(repo)}` : '';

  return (
    <nav className="side__nav" aria-label="Dashboard sections">
      {ITEMS.map((i) => {
        const active = i.exact ? pathname === i.href : pathname.startsWith(i.href);
        return (
          <Link key={i.href} href={`${i.href}${i.href === '/dashboard/registry' ? '' : qs}`} aria-current={active ? 'page' : undefined}>
            {i.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function RepoFilter({ repos }: { repos: string[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();
  const current = sp.get('repo') ?? sp.get('repo_hash') ?? '';

  function change(value: string) {
    const next = new URLSearchParams(sp.toString());
    next.delete('repo_hash');
    if (value) next.set('repo', value);
    else next.delete('repo');
    const q = next.toString();
    router.push(q ? `${pathname}?${q}` : pathname);
  }

  return (
    <label className="filter">
      <span>Repository</span>
      <select value={current} onChange={(e) => change(e.target.value)} disabled={repos.length === 0}>
        <option value="">{repos.length === 0 ? 'None recorded' : 'All repositories'}</option>
        {repos.map((r) => (
          <option key={r} value={r}>
            {r.slice(0, 12)}
          </option>
        ))}
      </select>
    </label>
  );
}
