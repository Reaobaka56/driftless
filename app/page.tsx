export default function Home() {
  return (
    <main
      style={{
        minHeight: '100vh',
        background: '#09090b',
        color: '#fafafa',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 24px',
        fontFamily: 'Arial, sans-serif',
      }}
    >
      <section style={{ width: '100%', maxWidth: 760 }}>
        <p style={{ color: '#a1a1aa', fontSize: 13, letterSpacing: '0.18em', textTransform: 'uppercase' }}>
          Raptor Labs / Developer Infrastructure
        </p>
        <h1 style={{ fontSize: 'clamp(48px, 9vw, 88px)', lineHeight: 0.98, letterSpacing: '-0.07em', margin: '28px 0 20px' }}>
          Driftless<span style={{ color: '#8b5cf6' }}>.</span>
        </h1>
        <p style={{ maxWidth: 590, color: '#a1a1aa', fontSize: 19, lineHeight: 1.7 }}>
          Detect broken API integrations before they become production incidents.
          Driftless scans repositories, identifies affected call sites, and prepares
          actionable findings for engineering teams.
        </p>
        <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginTop: 36 }}>
          <a
            href="/dashboard"
            style={{ background: '#8b5cf6', color: '#fff', padding: '13px 19px', borderRadius: 8, textDecoration: 'none', fontWeight: 600 }}
          >
            Open dashboard
          </a>
          <a
            href="https://github.com/Reaobaka56/driftless"
            style={{ border: '1px solid #3f3f46', color: '#e4e4e7', padding: '13px 19px', borderRadius: 8, textDecoration: 'none' }}
          >
            View source
          </a>
        </div>
        <p style={{ color: '#71717a', fontSize: 13, marginTop: 64 }}>
          Scan-first workflow · Human-reviewed changes · No automatic merges
        </p>
      </section>
    </main>
  );
}
