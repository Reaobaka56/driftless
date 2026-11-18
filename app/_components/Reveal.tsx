'use client';

import { useEffect, useRef, type CSSProperties, type ReactNode } from 'react';

/** Fades/raises content in once. Content stays visible without JS and under reduced motion. */
export function Reveal({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (el.getBoundingClientRect().top < window.innerHeight * 0.9) {
      el.dataset.state = 'in';
      return;
    }
    el.dataset.state = 'armed';
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.dataset.state = 'in';
          io.disconnect();
        }
      },
      { rootMargin: '0px 0px -10% 0px' },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div ref={ref} className="reveal" style={{ '--d': `${delay}ms` } as CSSProperties}>
      {children}
    </div>
  );
}
