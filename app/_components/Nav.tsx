'use client';

import { useEffect, useState } from 'react';
import { GitHubIcon, Logo } from './Logo';

export const REPO_URL = 'https://github.com/Reaobaka56/driftless';

const LINKS = [
  { id: 'process', label: 'How it works' },
  { id: 'principles', label: 'Principles' },
  { id: 'status', label: 'Status' },
];

export function Nav() {
  const [active, setActive] = useState<string>('');

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
      <div className="nav__inner">
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
        <a className="btn btn--primary" href={REPO_URL} target="_blank" rel="noopener noreferrer">
          <GitHubIcon />
          GitHub
          <span className="visually-hidden"> (opens in a new tab)</span>
        </a>
      </div>
    </header>
  );
}
