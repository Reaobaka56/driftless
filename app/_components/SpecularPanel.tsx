'use client';

import type { PointerEvent, ReactNode } from 'react';

/** Glass panel whose specular highlight follows the pointer (fine pointers, motion allowed). */
export function SpecularPanel({ children, className = '' }: { children: ReactNode; className?: string }) {
  function onMove(e: PointerEvent<HTMLDivElement>) {
    if (e.pointerType !== 'mouse') return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const el = e.currentTarget;
    const r = el.getBoundingClientRect();
    el.style.setProperty('--mx', `${e.clientX - r.left}px`);
    el.style.setProperty('--my', `${e.clientY - r.top}px`);
  }

  return (
    <div className={className} onPointerMove={onMove}>
      {children}
    </div>
  );
}
