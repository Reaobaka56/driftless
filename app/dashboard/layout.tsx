import type { Metadata } from 'next';
import Link from 'next/link';
import { Suspense } from 'react';
import { GitHubIcon, Logo } from '../_components/Logo';
import { REPO_URL } from '../_components/links';
import { RepoFilter, SideNav } from './_components/Chrome';
import { getRepos } from './_lib/data';
import './dashboard.css';

export const metadata: Metadata = {
  title: 'Dashboard · Driftless',
  // Open to anyone until auth lands, so keep it out of search indexes.
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

/**
 * Every /dashboard route renders inside this layout. When authentication is
 * added, gate it here once (check the session, redirect to sign-in) and all
 * dashboard pages are covered.
 */
export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const repos = await getRepos();

  return (
    <div className="shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <aside className="side">
        <Link className="side__brand" href="/" aria-label="Driftless, back to the site">
          <Logo />
          Driftless
        </Link>
        <Suspense fallback={<nav className="side__nav" aria-label="Dashboard sections" />}>
          <SideNav />
        </Suspense>
        <div className="side__foot">
          <Link href="/">Back to site</Link>
          <a href={REPO_URL} target="_blank" rel="noopener noreferrer">
            <GitHubIcon />
            Source<span className="visually-hidden"> (opens in a new tab)</span>
          </a>
        </div>
      </aside>

      <div className="shell__main">
        {/* The one glass layer: it floats over content scrolling underneath. */}
        <header className="bar glass">
          <Suspense fallback={null}>
            <RepoFilter repos={repos.ok ? repos.data : []} />
          </Suspense>
          <p className="bar__db">
            <span className={`dot ${repos.ok ? 'dot--on' : ''}`} aria-hidden="true" />
            {repos.ok ? 'Database connected' : repos.reason === 'not_configured' ? 'No database' : 'Database error'}
          </p>
        </header>
        <main id="main" className="content">
          {children}
        </main>
      </div>
    </div>
  );
}
