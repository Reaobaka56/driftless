// Reads {root, files} on stdin, writes {issues, parseErrors, scanned, skipped} on stdout.
// Only parses text. Never imports or executes scanned code.
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';

const require = createRequire(import.meta.url);
function emit(obj) { process.stdout.write(JSON.stringify(obj)); }

let ts;
try { ts = require(process.env.DRIFTLESS_TYPESCRIPT_PATH || 'typescript'); }
catch { emit({ error: 'typescript_not_found' }); process.exit(3); }

const SK = ts.SyntaxKind;
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const issues = [], parseErrors = [], skipped = [];
const seen = new Set();

const SECRET_NAME = /(secret|passw(or)?d|api[_-]?key|auth[_-]?token|access[_-]?token|private[_-]?key)/i;
const PLACEHOLDER = /^(x+|\*+|changeme|example|placeholder|your[-_ ]|<.*>|\$\{.*\})/i;
const TOKEN_PATTERNS = [
  [/AKIA[0-9A-Z]{16}/, 'AWS access key id'],
  [/gh[pousr]_[A-Za-z0-9]{36,}/, 'GitHub token'],
  [/sk_live_[0-9a-zA-Z]{24,}/, 'Stripe live secret key'],
  [/xox[baprs]-[0-9A-Za-z-]{10,}/, 'Slack token'],
  [/-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----/, 'private key block'],
];

const isStr = (n) => n && (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n));
const isDynamic = (n) => n && !isStr(n) && !ts.isNumericLiteral(n);
const isConcat = (n) => ts.isTemplateExpression(n) ||
  (ts.isBinaryExpression(n) && n.operatorToken.kind === SK.PlusToken && (isDynamic(n.left) || isDynamic(n.right)));
const calleeName = (c) => ts.isIdentifier(c) ? c.text : ts.isPropertyAccessExpression(c) ? c.name.text : null;

function scanFile(rel) {
  const abs = path.join(input.root, rel);
  let text;
  try { text = fs.readFileSync(abs, 'utf8'); }
  catch (e) { skipped.push({ file: rel, reason: `read failed: ${e.code || e.message}` }); return false; }
  const ext = path.extname(rel);
  const kind = { '.ts': ts.ScriptKind.TS, '.tsx': ts.ScriptKind.TSX, '.js': ts.ScriptKind.JS, '.jsx': ts.ScriptKind.JSX }[ext];
  const sf = ts.createSourceFile(rel, text, ts.ScriptTarget.Latest, true, kind);

  const diags = sf.parseDiagnostics || [];
  if (diags.length) {   // a recovered AST is not trustworthy evidence: report, don't analyse
    for (const d of diags.slice(0, 5)) {
      parseErrors.push({ file: rel, line: sf.getLineAndCharacterOfPosition(d.start || 0).line + 1,
                         message: ts.flattenDiagnosticMessageText(d.messageText, '\n') });
    }
    return false;
  }

  const lines = text.split('\n');
  const lineOf = (pos) => sf.getLineAndCharacterOfPosition(pos).line + 1;
  const redact = (s) => (s.length <= 4 ? '***' : s.slice(0, 3) + '***');
  const add = (rule, severity, node, description, remediation, confidence, secret) => {
    const start = lineOf(node.getStart(sf)), end = lineOf(node.getEnd());
    let evidence = (lines[start - 1] || '').trim();
    if (secret) evidence = evidence.split(secret).join(redact(secret));
    evidence = evidence.slice(0, 200) || node.getText(sf).slice(0, 200);
    const key = `${rule}|${start}|${end}`;
    if (seen.has(key + rel)) return;
    seen.add(key + rel);
    issues.push({ rule_id: rule, severity, file: rel, start_line: start, end_line: end,
                  description, evidence, remediation, confidence });
  };

  // pass 1: child_process bindings
  const execNs = new Set(), execFns = new Set();
  const isCP = (s) => /^(node:)?child_process$/.test(s);
  (function collect(n) {
    if (ts.isImportDeclaration(n) && ts.isStringLiteral(n.moduleSpecifier) && isCP(n.moduleSpecifier.text) && n.importClause) {
      if (n.importClause.name) execNs.add(n.importClause.name.text);
      const nb = n.importClause.namedBindings;
      if (nb && ts.isNamespaceImport(nb)) execNs.add(nb.name.text);
      if (nb && ts.isNamedImports(nb)) for (const e of nb.elements)
        if (['exec', 'execSync'].includes((e.propertyName || e.name).text)) execFns.add(e.name.text);
    }
    if (ts.isVariableDeclaration(n) && n.initializer && ts.isCallExpression(n.initializer) &&
        ts.isIdentifier(n.initializer.expression) && n.initializer.expression.text === 'require' &&
        isStr(n.initializer.arguments[0]) && isCP(n.initializer.arguments[0].text)) {
      if (ts.isIdentifier(n.name)) execNs.add(n.name.text);
      if (ts.isObjectBindingPattern(n.name)) for (const e of n.name.elements)
        if (['exec', 'execSync'].includes((e.propertyName || e.name).text)) execFns.add(e.name.text);
    }
    ts.forEachChild(n, collect);
  })(sf);

  const seenComments = new Set();
  const isTs = ext === '.ts' || ext === '.tsx';

  function visit(n) {
    // comments: @ts-ignore / @ts-nocheck without an explanation
    if (isTs) for (const r of ts.getLeadingCommentRanges(text, n.pos) || []) {
      if (seenComments.has(r.pos)) continue;
      seenComments.add(r.pos);
      const m = /@ts-(ignore|nocheck)\b(.*)/.exec(text.slice(r.pos, r.end));
      if (m && (m[1] === 'nocheck' || m[2].replace(/[*/\s:-]/g, '').length < 3)) {
        const fake = { getStart: () => r.pos, getEnd: () => r.end, getText: () => text.slice(r.pos, r.end) };
        add('ts-suppression', 'low', fake, `@ts-${m[1]} silences the type checker without an explanation.`,
            'Fix the type error, or use @ts-expect-error with a reason.', 0.9);
      }
    }

    if (ts.isCallExpression(n) || ts.isNewExpression(n)) {
      const name = calleeName(n.expression), args = n.arguments || [];
      if (ts.isCallExpression(n) && ts.isIdentifier(n.expression) && name === 'eval' && args.length && isDynamic(args[0]))
        add('ts-eval', 'high', n, 'eval() called with a non-literal argument allows arbitrary code execution.',
            'Remove eval; parse data with JSON.parse or use an explicit dispatch table.', 0.85);
      if (name === 'Function' && args.some(isDynamic))
        add('ts-eval', 'high', n, 'Function constructor called with a non-literal argument compiles arbitrary code.',
            'Avoid dynamic code generation.', 0.8);
      const isExec = ts.isCallExpression(n) && args.length &&
        ((ts.isIdentifier(n.expression) && execFns.has(n.expression.text)) ||
         (ts.isPropertyAccessExpression(n.expression) && ts.isIdentifier(n.expression.expression) &&
          execNs.has(n.expression.expression.text) && ['exec', 'execSync'].includes(n.expression.name.text)));
      if (isExec && isDynamic(args[0]))
        add('ts-command-injection', 'high', n,
            isConcat(args[0]) ? 'Shell command built by string interpolation/concatenation.'
                              : 'Shell command passed from a non-literal value.',
            'Use execFile/spawn with an argument array and no shell; validate inputs.',
            isConcat(args[0]) ? 0.8 : 0.5);
      if (name === 'createHash' && isStr(args[0]) && /^(md5|sha1)$/i.test(args[0].text))
        add('ts-weak-hash', 'medium', n, `createHash('${args[0].text}') is a broken hash for security purposes.`,
            'Use SHA-256 or better (or a password hash such as scrypt/argon2 for passwords). Ignore if used only as a non-security checksum.', 0.5);
      if (name === 'insertAdjacentHTML' && args[1] && isDynamic(args[1]))
        add('ts-xss-html-injection', 'medium', n, 'insertAdjacentHTML with a non-literal value can inject HTML/script.',
            'Use textContent or sanitize the HTML first.', 0.6);
      if (ts.isPropertyAccessExpression(n.expression) && ts.isIdentifier(n.expression.expression) &&
          n.expression.expression.text === 'document' && name === 'write' && args.length && isDynamic(args[0]))
        add('ts-xss-html-injection', 'medium', n, 'document.write with a non-literal value can inject HTML/script.',
            'Use DOM APIs with textContent.', 0.6);
      if (ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression) && name === 'forEach' && args[0] &&
          (ts.isArrowFunction(args[0]) || ts.isFunctionExpression(args[0])) &&
          (args[0].modifiers || []).some((m) => m.kind === SK.AsyncKeyword))
        add('ts-async-foreach', 'medium', n, 'forEach does not await an async callback; rejections go unhandled and work is not awaited.',
            'Use for...of with await, or Promise.all(items.map(...)).', 0.75);
      if (ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression) && name === 'catch' && args[0] &&
          (ts.isArrowFunction(args[0]) || ts.isFunctionExpression(args[0])) && ts.isBlock(args[0].body) &&
          args[0].body.statements.length === 0 && !/\S/.test(text.slice(args[0].body.getStart(sf) + 1, args[0].body.end - 1)))
        add('ts-empty-catch', 'medium', n, 'Promise rejection is swallowed by an empty .catch handler.',
            'Log or handle the error, or document why it is ignored.', 0.8);
    }

    if (ts.isCatchClause(n) && n.block.statements.length === 0 &&
        !/\S/.test(text.slice(n.block.getStart(sf) + 1, n.block.end - 1)))
      add('ts-empty-catch', 'medium', n, 'Exception is swallowed by an empty catch block.',
          'Handle or log the error, or add a comment explaining why it is safe to ignore.', 0.9);

    if (ts.isBinaryExpression(n) && [SK.EqualsToken, SK.PlusEqualsToken].includes(n.operatorToken.kind)) {
      const l = n.left;
      if (ts.isPropertyAccessExpression(l) && ['innerHTML', 'outerHTML'].includes(l.name.text) && isDynamic(n.right))
        add('ts-xss-html-injection', 'medium', n, `Assigning a non-literal value to ${l.name.text} can inject HTML/script.`,
            'Use textContent, or sanitize with a vetted library before assigning.', isConcat(n.right) ? 0.7 : 0.5);
      if (n.operatorToken.kind === SK.EqualsToken && l.getText(sf) === 'process.env.NODE_TLS_REJECT_UNAUTHORIZED' &&
          isStr(n.right) && n.right.text === '0')
        add('ts-tls-verification-disabled', 'high', n, 'TLS certificate verification is disabled process-wide.',
            'Remove this; trust the correct CA instead.', 0.9);
      checkSecret(n, ts.isIdentifier(l) ? l.text : ts.isPropertyAccessExpression(l) ? l.name.text : null, n.right);
    }
    if (ts.isPropertyAssignment(n)) {
      const nm = ts.isIdentifier(n.name) || ts.isStringLiteral(n.name) ? n.name.text : null;
      if (nm === 'rejectUnauthorized' && n.initializer.kind === SK.FalseKeyword)
        add('ts-tls-verification-disabled', 'high', n, 'TLS certificate verification is disabled (rejectUnauthorized: false).',
            'Remove it, or pin the expected CA/certificate.', 0.9);
      checkSecret(n, nm, n.initializer);
    }
    if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name)) checkSecret(n, n.name.text, n.initializer);
    if (ts.isJsxAttribute(n) && n.name.getText(sf) === 'dangerouslySetInnerHTML')
      add('ts-xss-html-injection', 'medium', n, 'dangerouslySetInnerHTML bypasses React escaping.',
          'Ensure the value is sanitized (e.g. DOMPurify) or render as text.', 0.5);
    if (isStr(n)) for (const [re, label] of TOKEN_PATTERNS) {
      const m = re.exec(n.text);
      if (m) add('ts-hardcoded-secret', 'high', n, `String literal looks like a ${label}.`,
                 'Revoke the credential, remove it from source and load it from the environment or a secret manager.', 0.9, m[0]);
    }
    ts.forEachChild(n, visit);
  }

  function checkSecret(node, name, init) {
    if (!name || !SECRET_NAME.test(name) || !isStr(init)) return;
    const v = init.text;
    if (v.length < 8 || /\s/.test(v) || PLACEHOLDER.test(v) || v.includes('process.env')) return;
    if (!(/\d/.test(v) && /[A-Za-z]/.test(v))) return;   // plain words are labels, not credentials
    add('ts-hardcoded-secret', 'high', node, `Credential-like value assigned to "${name}" is hardcoded.`,
        'Load secrets from the environment or a secret manager; rotate this value.', 0.6, v);
  }

  visit(sf);
  return true;
}

let scanned = 0;
for (const rel of input.files) if (scanFile(rel)) scanned++;
emit({ issues, parseErrors, skipped, scanned, tsVersion: ts.version });
