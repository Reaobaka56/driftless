import Link from 'next/link';
import { GitHubIcon, Logo } from './_components/Logo';
import { CopyButton } from './_components/CopyButton';
import { Nav } from './_components/Nav';
import { REPO_URL, repoFile } from './_components/links';
import './landing.css';

const RUN_COMMANDS = `git clone ${REPO_URL}
cd driftless
pip install -e ".[dev,worker]"
(cd src/driftless/scanners/ts && npm install)

driftless scan path/to/repo --vendor stripe
driftless fix stripe-2026-11-17-charge-source path/to/repo --dry-run`;

const GUARANTEES = [
  {
    title: 'Edit a file that doesn’t import the SDK',
    body: 'Detection is a syntax-tree match gated on the vendor import. Strings, comments and unrelated files are never matched.',
    file: 'src/driftless/detect/python_ast.py',
  },
  {
    title: 'Guess at an ambiguous call',
    body: 'If a call passes both the old and the new argument, or repeats the old one, it is left exactly as it was and listed as skipped.',
    file: 'src/driftless/fix/recipes.py',
  },
  {
    title: 'Keep an edit it couldn’t verify',
    body: 'If the re-scan still finds the call, or the repository’s tests fail, every file it touched is restored.',
    file: 'src/driftless/fix/pipeline.py',
  },
  {
    title: 'Write outside the repository',
    body: 'Symlinks and paths that resolve outside the repo are refused. Writes go to a temporary file that atomically replaces the original.',
    file: 'src/driftless/fix/recipes.py',
  },
  {
    title: 'Report a clean scan it didn’t run',
    body: 'When a scanner can’t run, the scan is marked partial or failed and the reason is recorded. It is never reported as zero findings.',
    file: 'src/driftless/pipeline.py',
  },
  {
    title: 'Trust a model’s output',
    body: 'LLM analysis is optional. A finding is dropped unless it cites lines in a file that was analysed and its evidence appears at those lines.',
    file: 'src/driftless/llm/validate.py',
  },
  {
    title: 'Modify a repository while scanning',
    body: 'The scan worker clones read-only and records findings. It cannot fix, branch, commit or open a pull request.',
    file: 'worker/tasks.py',
  },
];

const WORKING: [string, string][] = [
  ['Python call-site detection', 'Syntax-tree based, gated on the vendor import.'],
  ['Keyword-rename recipe', 'Validated inputs, atomic writes, automatic revert.'],
  ['TypeScript and JavaScript scanner', 'Nine rules for security and error-handling mistakes. Scans only.'],
  ['Scan worker and registry API', 'Records findings per repository and commit. Needs Postgres and Redis.'],
  ['Dashboard', 'Reads scan and fix records from Postgres.'],
];

const NEXT: [string, string][] = [
  ['More recipes and records', 'The registry holds one record: Stripe Charge.create, source to payment_method.'],
  ['Draft pull request delivery', 'Scanning and fixing are separate steps. The workflow that joins them doesn’t exist yet.'],
  ['TypeScript fixes', 'TypeScript and JavaScript are scanned, not fixed.'],
  ['Records drafted from changelogs', 'A person would still review each one.'],
];

export default function Home() {
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <Nav />

      <main id="main">
        {/* ───────── Hero ───────── */}
        <section id="top" className="hero" aria-labelledby="hero-title">
          <div className="container hero__grid">
            <div className="hero__copy">
              <h1 id="hero-title">
                <span className="h1__a">Your vendor changed the API.</span>{' '}
                <span className="h1__b">Driftless writes the patch.</span>
              </h1>
              <p className="hero__lede">
                It finds the exact calls a vendor change breaks, rewrites them with a recipe a person has reviewed, then
                re-scans and runs your pytest suite if there is one. If a check fails, the edit is reverted. You decide
                what merges.
              </p>
              <div className="hero__actions">
                <Link className="btn btn--primary" href="/dashboard">
                  Open dashboard
                </Link>
                <a className="btn btn--outline" href={REPO_URL} target="_blank" rel="noopener noreferrer">
                  <GitHubIcon />
                  View source
                  <span className="visually-hidden"> (opens in a new tab)</span>
                </a>
              </div>
              <dl className="hero__scope">
                <div>
                  <dt>Python</dt>
                  <dd>scan and fix</dd>
                </div>
                <div>
                  <dt>TypeScript, JavaScript</dt>
                  <dd>scan only</dd>
                </div>
                <div>
                  <dt>Registry</dt>
                  <dd>1 record, Stripe</dd>
                </div>
              </dl>
            </div>

            <figure className="hero__plate">
              <div className="plate session">
                <div className="session__bar">
                  <span>app.py</span>
                  <span>1 call site, 1 file changed</span>
                </div>
                <pre className="session__cmds" tabIndex={0} aria-label="Commands and their output">
                  <code>
                    <span className="t-prompt">$ </span>driftless scan ./checkout --vendor stripe{'\n'}
                    <span className="t-dim">app.py:5 Charge.create (record: stripe-2026-11-17-charge-source)</span>
                    {'\n'}
                    <span className="t-prompt">$ </span>driftless fix stripe-2026-11-17-charge-source ./checkout{'\n'}
                    <span className="t-dim">success confidence=0.8 files=[&apos;app.py&apos;]</span>
                  </code>
                </pre>
                <pre className="diff" tabIndex={0} aria-label="Before and after of app.py">
                  <code>
                    <span className="row">
                      <span className="gut">4</span>
                      <span className="sign" aria-hidden="true">
                        {' '}
                      </span>
                      def charge(token):
                    </span>
                    <span className="row row--del">
                      <span className="gut">5</span>
                      <span className="sign" aria-hidden="true">
                        -
                      </span>
                      <span className="visually-hidden">Removed: </span>
                      {'    return stripe.Charge.create(amount=100, currency="usd", '}
                      <mark>source</mark>
                      {'=token)'}
                    </span>
                    <span className="row row--add">
                      <span className="gut">5</span>
                      <span className="sign" aria-hidden="true">
                        +
                      </span>
                      <span className="visually-hidden">Added: </span>
                      {'    return stripe.Charge.create(amount=100, currency="usd", '}
                      <mark>payment_method</mark>
                      {'=token)'}
                    </span>
                    <span className="row row--gap" aria-hidden="true">
                      <span className="gut">⋮</span>
                    </span>
                    <span className="row row--quiet">
                      <span className="gut">9</span>
                      <span className="sign" aria-hidden="true">
                        {' '}
                      </span>
                      {'    return stripe.Customer.create(email="a@b.c")'}
                    </span>
                  </code>
                </pre>
              </div>
              <figcaption>
                Real output from the two commands, run against the sample repository in <code>tests/fixtures</code>. The
                diff is drawn from the file before and after. Line 9 uses the same SDK but a different call, so it is
                untouched.
              </figcaption>
            </figure>
          </div>
        </section>

        {/* ───────── How it works ───────── */}
        <section id="process" className="section" aria-labelledby="process-title">
          <div className="container">
            <header className="section__head">
              <h2 id="process-title">Four steps. Each leaves something you can inspect.</h2>
            </header>

            <ol className="steps">
              <li className="step">
                <div className="step__text">
                  <p className="step__n">Step 1</p>
                  <h3>Find the call, not the string.</h3>
                  <p>
                    Driftless matches the exact call and keyword in the syntax tree, and only in files that import the
                    vendor SDK. Strings, comments and unrelated files are never matched.
                  </p>
                </div>
                <div className="plate art">
                  <pre tabIndex={0} aria-label="Output of driftless scan">
                    <code>
                      <span className="t-prompt">$ </span>driftless scan ./checkout --vendor stripe{'\n'}
                      <span className="t-dim">app.py:5 Charge.create (record: stripe-2026-11-17-charge-source)</span>
                    </code>
                  </pre>
                </div>
              </li>

              <li className="step">
                <div className="step__text">
                  <p className="step__n">Step 2</p>
                  <h3>Apply a recipe a person reviewed.</h3>
                  <p>
                    Each vendor change is a registry record. Its recipe, <code>rename_keyword</code>, rewrites only the
                    named argument, and gives the same output on every run. Records not marked reviewed are ignored.
                  </p>
                </div>
                <div className="plate art">
                  <p className="art__label">registry/stripe/stripe-2026-11-17-charge-source.yaml (excerpt)</p>
                  <pre tabIndex={0} aria-label="Registry record excerpt">
                    <code>
                      {`id: stripe-2026-11-17-charge-source
type: removed_param
affects:
  module: stripe
  symbol: Charge.create
  param: source
  replacement_param: payment_method
effective: "2026-12-01"
recipe: rename_keyword
review: {status: reviewed, by: owner, date: "2026-11-17"}`}
                    </code>
                  </pre>
                </div>
              </li>

              <li className="step">
                <div className="step__text">
                  <p className="step__n">Step 3</p>
                  <h3>Prove it, or put it back.</h3>
                  <p>
                    After the edit it re-scans and, if the repository has a <code>tests/</code> folder, runs pytest. A
                    failed check restores every file it touched. A repo without tests can still succeed, but earns less
                    confidence.
                  </p>
                </div>
                <div className="plate art">
                  <table className="score">
                    <caption className="art__label">How confidence is scored</caption>
                    <tbody>
                      <tr>
                        <th scope="row">Re-scan finds no remaining call sites</th>
                        <td>+0.5</td>
                      </tr>
                      <tr>
                        <th scope="row">Edit applied without errors</th>
                        <td>+0.2</td>
                      </tr>
                      <tr>
                        <th scope="row">Repository tests pass</th>
                        <td>+0.3</td>
                      </tr>
                      <tr>
                        <th scope="row">No tests/ folder, instead of the line above</th>
                        <td>+0.1</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </li>

              <li className="step">
                <div className="step__text">
                  <p className="step__n">Step 4</p>
                  <h3>You decide.</h3>
                  <p>
                    The result is a status, a confidence score and a list of calls it refused to touch. Driftless never
                    merges. <code>--dry-run</code> shows what would change without writing anything. Opening a draft pull
                    request is not built yet.
                  </p>
                </div>
                <div className="plate art">
                  <table className="score score--status">
                    <caption className="art__label">Possible results</caption>
                    <tbody>
                      <tr>
                        <th scope="row">success</th>
                        <td>Confidence 0.8 or more, and no call skipped.</td>
                      </tr>
                      <tr>
                        <th scope="row">draft</th>
                        <td>Confidence below 0.8, or a call was skipped as ambiguous. Look before using.</td>
                      </tr>
                      <tr>
                        <th scope="row">failed</th>
                        <td>A check failed or a file couldn’t be edited. Everything is reverted.</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </li>
            </ol>
          </div>
        </section>

        {/* ───────── Guarantees ───────── */}
        <section id="limits" className="section section--sunk" aria-labelledby="limits-title">
          <div className="container">
            <header className="section__head">
              <h2 id="limits-title">What it won’t do.</h2>
              <p>
                An unattended tool that edits source has to be predictable before it is clever. Each limit below is
                enforced in code you can read.
              </p>
            </header>
            <ul className="limits">
              {GUARANTEES.map((g) => (
                <li key={g.title} className="limit">
                  <h3>{g.title}</h3>
                  <p>{g.body}</p>
                  <a href={repoFile(g.file)} target="_blank" rel="noopener noreferrer">
                    {g.file}
                    <span className="visually-hidden"> (opens in a new tab)</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* ───────── Status ───────── */}
        <section id="status" className="section" aria-labelledby="status-title">
          <div className="container">
            <header className="section__head">
              <h2 id="status-title">Early, and specific about it.</h2>
              <p>What works today, and what doesn’t exist yet.</p>
            </header>
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
          </div>
        </section>

        {/* ───────── Run it ───────── */}
        <section id="run" className="section section--sunk" aria-labelledby="run-title">
          <div className="container run">
            <div className="run__copy">
              <h2 id="run-title">Run it on a repository.</h2>
              <p>
                Install from source. Run the commands from the repository root so the CLI finds <code>registry/</code>.
                Start with <code>--dry-run</code> and read the result before letting it write.
              </p>
              <Link className="run__link" href="/dashboard">
                Or look at scan and fix records in the dashboard
              </Link>
            </div>
            <div className="plate art run__plate">
              <div className="run__bar">
                <span>shell</span>
                <CopyButton text={RUN_COMMANDS} label="Copy commands" />
              </div>
              <pre tabIndex={0} aria-label="Install and run commands">
                <code>{RUN_COMMANDS}</code>
              </pre>
            </div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="container">
          <div className="footer__row">
            <a className="brand" href="#top" aria-label="Driftless, back to top">
              <Logo />
              Driftless
            </a>
            <nav className="footer__links" aria-label="Footer">
              <a href="#process">How it works</a>
              <a href="#limits">Guarantees</a>
              <a href="#status">Status</a>
              <Link href="/dashboard">Dashboard</Link>
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
