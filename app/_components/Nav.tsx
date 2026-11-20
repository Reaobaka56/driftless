'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Logo } from './Logo';

const LINKS = [
  { id: 'process', label: 'How it works' },
  { id: 'limits', label: 'Guarantees' },
  { id: 'status', label: 'Status' },
  { id: 'run', label: 'Run it' },
];

/** Floating site bar: the one place glass is used on the landing page. */
export function Nav() {
  const [active, setActive] = useState('');

  useEffect(() => {
    const els = LINKS.map((l) => document.getElementById(l.id)).filter((e): e is HTMLElement => !!e);
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) if (e.isIntersecting) setActive(e.target.id);
      },
      { rootMargin: '-45% 0px -50% 0px' },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <header className="nav glass">
      <div className="container nav__inner">
        <a className="brand" href="#top" aria-label="Driftless, back to top">
          <Logo />
          Driftless
        </a>
        <nav className="nav__links" aria-label="Page sections">
          {LINKS.map((l) => (
            <a key={l.id} href={`#${l.id}`} aria-current={active === l.id ? 'true' : undefined}>
              {l.label}
            </a>
          ))}
        </nav>
        <Link className="btn btn--primary btn--sm nav__cta" href="/dashboard">
          Open dashboard
        </Link>
      </div>
    </header>
  );
}
