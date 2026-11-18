import { GitHubIcon, Logo } from './_components/Logo';
import { REPO_URL, Nav } from './_components/Nav';
import { Reveal } from './_components/Reveal';
import { SpecularPanel } from './_components/SpecularPanel';
import './landing.css';

const STEPS = [
  {
    title: 'Finds real call sites, not text matches.',
    body: (
      <>
        A syntax-tree scan matches the exact call and keyword, and only in files that import the vendor&rsquo;s SDK.
        Same-named methods from other libraries are left alone.
      </>
    ),
  },
  {
    title: 'Applies a reviewed recipe.',
    body: (
      <>
        Each vendor change is a registry record that a person has reviewed. The recipe rewrites only the affected
        arguments, and produces the same output on every run.
      </>
    ),
  },
  {
    title: 'Proves it, or puts it back.',
    body: (
      <>
        After the edit, Driftless re-scans and runs your tests. If either fails, the changes are reverted and the
        result is reported as failed, not hidden.
      </>
    ),
  },
  {
    title: 'You make the call.',
    body: (
      <>
        The result is a patch with a confidence score and notes on anything Driftless refused to touch. Nothing is
        ever merged automatically. Delivering it as a draft pull request is next on the roadmap.
      </>
    ),
  },
];

const PRINCIPLES = [
  {
    t: 'Reviewed, not improvised',
    d: 'Fixes come from registry records a human has signed off, not from a model guessing at a patch.',
  },
  {
    t: 'Refuses ambiguity',
    d: 'If a call passes both the old and the new argument, or repeats one, Driftless leaves it untouched and says so.',
  },
  {
    t: 'Read-only scanning',
    d: 'The scan worker clones, analyses and records findings. It has no ability to modify a repository, create a branch or open a pull request.',
  },
  {
    t: 'Honest about failure',
    d: 'If a scanner can’t run, the scan is marked partial or failed. It is never reported as a clean zero.',
  },
  {
    t: 'AI is optional, never required',
    d: 'Optional LLM analysis can add findings through a provider fallback chain, and every finding must cite real lines of your code. With no LLM available, the scan still completes with its deterministic results.',
    wide: true,
  },
];

const WORKING = [
  ['Python call-site detection', 'Syntax-tree based, gated on the vendor import.'],
  ['Keyword-rename recipe', 'Validated inputs, atomic writes, automatic revert.'],
  ['TypeScript and JavaScript scanner', 'Nine rules covering security and error-handling mistakes.'],
  ['Scan worker and registry API', 'Records findings per repository and commit.'],
];

const NEXT = [
  ['More recipes and records', 'The registry holds one record today: Stripe Charge.create, source → payment_method.'],
  ['Draft pull request delivery', 'The fix workflow is a separate step from scanning.'],
  ['TypeScript fixes', 'TypeScript and JavaScript are scanned, not yet fixed.'],
  ['Drafting records from changelogs', 'A person would still review each record.'],
];

export default function Home() {
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <Nav />

      <div id="top" style={{ position: 'relative', overflow: 'clip' }}>
        <div className="atmosphere" aria-hidden="true">
          <div className="ring" />
        </div>

        <main id="main">
          <section className="hero" aria-labelledby="hero-title">
            <div className="container hero__grid">
              <div>
                <p className="eyebrow" data-rise style={{ '--i': 0 } as React.CSSProperties}>
                  Self-maintaining API integrations
                </p>
                <h1 id="hero-title" data-rise style={{ '--i': 1 } as React.CSSProperties}>
                  Vendor APIs change. Your integrations shouldn&rsquo;t break.
                </h1>
                <p className="hero__lede" data-rise style={{ '--i': 2 } as React.CSSProperties}>
                  Driftless finds the exact call sites an API change breaks, applies a reviewed fix, proves it with a
                  re-scan and your own tests, and leaves the merge to you.
                </p>
                <div className="hero__actions" data-rise style={{ '--i': 3 } as React.CSSProperties}>
                  <a className="btn btn--primary" href={REPO_URL} target="_blank" rel="noopener noreferrer">
                    <GitHubIcon />
                    View on GitHub
                    <span className="visually-hidden"> (opens in a new tab)</span>
                  </a>
                  <a className="btn btn--ghost glass" href="#process">
                    See how it works
                  </a>
                </div>
                <ul className="hero__assure" data-rise style={{ '--i': 4 } as React.CSSProperties}>
                  <li>Reviewed recipes</li>
                  <li>Auto-revert on failed checks</li>
                  <li>Nothing merges without you</li>
                </ul>
              </div>

              <div data-rise style={{ '--i': 3 } as React.CSSProperties}>
                <SpecularPanel className="term glass">
                  <div className="term__bar">
                    <span className="term__dots" aria-hidden="true">
                      <i />
                      <i />
                      <i />
                    </span>
                    <span>driftless · checkout service</span>
                  </div>
                  <pre className="term__body" tabIndex={0} aria-label="Terminal output: scan, fix and resulting diff">
                    <code>
                      <span className="t-prompt">$ </span>driftless scan ./checkout --vendor stripe{'\n'}
                      <span className="t-dim">app.py:5 Charge.create (record: stripe-2026-11-17-charge-source)</span>
                      <span className="t-gap" />
                      <span className="t-prompt">$ </span>driftless fix stripe-2026-11-17-charge-source ./checkout{'\n'}
                      <span className="t-dim">success confidence=0.8 files=[&apos;app.py&apos;]</span>
                      <span className="t-gap" />
                      <span className="t-dim">app.py</span>
                      {'\n'}
                      <span className="t-del">- return stripe.Charge.create(amount=100, currency=&quot;usd&quot;, source=token)</span>
                      {'\n'}
                      <span className="t-add">+ return stripe.Charge.create(amount=100, currency=&quot;usd&quot;, payment_method=token)</span>
                    </code>
                  </pre>
                  <p className="term__cap">Real output from the CLI against the sample repository in the test suite.</p>
                </SpecularPanel>
              </div>
            </div>
          </section>

          <section id="process" className="section" aria-labelledby="process-title">
            <div className="container split">
              <div className="split__lead">
                <Reveal>
                  <span className="section__label">How it works</span>
                  <h2 id="process-title">Four steps from a vendor notice to a verified patch.</h2>
                  <p className="section__intro">
                    Every deprecation notice becomes a hunt through your codebase. Driftless turns the hunt into a
                    pipeline you can audit.
                  </p>
                </Reveal>
              </div>
              <ol className="steps" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {STEPS.map((s, i) => (
                  <li key={s.title}>
                    <Reveal delay={i * 40}>
                      <div className="step">
                        <span className="step__n" aria-hidden="true">
                          {String(i + 1).padStart(2, '0')}
                        </span>
                        <div>
                          <h3>
                            <span className="visually-hidden">Step {i + 1}: </span>
                            {s.title}
                          </h3>
                          <p>{s.body}</p>
                        </div>
                      </div>
                    </Reveal>
                  </li>
                ))}
              </ol>
            </div>
          </section>

          <section id="principles" className="section section--deep" aria-labelledby="principles-title">
            <div className="container">
              <Reveal>
                <span className="section__label">Principles</span>
                <h2 id="principles-title">Built to be trusted with someone else&rsquo;s code.</h2>
                <p className="section__intro">
                  An unattended tool that edits source has to be predictable first and clever second.
                </p>
              </Reveal>
              <Reveal delay={60}>
                <dl className="principles">
                  {PRINCIPLES.map((p) => (
                    <div key={p.t} className={`principle${p.wide ? ' principle--wide' : ''}`}>
                      <dt>{p.t}</dt>
                      <dd>{p.d}</dd>
                    </div>
                  ))}
                </dl>
              </Reveal>
            </div>
          </section>

          <section id="status" className="section" aria-labelledby="status-title">
            <div className="container">
              <Reveal>
                <span className="section__label">Status</span>
                <h2 id="status-title">Early, and specific about it.</h2>
                <p className="section__intro">What works today, and what doesn&rsquo;t exist yet.</p>
              </Reveal>
              <Reveal delay={60}>
                <div className="ledger">
                  <div>
                    <h3>Working today</h3>
                    <ul>
                      {WORKING.map(([t, d]) => (
                        <li key={t}>
                          <i className="mark mark--done" aria-hidden="true" />
                          <div>
                            {t}
                            <span>{d}</span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h3>Not built yet</h3>
                    <ul>
                      {NEXT.map(([t, d]) => (
                        <li key={t}>
                          <i className="mark mark--next" aria-hidden="true" />
                          <div>
                            {t}
                            <span>{d}</span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </Reveal>
            </div>
          </section>

          <section className="closer" aria-labelledby="closer-title">
            <div className="container">
              <Reveal>
                <h2 id="closer-title">Follow the build.</h2>
                <p>Driftless is open on GitHub. Read the code, run it on a repository, and tell us what it misses.</p>
                <a className="btn btn--primary" href={REPO_URL} target="_blank" rel="noopener noreferrer">
                  <GitHubIcon />
                  View on GitHub
                  <span className="visually-hidden"> (opens in a new tab)</span>
                </a>
              </Reveal>
            </div>
          </section>
        </main>
      </div>

      <footer className="footer">
        <div className="container">
          <div className="footer__row">
            <a className="brand" href="#top" aria-label="Driftless, back to top">
              <Logo />
              Driftless
            </a>
            <nav className="footer__links" aria-label="Footer">
              <a href="#process">How it works</a>
              <a href="#principles">Principles</a>
              <a href="#status">Status</a>
              <a href="/dashboard">Dashboard</a>
              <a href={REPO_URL} target="_blank" rel="noopener noreferrer">
                GitHub<span className="visually-hidden"> (opens in a new tab)</span>
              </a>
            </nav>
          </div>
          <p className="footer__fine">© 2026 Driftless. Early software: review every change before you merge it.</p>
        </div>
      </footer>
    </>
  );
}
