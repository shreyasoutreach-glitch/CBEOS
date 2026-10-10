"""HTML rendering. Deliberately template-engine-free (stdlib strings) to keep
the whole app dependency-light, matching v1.0's design choice. Every value
that could contain user input is passed through util.esc(). Every
state-changing form carries the session CSRF token.
"""
import json

from . import db as dbm
from . import engine
from . import agents
from . import supplier_ops
from . import util
from .db import FIELD_LABELS

CSS = '''
:root{color-scheme:light;--bg:#f5f5f7;--panel:#fff;--panel2:#fafafc;--line:#e5e5ea;--text:#1d1d1f;--muted:#6e6e73;--mint:#1677ff;--amber:#9a6700;--red:#c62828;--blue:#2563eb;--shadow:0 8px 30px rgba(0,0,0,.045)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
a{color:#06c;text-underline-offset:3px}
.shell{display:grid;grid-template-columns:248px minmax(0,1fr);min-height:100vh}
.side{border-right:1px solid var(--line);padding:26px 16px;background:rgba(255,255,255,.82);backdrop-filter:blur(18px)}
.logo{font-weight:750;font-size:16px;letter-spacing:-.55px;padding:4px 12px 28px;line-height:1.2}.logo span{display:block;color:var(--muted);font-weight:500;font-size:11px;letter-spacing:.15px;margin-top:5px}
.nav a{display:flex;align-items:center;color:#424245;text-decoration:none;padding:10px 12px;border-radius:10px;margin:3px 0;font-size:13px;transition:background .16s,color .16s}
.nav a:hover,.nav a.active{background:#eaf2ff;color:#0758c9;font-weight:650}
.navgroup{color:#86868b;font-size:10px;text-transform:uppercase;letter-spacing:1px;padding:14px 12px 4px}
.sidefoot{position:fixed;bottom:16px;width:210px;color:#86868b;font-size:10.5px;line-height:1.7}
.main{padding:38px clamp(20px,4vw,64px);max-width:1600px;width:100%;margin:0 auto}
.top{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;flex-wrap:wrap}
.eyebrow{text-transform:uppercase;letter-spacing:1.35px;color:#1677ff;font-size:10px;font-weight:750}
.title{font-size:clamp(28px,3vw,42px);line-height:1.08;margin:8px 0 12px;letter-spacing:-1.65px;font-weight:750}
.sub{color:var(--muted);max-width:780px;font-size:14px;line-height:1.65}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:22px 0}
.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.grid5{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}
.two{display:grid;grid-template-columns:1.5fr 1fr;gap:16px}
.card{background:var(--panel);border:1px solid rgba(0,0,0,.055);border-radius:18px;padding:21px;box-shadow:var(--shadow)}
.kpi{font-size:clamp(25px,2.5vw,34px);font-weight:750;letter-spacing:-1px;margin-top:8px}
.label{color:#86868b;font-size:10px;text-transform:uppercase;letter-spacing:.85px;font-weight:700}
.bar{height:6px;background:#e9e9eb;border-radius:99px;overflow:hidden}.fill{height:100%;background:#1677ff;border-radius:99px}
table{width:100%;border-collapse:collapse}
th{font-size:10px;color:#86868b;text-transform:uppercase;letter-spacing:.65px;text-align:left;padding:12px 9px;border-bottom:1px solid var(--line)}
td{padding:13px 9px;border-bottom:1px solid #f0f0f2;vertical-align:top;font-size:13px}
.pill{display:inline-flex;padding:4px 9px;border-radius:99px;background:#f0f0f2;color:#48484a;font-size:10.5px;font-weight:700;white-space:nowrap}
.pill.good{background:#e8f7ee;color:#17663a}.pill.warn{background:#fff4d6;color:#825600}.pill.bad{background:#fdeaea;color:#a51f1f}.pill.info{background:#eaf2ff;color:#0758c9}
.btn{display:inline-flex;align-items:center;justify-content:center;background:#1677ff;color:#fff;text-decoration:none;border:0;border-radius:999px;padding:10px 16px;font-weight:650;cursor:pointer;font-size:12.5px;box-shadow:0 2px 5px #1677ff20;transition:transform .15s,background .15s}
.btn:hover{background:#0866e8;transform:translateY(-1px)}
.btn.secondary{background:#f0f0f2;color:#1d1d1f;box-shadow:none}.btn.danger{background:#fdeaea;color:#a51f1f}.btn.small{padding:6px 11px;font-size:11px}
.actions{display:flex;gap:8px;flex-wrap:wrap}
.formgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.formgrid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.field{margin-bottom:12px}.field label{display:block;color:#6e6e73;font-size:11px;font-weight:650;margin-bottom:5px}
.field input,.field select,.field textarea{width:100%;margin-top:3px;background:#fff;color:#1d1d1f;border:1px solid #d2d2d7;border-radius:10px;padding:11px 12px;font:inherit;outline:none;transition:border-color .15s,box-shadow .15s}
.field input:focus,.field select:focus,.field textarea:focus{border-color:#1677ff;box-shadow:0 0 0 3px #1677ff20}
.field textarea{min-height:100px}
.notice,.dangerbox,.successbox,.warnbox{padding:13px 15px;border-radius:12px;margin:12px 0;line-height:1.6}
.notice{background:#f1f6ff;border:1px solid #d9e7ff;color:#25466e}.dangerbox{background:#fff0f0;border:1px solid #ffd6d6;color:#8f1d1d}
.successbox{background:#edf9f1;border:1px solid #d3efdc;color:#175c34}.warnbox{background:#fff8e7;border:1px solid #f3e2b2;color:#765300}
.section{margin-top:18px}.small{font-size:11.5px}.muted{color:var(--muted)}
.source{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10.5px;color:#555;background:#f5f5f7;padding:8px;border-radius:8px;white-space:pre-wrap}
.login{min-height:100vh;display:grid;place-items:center;padding:24px}
.login .card{width:min(440px,100%);padding:30px}
.footer{margin-top:34px;color:#86868b;font-size:10.5px;border-top:1px solid var(--line);padding-top:16px;line-height:1.6}
.trace{display:flex;flex-direction:column;gap:5px}.trace .node{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 14px}.trace .arrow{text-align:center;color:#8e8e93;font-size:16px;margin:-2px 0}
.checklist{list-style:none;padding:0;margin:0}.checklist li{padding:9px 0;border-bottom:1px solid #f0f0f2;font-size:12.5px;display:flex;gap:9px;align-items:flex-start}
.tick{width:16px;flex:0 0 16px;font-weight:900}.tick.yes{color:#16834a}.tick.no{color:#c62828}
.tabs{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap}.tabs a{padding:8px 12px;border-radius:999px;background:#f0f0f2;color:#48484a;text-decoration:none;font-size:12px}.tabs a.active{background:#1677ff;color:#fff;font-weight:700}
.kv{display:grid;grid-template-columns:170px 1fr;gap:7px 12px;font-size:12.5px}.kv div:nth-child(odd){color:#6e6e73}
.journey{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:20px 0}.journey a{display:block;color:var(--text);text-decoration:none}.journey .step{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#1677ff;font-weight:750}.journey h3{font-size:15px;margin:9px 0 6px;letter-spacing:-.3px}.journey p{font-size:12px;color:var(--muted);margin:0;line-height:1.6}
.sandbox-banner{border:1px solid #f0dca4;background:#fff8e7;color:#6e4d00;padding:14px 16px;border-radius:14px;margin:18px 0;line-height:1.6}
.outcome{border:1px solid #dbe7fb;background:linear-gradient(135deg,#f5f9ff,#fff)}
.login-layout{width:min(1120px,100%);display:grid;grid-template-columns:minmax(0,1.15fr) minmax(340px,.85fr);gap:26px;align-items:stretch}
.hero-panel{border-radius:26px;padding:clamp(28px,5vw,56px);background:radial-gradient(circle at 85% 15%,#d8e8ff 0,transparent 36%),linear-gradient(145deg,#fff 0%,#f3f7ff 100%);border:1px solid #e2eaf7;box-shadow:0 20px 60px #233e6810;overflow:hidden}
.hero-panel .title{font-size:clamp(36px,5vw,58px);letter-spacing:-2.4px;max-width:600px;margin-top:15px}
.hero-panel .sub{font-size:16px;max-width:580px}
.hero-art{margin:28px 0 24px;background:#fff;border:1px solid #e2eaf7;border-radius:20px;padding:18px;box-shadow:0 10px 32px #173f7310}
.flow-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;align-items:stretch}
.flow-node{background:#f7f9fc;border:1px solid #e4e9f0;border-radius:12px;padding:11px 8px;text-align:center;min-width:0}
.flow-node b{display:block;font-size:11px;letter-spacing:-.1px}.flow-node span{display:block;font-size:9.5px;color:#6e6e73;margin-top:4px;line-height:1.4}
.flow-icon{width:28px;height:28px;display:grid;place-items:center;margin:0 auto 7px;border-radius:9px;background:#eaf2ff;color:#0758c9;font-weight:800;font-size:13px}
.hero-proof{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:18px}
.proof{padding:13px;border-top:1px solid #dce5f1}.proof strong{display:block;font-size:12px}.proof span{display:block;color:#6e6e73;font-size:10.5px;line-height:1.5;margin-top:4px}
.login-brand{font-size:12px;font-weight:750;letter-spacing:.1px;color:#1d1d1f}.login-note{font-size:11px;color:#6e6e73;line-height:1.6;margin-top:18px}
@media(max-width:1080px){.journey{grid-template-columns:repeat(2,minmax(0,1fr))}.shell{grid-template-columns:210px minmax(0,1fr)}.grid5{grid-template-columns:repeat(3,minmax(0,1fr))}.main{padding:28px 24px}}
@media(max-width:820px){.login-layout{grid-template-columns:1fr}.hero-panel{padding:28px}.login-layout .login-card{max-width:560px;width:100%;margin:0 auto}.shell{grid-template-columns:1fr}.side{position:static;padding:12px 16px;border-right:0;border-bottom:1px solid var(--line)}.logo{padding:4px 8px 10px}.sidefoot{display:none}.nav{display:flex;overflow:auto;gap:4px}.nav a{white-space:nowrap}.main{padding:24px 18px}}
@media(max-width:620px){.journey,.grid,.grid3,.grid5,.two,.formgrid,.formgrid3{grid-template-columns:1fr}.flow-row{grid-template-columns:repeat(2,minmax(0,1fr))}.hero-proof{grid-template-columns:1fr}.title{font-size:30px}.card{padding:17px}.login{padding:14px}.hero-panel .title{font-size:38px}.login-layout{gap:14px}}
'''


NAV = [
    ('overview', '/', 'Overview'), ('cases', '/cases', 'Cases'), ('agents', '/agents', 'Agent terminal'),
    ('suppliers', '/suppliers', 'Suppliers'), ('installations', '/installations', 'Installations'),
    ('exceptions', '/exceptions', 'Exceptions'), ('verification', '/verification', 'Verification'),
    ('audit', '/audit', 'Audit'), ('sources', '/sources', 'Regulatory sources'),
    ('settings', '/settings', 'Settings'),
]


def layout(actor, title, content, active='overview'):
    if not actor:
        return '<!doctype html><meta http-equiv="refresh" content="0;url=/login">'
    nav = ''.join(f'<a class="{"active" if k == active else ""}" href="{u}">{n}</a>' for k, u, n in NAV)
    nav = ''.join(f'<a class="{"active" if k == active else ""}" href="{u}">{n}</a>' for k, u, n in NAV)
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{util.esc(title)} · CBAM Evidence OS</title><style>{CSS}</style></head><body><div class="shell">
<aside class="side"><div class="logo">CBAM <span>Control Tower</span></div><nav class="nav">{nav}</nav>
<div class="sidefoot">Evidence graph · reconciliation · exception queue · verification readiness<br><br>
{util.esc(actor["email"])} · {util.esc(actor["role"])}<br><a href="/logout">Sign out</a></div></aside>
<main class="main">{content}<div class="footer">CBAM Evidence OS · Control Tower build · scenario calculations
are not a declaration, legal opinion, or verified submission.</div></main></div></body></html>'''


def login_page(error=''):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>CBEOS · Evidence operations, made clear</title><meta name="description" content="Organize CBAM evidence, surface missing information, and prepare a traceable human-review workflow.">
<style>{CSS}</style></head><body><div class="login">
<div class="login-layout">
<section class="hero-panel">
<div class="login-brand">CBEOS <span style="color:#1677ff">/</span> CBAM Evidence OS</div>
<div class="eyebrow" style="margin-top:34px">Evidence operations workspace</div>
<h1 class="title">Less chasing.<br>Clearer evidence.</h1>
<p class="sub">A focused workspace for organizing supplier evidence, finding gaps, and preparing a traceable review trail for CBAM teams.</p>
<div class="hero-art" aria-label="Evidence workflow illustration">
<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:14px">
<div><div class="label">One guided workflow</div><div style="font-size:14px;font-weight:750;margin-top:4px">From documents to review queue</div></div>
<span class="pill info">Human-led</span>
</div>
<div class="flow-row">
<div class="flow-node"><div class="flow-icon">01</div><b>Collect</b><span>Import case & supplier files</span></div>
<div class="flow-node"><div class="flow-icon">02</div><b>Connect</b><span>Link facts to source evidence</span></div>
<div class="flow-node"><div class="flow-icon">03</div><b>Resolve</b><span>Review gaps and conflicts</span></div>
<div class="flow-node"><div class="flow-icon">04</div><b>Review</b><span>Check readiness and audit trail</span></div>
</div>
<svg viewBox="0 0 560 92" role="img" aria-label="Evidence and exception records converge into a human review queue" style="display:block;width:100%;height:auto;margin-top:12px">
<defs><linearGradient id="cbeosFlow" x1="0" x2="1"><stop offset="0" stop-color="#8ab9ff"/><stop offset="1" stop-color="#1677ff"/></linearGradient></defs>
<path d="M70 8 V27 Q70 37 82 37 H270 Q280 37 280 49 V61 M210 8 V23 Q210 37 220 37 M350 8 V23 Q350 37 340 37 M490 8 V27 Q490 37 478 37 H290" fill="none" stroke="url(#cbeosFlow)" stroke-width="2.5" stroke-linecap="round"/>
<circle cx="280" cy="61" r="5" fill="#1677ff"/><path d="M280 66 V76" stroke="#1677ff" stroke-width="2.5" stroke-linecap="round"/>
<rect x="193" y="76" width="174" height="15" rx="7.5" fill="#eaf2ff"/><text x="280" y="86.5" text-anchor="middle" font-size="9.5" font-family="-apple-system,BlinkMacSystemFont,Arial" fill="#0758c9" font-weight="700">HUMAN REVIEW · NOT AUTO-APPROVAL</text>
</svg>
</div>
<div class="hero-proof">
<div class="proof"><strong>Traceable by design</strong><span>Candidate facts retain document links and source context where extraction supports it.</span></div>
<div class="proof"><strong>Exceptions first</strong><span>Focus the team on missing evidence, conflicts, and next actions.</span></div>
<div class="proof"><strong>Humans stay in control</strong><span>Agents triage. They do not certify compliance or submit declarations.</span></div>
</div>
<div class="notice" style="margin-top:24px"><b>Sandbox boundary.</b> This build is for synthetic-data evaluation. Regulatory reconciliation is incomplete; do not use it for live filing, liability decisions, or confidential customer documents.</div>
</section>
<section class="login">
<div class="card login-card">
<div class="eyebrow">Welcome back</div><h2 style="font-size:28px;letter-spacing:-1px;margin:8px 0 4px">Sign in to CBEOS</h2>
<p class="sub" style="font-size:13px;margin-bottom:24px">Open your workspace and continue reviewing the evidence queue.</p>
{f'<div class="dangerbox">{util.esc(error)}</div>' if error else ''}
<form method="post" action="/login">
<div class="field"><label for="email">Work email</label><input id="email" name="email" type="email" autocomplete="username" placeholder="you@company.com" required></div>
<div class="field"><label for="password">Password</label><input id="password" name="password" type="password" autocomplete="current-password" placeholder="Enter your password" required></div>
<button class="btn" type="submit" style="width:100%;padding:12px">Sign in <span aria-hidden="true" style="margin-left:8px">→</span></button>
</form>
<p class="login-note">Access is configured by the workspace administrator. If you do not have credentials, ask your administrator to provision an account.</p>
<div style="border-top:1px solid #e5e5ea;margin-top:22px;padding-top:17px"><div class="label">What happens after sign-in?</div><p class="muted small" style="line-height:1.7;margin-bottom:0">Start a case → add supplier and installation records → upload synthetic evidence → review exceptions → run the coordinated agent triage → inspect the audit and readiness results.</p></div>
</div>
</section>
</div></div></body></html>'''


def pill_for_status(status):
    good = {'complete', 'verified', 'RESOLVED', 'ACCEPTED_WITH_RISK', 'READY', 'active', 'VALIDATED'}
    bad = {'missing', 'rejected', 'OPEN', 'BLOCKED', 'NOT_READY', 'OVERDUE'}
    cls = 'good' if status in good else ('bad' if status in bad else 'warn')
    return f'<span class="pill {cls}">{util.esc(status)}</span>'


# ---------------------------------------------------------------------------
# Dashboard (portfolio-wide control tower home)
# ---------------------------------------------------------------------------

def dashboard(c, actor):
    tid = actor['tenant_id']
    cases = c.execute('SELECT * FROM cases WHERE tenant_id=? ORDER BY updated DESC', (tid,)).fetchall()
    for case in cases:
        supplier_ops.escalate_overdue(c, tid, case['id'])
    count = lambda q, args=(tid,): c.execute(q, args).fetchone()['n']
    total_lines = count('SELECT COUNT(*) n FROM import_lines WHERE tenant_id=?')
    blocked_lines = count("SELECT COUNT(*) n FROM import_lines WHERE tenant_id=? AND status='blocked'")
    ready_lines = count("SELECT COUNT(*) n FROM import_lines WHERE tenant_id=? AND status IN ('ready','calculated','approved')")
    open_exceptions = count("SELECT COUNT(*) n FROM exceptions WHERE tenant_id=? AND status NOT IN ('RESOLVED','ACCEPTED_WITH_RISK','WAIVED')")
    high_exceptions = count("SELECT COUNT(*) n FROM exceptions WHERE tenant_id=? AND status NOT IN ('RESOLVED','ACCEPTED_WITH_RISK','WAIVED') AND severity='high'")
    overdue_requests = count("SELECT COUNT(*) n FROM supplier_requests WHERE tenant_id=? AND status='OVERDUE'")
    suppliers_n = count('SELECT COUNT(*) n FROM suppliers WHERE tenant_id=?')
    installations_n = count('SELECT COUNT(*) n FROM installations WHERE tenant_id=?')
    docs_n = count('SELECT COUNT(*) n FROM documents WHERE tenant_id=?')
    calc_rows = c.execute("SELECT result_json FROM calculation_runs WHERE tenant_id=? AND run_type='import_line' AND id IN (SELECT MAX(id) FROM calculation_runs WHERE tenant_id=? GROUP BY import_line_id)", (tid, tid)).fetchall()
    exposure = sum(util.num(json.loads(r['result_json']).get('indicative_certificate_equivalent') or 0) * util.num(json.loads(r['result_json']).get('certificate_price_eur_per_tco2e') or 0) for r in calc_rows)
    rs = engine.latest_rule_set(c)
    latest_price = engine.latest_certificate_price(c, rs['id']) if rs else None
    price = latest_price['price_eur'] if latest_price else '—'
    body = f"""<div class="top"><div><div class="eyebrow">Control tower</div><div class="title">Evidence → exception → financial consequence</div>
<div class="sub">CBAM Evidence OS controls provenance, reconciliation, verifier readiness, and the commercial cost of uncertainty.</div></div><div class="actions"><a class="btn" href="/case/new">+ New case</a></div></div>
<div class="sandbox-banner"><b>Sandbox mode · human-controlled</b> &nbsp; Exposure is indicative scenario output, not a legal liability or filing figure. Unapproved regulatory values must not be used for customer decisions. No filing is submitted from this workspace.</div>
<div class="journey">
<a class="card" href="/cases"><div class="step">01 · Scope</div><h3>Open the case workspace ↗</h3><p>See imports, evidence coverage, readiness and what is blocking progress.</p></a>
<a class="card" href="/suppliers"><div class="step">02 · Recover evidence</div><h3>Chase supplier gaps ↗</h3><p>Review supplier requests, installation records and supporting documents.</p></a>
<a class="card" href="/exceptions"><div class="step">03 · Resolve risk</div><h3>Clear exceptions ↗</h3><p>Prioritize conflicts and missing evidence instead of chasing every row manually.</p></a>
<a class="card" href="/verification"><div class="step">04 · Prove readiness</div><h3>Prepare the review ↗</h3><p>Inspect readiness and preserve a traceable hand-off for human review.</p></a>
</div>
<div class="card outcome"><div class="eyebrow">Client outcome view</div><h2 style="margin-top:6px">What needs action now?</h2><div class="grid3">
<div><div class="label">Evidence workflow blocked</div><div class="kpi" style="color:var(--red)">{blocked_lines}</div><div class="muted small">import lines need attention</div></div>
<div><div class="label">High-severity exceptions</div><div class="kpi" style="color:{'var(--red)' if high_exceptions else 'var(--mint)'}">{high_exceptions}</div><div class="muted small">open and prioritized</div></div>
<div><div class="label">Supplier follow-up overdue</div><div class="kpi" style="color:{'var(--amber)' if overdue_requests else 'var(--mint)'}">{overdue_requests}</div><div class="muted small">requests requiring follow-up</div></div>
</div><p class="muted small">These are live workflow counts for this tenant. They measure operational status, not regulatory compliance or financial savings.</p></div>
<div class="grid5"><div class="card"><div class="label">Import lines</div><div class="kpi">{total_lines}</div></div>
<div class="card"><div class="label">Blocked lines</div><div class="kpi" style="color:var(--red)">{blocked_lines}</div></div>
<div class="card"><div class="label">Ready / calculated</div><div class="kpi" style="color:var(--mint)">{ready_lines}</div></div>
<div class="card"><div class="label">Open exceptions</div><div class="kpi" style="color:{'var(--red)' if high_exceptions else 'var(--amber)'}">{open_exceptions}</div></div>
<div class="card"><div class="label">Overdue supplier requests</div><div class="kpi" style="color:var(--amber)">{overdue_requests}</div></div></div>
<div class="grid3"><div class="card"><div class="label">Suppliers</div><div class="kpi">{suppliers_n}</div></div><div class="card"><div class="label">Installations</div><div class="kpi">{installations_n}</div></div><div class="card"><div class="label">Source documents</div><div class="kpi">{docs_n}</div></div></div>
<div class="card section"><h2>Commercial exposure control</h2><p class="muted small">Latest stored CBAM certificate price: <b>€{util.esc(price)}/tCO2e</b>. Exposure is scenario-only.</p><div class="kpi">{util.money(exposure)}</div></div>"""
    updates = c.execute("SELECT * FROM regulatory_updates WHERE status='ACTIVE' ORDER BY announced_date DESC LIMIT 4").fetchall()
    body += '<div class="card section"><h2>Regulatory changes that affect the product</h2>'
    for u in updates:
        body += f'<div class="warnbox small"><b>{util.esc(u["title"])}</b><br>{util.esc(u["impact"])} <span class="muted">Product: {util.esc(u["product_implication"])}</span></div>'
    body += '</div><div class="card section"><h2>Case portfolio</h2><table><tr><th>Case</th><th>Period</th><th>Readiness</th><th>Blockers</th><th></th></tr>'
    for item in cases:
        score, readiness = engine.readiness(c, tid, item['id'])
        css = 'good' if readiness['ready'] else ('warn' if score >= 60 else 'bad')
        blockers = ' · '.join(readiness['blockers'][:3]) or 'No current blockers'
        body += f'<tr><td><b>{util.esc(item["case_name"])}</b><div class="muted small">{util.esc(item["company"])} · {util.esc(item["sector"] or "sector not set")}</div></td><td>{util.esc(item["period"])}</td><td><span class="pill {css}">{score}%</span></td><td class="small">{util.esc(blockers)}</td><td><a class="btn secondary" href="/case/{item["id"]}">Open</a></td></tr>'
    body += '</table></div>'
    top = c.execute("SELECT * FROM exceptions WHERE tenant_id=? AND status NOT IN ('RESOLVED','ACCEPTED_WITH_RISK','WAIVED') ORDER BY CASE severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,id DESC LIMIT 8", (tid,)).fetchall()
    body += '<div class="card section"><h2>Highest-priority exceptions</h2><table><tr><th>Title</th><th>Severity</th><th>Status</th><th>Owner</th><th></th></tr>'
    for item in top:
        body += f'<tr><td><b>{util.esc(item["title"])}</b><div class="muted small">{util.esc((item["detail"] or "")[:110])}</div></td><td>{pill_for_status(item["severity"])}</td><td>{pill_for_status(item["status"])}</td><td>{util.esc(item["owner"])}</td><td><a class="btn secondary small" href="/case/{item["case_id"]}">Open case</a></td></tr>'
    body += '</table></div>'
    return layout(actor, 'Overview', body, 'overview')


def agents_home(c, actor):
    tid = actor['tenant_id']
    cases = c.execute('SELECT * FROM cases WHERE tenant_id=? ORDER BY updated DESC', (tid,)).fetchall()
    body = '''<div class="top"><div><div class="eyebrow">CBEOS orchestration layer</div><div class="title">Agent terminal</div>
<div class="sub">One coordinated run. Specialist agents exchange structured hand-offs and return a prioritized work queue. No agent can verify evidence or approve a declaration.</div></div></div>
<div class="notice"><b>Data boundary:</b> the workflow is read-only with respect to evidence, exceptions and calculations. Optional model commentary requires explicit credentials and a user-launched run. Model prose is advisory, never authoritative.</div>
<div class="card section"><h2>Select a case</h2><table><tr><th>Case</th><th>Period</th><th>Sector</th><th>Latest agent run</th><th></th></tr>'''
    for case in cases:
        latest = c.execute('SELECT id,status,finished_at FROM agent_runs WHERE tenant_id=? AND case_id=? ORDER BY id DESC LIMIT 1', (tid, case['id'])).fetchone()
        label = (f"#{latest['id']} · {latest['status']} · {latest['finished_at'] or 'in progress'}" if latest else 'Not run yet')
        body += f'<tr><td><b>{util.esc(case["case_name"])}</b><div class="muted small">{util.esc(case["company"])}</div></td><td>{util.esc(case["period"])}</td><td>{util.esc(case["sector"] or "not set")}</td><td>{util.esc(label)}</td><td><a class="btn secondary" href="/case/{case["id"]}/agents">Open terminal</a></td></tr>'
    if not cases:
        body += '<tr><td colspan="5">No cases yet. Create a case first, then return here to start the workflow.</td></tr>'
    body += '</table></div><div class="card section"><h2>Specialist roster</h2><div class="grid3">'
    roster = [('Intake & Scope','Builds the operational baseline without promoting extracted facts.'),('Evidence Quality','Finds missing requirements, empty extractions and review work.'),('Supplier Operations','Surfaces open and overdue requests without sending messages.'),('Reconciliation','Ranks open conflicts and exceptions without auto-closing them.'),('Regulatory Research','Retrieves source pages with page number and SHA-256.'),('Calculation Integrity','Flags non-official defaults and scenario-only outputs.'),('Commercial Exposure','Separates recorded impacts from indicative estimates.'),('Verifier Readiness','Combines blockers into a transparent readiness verdict.'),('Declaration Package QA','Checks package hash and snapshot freshness.')]
    for name, desc in roster:
        body += f'<div class="card"><h3>{util.esc(name)} Agent</h3><p class="muted small">{util.esc(desc)}</p></div>'
    body += '</div></div>'
    return layout(actor, 'Agent terminal', body, 'agents')


def agent_case_terminal(c, actor, case, csrf, run_id=None):
    tid, cid = actor['tenant_id'], case['id']
    run, messages = agents.load_run(c, tid, cid, run_id)
    model_on = agents.llm_configured()
    mode = 'Configured LLM commentary + deterministic policy agents' if model_on else 'Deterministic policy agents + local source retrieval'
    boundary = ('A configured model may receive case metadata, counts, exception summaries/details, prior hand-offs and selected regulatory excerpts. Raw uploaded documents are not sent.' if model_on else 'No model API credentials are configured, so no case data is sent to an external model.')
    body = f"""<div class="top"><div><div class="eyebrow">Agent terminal · case #{cid}</div><div class="title">{util.esc(case['case_name'])}</div>
<div class="sub">{util.esc(case['company'])} · {util.esc(case['period'])} · {util.esc(case['sector'] or 'sector not set')}</div></div>
<div class="actions"><a class="btn secondary" href="/case/{cid}">Back to case</a><a class="btn secondary" href="/agents">All cases</a></div></div>
<div class="notice"><b>Operating mode:</b> {util.esc(mode)}. {util.esc(boundary)} Calculations, approvals and evidence verification remain human-controlled.</div>
<div class="card section"><h2>Launch coordinated workflow</h2><p class="muted">The orchestrator sends structured hand-offs through Intake → Evidence Quality → Reconciliation → Regulatory Research → Calculation Integrity → Verifier Readiness.</p>
<form method="post" action="/case/{cid}/agents/run"><input type="hidden" name="csrf" value="{util.esc(csrf)}"><button class="btn">Run workflow now</button></form></div>"""
    if run:
        summary = run.get('summary', {})
        readiness = summary.get('readiness', {}) if isinstance(summary, dict) else {}
        verdict = readiness.get('verdict', run['status'])
        cls = 'good' if verdict == 'READY_FOR_HUMAN_REVIEW' else 'bad'
        body += f"""<div class="grid"><div class="card"><div class="label">Latest run</div><div class="kpi">#{run['id']}</div><span class="pill">{util.esc(run['status'])}</span></div>
<div class="card"><div class="label">Readiness verdict</div><div class="kpi">{util.esc(readiness.get('readiness_score','—'))}/100</div><span class="pill {cls}">{util.esc(verdict)}</span></div>
<div class="card"><div class="label">Source documents indexed</div><div class="kpi">{util.esc(summary.get('source_corpus',{}).get('documents','—'))}</div></div>
<div class="card"><div class="label">Model commentary</div><div class="kpi">{util.esc(summary.get('llm_commentary_status','not available'))}</div><div class="muted small">Advisory only</div></div></div>"""
        blockers = readiness.get('blockers', []) + readiness.get('calculation_blockers', [])
        if blockers:
            body += '<div class="dangerbox"><b>Current blockers</b><ul>' + ''.join(f'<li>{util.esc(x)}</li>' for x in blockers) + '</ul></div>'
        body += '<div class="card section"><h2>Prioritized next actions</h2><table><tr><th>Priority</th><th>Action</th></tr>'
        for item in summary.get('next_actions', []):
            body += f'<tr><td>{pill_for_status(item.get("priority","P2"))}</td><td>{util.esc(item.get("action",""))}</td></tr>'
        body += '</table></div>'
        regulatory = summary.get('agents', {}).get('regulatory', {})
        body += '<div class="card section"><h2>Regulatory source trail</h2><p class="muted small">Page-level retrieval is not legal validation.</p><table><tr><th>Source / page</th><th>Relevance</th><th>Excerpt</th></tr>'
        for item in regulatory.get('sources', []):
            body += f'<tr><td>{util.esc(item.get("filename"))}<div class="muted small">Page {util.esc(item.get("page"))}</div><div class="source">SHA-256 {util.esc(item.get("sha256"))}</div></td><td>{util.esc(item.get("score"))}</td><td>{util.esc(item.get("excerpt"))}</td></tr>'
        body += '</table></div>'
        ok, at = agents.verify_message_chain(c, tid, cid, run['id'])
        integrity = 'successbox' if ok else 'dangerbox'
        note = 'Conversation hash chain verified.' if ok else f'Conversation integrity failed at sequence {at}.'
        body += f'<div class="card section"><h2>Agent-to-agent conversation</h2><div class="{integrity}">{util.esc(note)}</div><div class="trace">'
        for msg in messages:
            body += f'<div class="node"><div class="eyebrow">{util.esc(msg.get("sequence_no"))}. {util.esc(msg.get("from_agent"))} → {util.esc(msg.get("to_agent"))} · {util.esc(msg.get("message_type"))}</div><p>{util.esc(msg.get("body"))}</p><details><summary class="muted small">Inspect structured hand-off payload</summary><div class="source">{util.esc(msg.get("payload_json","{}"))}</div></details></div>'
        body += '</div></div>'
    else:
        body += '<div class="card section"><h2>What the run produces</h2><ul class="checklist"><li>Evidence gaps and open-exception priorities</li><li>Regulatory references with source file, page and hash</li><li>Calculation integrity warnings and readiness verdict</li><li>No automatic verification, exception closure or filing</li></ul></div>'
    return layout(actor, 'Agent terminal', body, 'agents')


def case_list(c, actor):
    tid = actor['tenant_id']
    cases = c.execute('SELECT * FROM cases WHERE tenant_id=? ORDER BY updated DESC', (tid,)).fetchall()
    body = '<div class="top"><div><div class="eyebrow">Cases</div><div class="title">Operational workspaces</div>' \
           '<div class="sub">A case is the bounded unit of evidence, reconciliation, supplier follow-up and review for one importer/period.</div></div>' \
           '<div class="actions"><a class="btn" href="/case/new">+ New case</a></div></div>' \
           '<div class="card section"><table><tr><th>Case</th><th>Period</th><th>Sector</th><th>Status</th><th>Readiness</th><th></th></tr>'
    for x in cases:
        sc, rd = engine.readiness(c, tid, x['id'])
        body += (f'<tr><td><b>{util.esc(x["case_name"])}</b><div class="muted small">{util.esc(x["company"])}</div></td>'
                 f'<td>{util.esc(x["period"])}</td><td>{util.esc(x["sector"])}</td><td>{pill_for_status(x["status"])}</td>'
                 f'<td>{sc}%</td><td><a class="btn secondary small" href="/case/{x["id"]}">Open</a></td></tr>')
    body += '</table></div>'
    return layout(actor, 'Cases', body, 'cases')


def case_form(actor, csrf):
    body = f'''<div class="eyebrow">Create operational case</div><div class="title">Start with the import, not the spreadsheet</div>
<div class="sub">A case is the bounded unit of evidence, reconciliation, supplier follow-up and review for one importer/reporting period.</div>
<div class="card section"><form method="post" action="/case/create"><div class="formgrid">
<div class="field"><label>Company / importer</label><input name="company" required></div>
<div class="field"><label>Case / workspace reference</label><input name="case_name" required placeholder="e.g. 2026 Annual CBAM Case"></div>
<div class="field"><label>Reporting period</label><input name="period" value="2026" required></div>
<div class="field"><label>Sector</label><select name="sector">
<option value="iron_steel">Iron &amp; steel</option><option value="aluminium">Aluminium</option>
<option value="fertilisers">Fertilisers</option><option value="cement">Cement</option>
<option value="hydrogen">Hydrogen</option><option value="electricity">Electricity</option>
<option value="other">Other / mixed</option></select></div></div>
<div class="field"><label>Internal notes</label><textarea name="notes" placeholder="Context, owner, unusual facts, review scope..."></textarea></div>
<input type="hidden" name="csrf" value="{util.esc(csrf)}"><button class="btn">Create case</button></form></div>'''
    return layout(actor, 'New case', body, 'cases')


def case_detail(c, actor, case, csrf):
    tid, cid = actor['tenant_id'], case['id']
    sc, rd = engine.readiness(c, tid, cid)
    cls = 'good' if rd['ready'] else ('warn' if sc >= 60 else 'bad')
    imports = c.execute('SELECT * FROM imports WHERE tenant_id=? AND case_id=? ORDER BY id DESC', (tid, cid)).fetchall()
    lines = c.execute('SELECT * FROM import_lines WHERE tenant_id=? AND case_id=? ORDER BY id DESC', (tid, cid)).fetchall()
    docs = c.execute('SELECT * FROM documents WHERE tenant_id=? AND case_id=? ORDER BY id DESC', (tid, cid)).fetchall()
    facts = c.execute('SELECT f.*,d.filename FROM facts f JOIN documents d ON d.id=f.document_id '
                        'WHERE f.tenant_id=? AND f.case_id=? ORDER BY f.id DESC LIMIT 60', (tid, cid)).fetchall()
    ev = c.execute('SELECT * FROM evidence WHERE tenant_id=? AND case_id=? ORDER BY id', (tid, cid)).fetchall()
    req = c.execute('SELECT * FROM evidence_requirements WHERE tenant_id=? AND case_id=? ORDER BY scope_type,id', (tid, cid)).fetchall()
    exc = c.execute("SELECT * FROM exceptions WHERE tenant_id=? AND case_id=? AND status NOT IN ('RESOLVED','ACCEPTED_WITH_RISK','WAIVED') "
                      "ORDER BY CASE severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,id", (tid, cid)).fetchall()
    suppliers = c.execute('SELECT * FROM suppliers WHERE tenant_id=? ORDER BY name', (tid,)).fetchall()
    installations = c.execute('SELECT * FROM installations WHERE tenant_id=? ORDER BY name', (tid,)).fetchall()

    body = f'''<div class="top"><div><div class="eyebrow">Case · {util.esc(case["period"])}</div><div class="title">{util.esc(case["case_name"])}</div>
<div class="sub">{util.esc(case["company"])} · {util.esc(case["sector"] or "sector not set")} · status {util.esc(case["status"])}</div></div>
<div class="actions"><a class="btn" href="/case/{cid}/agents">Run agent workflow</a><a class="btn secondary" href="/case/{cid}/pack">Evidence pack (JSON)</a>
<a class="btn secondary" href="/case/{cid}/declaration">Declaration package</a>
{'<form method="post" action="/approve" style="display:inline"><input type="hidden" name="case_id" value="' + str(cid) + '"><input type="hidden" name="csrf" value="' + util.esc(csrf) + '"><button class="btn" ' + ('' if rd['ready'] else 'disabled') + '>Approve case</button></form>'}
</div></div>
<div class="grid"><div class="card"><div class="label">Readiness</div><div class="kpi">{sc}%</div>
<span class="pill {cls}">{'READY FOR HUMAN APPROVAL' if rd['ready'] else 'BLOCKED'}</span></div>
<div class="card"><div class="label">Import lines</div><div class="kpi">{rd["import_lines_total"]}</div>
<div class="muted small">{rd["import_lines_blocked"]} blocked</div></div>
<div class="card"><div class="label">Documents</div><div class="kpi">{rd["docs"]}</div></div>
<div class="card"><div class="label">Open exceptions</div><div class="kpi">{rd["open_issues"]}</div></div></div>'''
    if rd['blockers']:
        body += '<div class="dangerbox"><b>Approval blockers</b><ul>' + ''.join(f'<li>{util.esc(x)}</li>' for x in rd['blockers']) + '</ul></div>'
    else:
        body += '<div class="successbox"><b>Operational blockers cleared.</b> The evidence workflow is complete enough for human consequential review. This is not a legal compliance certification.</div>'

    body += '<div class="two section"><div><div class="card"><h2>1 · Imports &amp; import lines</h2>'
    body += f'''<form method="post" action="/case/{cid}/import/create"><input type="hidden" name="csrf" value="{util.esc(csrf)}">
<div class="formgrid3"><div class="field"><label>Import reference</label><input name="reference" placeholder="e.g. MRN or shipment ref" required></div>
<div class="field"><label>Mode</label><select name="mode"><option value="sea">Sea</option><option value="road">Road</option><option value="rail">Rail</option><option value="air">Air</option></select></div>
<div class="field"><label>Arrival date</label><input name="arrival_date" type="date"></div></div>
<button class="btn secondary small">+ Add import</button></form>'''
    body += '<table class="section"><tr><th>Reference</th><th>Mode</th><th>Arrival</th><th>Lines</th></tr>'
    for im in imports:
        n = c.execute('SELECT COUNT(*) n FROM import_lines WHERE import_id=?', (im['id'],)).fetchone()['n']
        body += f'<tr><td><b>{util.esc(im["reference"])}</b></td><td>{util.esc(im["mode"])}</td><td>{util.esc(im["arrival_date"])}</td><td>{n}</td></tr>'
    body += '</table>'

    supplier_opts = ''.join(f'<option value="{s["id"]}">{util.esc(s["name"])}</option>' for s in suppliers)
    installation_opts = ''.join(f'<option value="{i["id"]}">{util.esc(i["name"])}</option>' for i in installations)
    import_opts = ''.join(f'<option value="{i["id"]}">{util.esc(i["reference"])}</option>' for i in imports)
    body += f'''<h3 class="section">Add import line</h3><form method="post" action="/line/create"><input type="hidden" name="case_id" value="{cid}">
<input type="hidden" name="csrf" value="{util.esc(csrf)}"><div class="formgrid3">
<div class="field"><label>Import</label><select name="import_id"><option value="">(unassigned)</option>{import_opts}</select></div>
<div class="field"><label>CN code</label><input name="cn_code" placeholder="e.g. 72081000" required></div>
<div class="field"><label>Quantity (t)</label><input name="quantity" placeholder="e.g. 24.500"></div>
<div class="field"><label>Origin country</label><input name="origin_country"></div>
<div class="field"><label>Supplier</label><select name="supplier_id"><option value="">(unassigned)</option>{supplier_opts}</select></div>
<div class="field"><label>Installation</label><select name="installation_id"><option value="">(unassigned)</option>{installation_opts}</select></div>
<div class="field"><label>Invoice ref</label><input name="invoice_ref"></div></div>
<button class="btn secondary small">+ Add import line</button></form>'''
    body += '<table class="section"><tr><th>Line</th><th>CN</th><th>Qty</th><th>Supplier</th><th>Installation</th><th>Status</th><th></th></tr>'
    for l in lines:
        sname = c.execute('SELECT name FROM suppliers WHERE id=?', (l['supplier_id'],)).fetchone()
        iname = c.execute('SELECT name FROM installations WHERE id=?', (l['installation_id'],)).fetchone()
        body += (f'<tr><td><b>#{l["id"]}</b> {util.esc(l["invoice_ref"])}</td><td>{util.esc(l["cn_code"])}</td>'
                 f'<td>{util.esc(l["quantity"])} {util.esc(l["quantity_unit"])}</td><td>{util.esc(sname["name"] if sname else "—")}</td>'
                 f'<td>{util.esc(iname["name"] if iname else "—")}</td><td>{pill_for_status(l["status"])}</td>'
                 f'<td><a class="btn secondary small" href="/line/{l["id"]}">Trace →</a></td></tr>')
    body += '</table></div></div>'

    body += '<div><div class="card"><h2>2 · Open exceptions</h2>'
    if not exc:
        body += '<div class="successbox">No open exceptions in this case.</div>'
    for e in exc:
        body += (f'<div class="dangerbox"><b>{util.esc(e["title"])}</b> {pill_for_status(e["severity"])} {pill_for_status(e["status"])}'
                 f'<div class="muted small" style="margin-top:5px">{util.esc(e["detail"])}</div>'
                 f'<div class="actions" style="margin-top:8px"><a class="btn secondary small" href="/exceptions#e{e["id"]}">Manage →</a></div></div>')
    body += '</div>'
    body += f'''<div class="card section"><h2>3 · Evidence requirements</h2><p class="muted small">Requirements are scope-aware (case / supplier / installation / import line), not a generic checklist.</p>
<table><tr><th>Requirement</th><th>Scope</th><th>Status</th></tr>'''
    for r in req[:40]:
        body += f'<tr><td><b>{util.esc(r["name"])}</b></td><td class="small">{util.esc(r["scope_type"])} #{r["scope_id"]}</td><td>{pill_for_status(r["status"])}</td></tr>'
    if len(req) > 40:
        body += f'<tr><td colspan="3" class="muted small">+ {len(req) - 40} more requirement rows (per supplier/installation/import line).</td></tr>'
    body += '</table></div></div></div>'

    body += f'''<div class="card section"><h2>4 · Intake &amp; provenance</h2>
<form method="post" action="/upload" enctype="multipart/form-data"><input type="hidden" name="case_id" value="{cid}">
<input type="hidden" name="csrf" value="{util.esc(csrf)}"><div class="formgrid3">
<div class="field"><label>Document type</label><select name="doc_type"><option>commercial_invoice</option><option>packing_list</option>
<option>bill_of_lading</option><option>classification</option><option>customs</option><option>emissions</option>
<option>supplier_declaration</option><option>methodology</option><option>verification</option><option>other</option></select></div>
<div class="field"><label>Applies to import line (optional)</label><select name="import_line_id"><option value="">(case-level)</option>
{"".join(f'<option value="{l["id"]}">#{l["id"]} {util.esc(l["cn_code"])}</option>' for l in lines)}</select></div>
<div class="field"><label>Applies to installation (optional)</label><select name="installation_id"><option value="">(none)</option>{installation_opts}</select></div>
</div><div class="field"><label>Source file (.pdf / .xlsx / .csv / .txt)</label><input type="file" name="file" required></div>
<button class="btn">Upload + extract candidates</button></form>'''
    body += '<table class="section"><tr><th>File</th><th>Type</th><th>Fingerprint</th><th>Status</th><th></th></tr>'
    for d in docs[:30]:
        body += (f'<tr><td><b>{util.esc(d["filename"])}</b><div class="muted small">{d["size_bytes"]:,} bytes</div></td>'
                 f'<td>{util.esc(d["doc_type"])}</td><td class="source">{util.esc(d["sha256"][:18])}…</td>'
                 f'<td><span class="pill good">{util.esc(d["status"])}</span></td>'
                 f'<td><a class="btn secondary small" href="/document/{d["id"]}/download">Download</a></td></tr>')
    body += '</table></div>'

    body += '<div class="card section"><h2>5 · Candidate facts → authoritative facts</h2>' \
            '<p class="muted small">Nothing extracted becomes authoritative automatically. Every value retains source document, locator and excerpt.</p>' \
            '<table><tr><th>Field</th><th>Value</th><th>Source</th><th>Status</th><th></th></tr>'
    for f in facts:
        pill = 'good' if f['status'] == 'verified' else ('bad' if f['status'] == 'rejected' else 'warn')
        actions = ''
        if f['status'] == 'candidate':
            actions = (f'<form method="post" action="/fact/verify" style="display:inline"><input type="hidden" name="id" value="{f["id"]}">'
                       f'<input type="hidden" name="csrf" value="{util.esc(csrf)}"><button class="btn small">Verify</button></form> '
                       f'<form method="post" action="/fact/reject" style="display:inline"><input type="hidden" name="id" value="{f["id"]}">'
                       f'<input type="hidden" name="csrf" value="{util.esc(csrf)}"><button class="btn danger small">Reject</button></form>')
        body += (f'<tr><td><b>{util.esc(FIELD_LABELS.get(f["field"], f["field"]))}</b><div class="muted small">{util.esc(f["unit"])}</div></td>'
                 f'<td>{util.esc(f["value"])}</td><td><div class="source">{util.esc(f["filename"])} · {util.esc(f["location"])}<br>{util.esc(f["source_excerpt"])}</div></td>'
                 f'<td><span class="pill {pill}">{util.esc(f["status"])}</span></td><td>{actions}</td></tr>')
    body += '</table></div>'

    body += f'''<div class="card section"><h2>6 · Evidence ledger</h2>
<form method="post" action="/evidence/add"><input type="hidden" name="case_id" value="{cid}"><input type="hidden" name="csrf" value="{util.esc(csrf)}">
<div class="formgrid3"><div class="field"><label>Name</label><input name="name" required placeholder="e.g. Supplier verified emissions statement"></div>
<div class="field"><label>Category</label><select name="category">{"".join(f'<option value="{cat}">{cat}</option>' for _, cat, _, _, _ in dbm.REQS)}</select></div>
<div class="field"><label>Scope</label><select name="scope_type"><option value="case">Case</option><option value="supplier">Supplier</option>
<option value="installation">Installation</option><option value="import_line">Import line</option></select></div></div>
<div class="field"><label>Scope id (supplier/installation/import-line id, blank for case)</label><input name="scope_id" placeholder="e.g. 3"></div>
<div class="field"><label>Source / reference</label><input name="source"></div><div class="field"><label>Note</label><textarea name="note"></textarea></div>
<button class="btn">Add evidence</button></form><table class="section"><tr><th>Evidence</th><th>Status</th><th>Scope</th><th>Source</th></tr>'''
    for e in ev:
        body += (f'<tr><td><b>{util.esc(e["name"])}</b><div class="muted small">{util.esc(e["category"])}</div></td>'
                 f'<td><span class="pill {"good" if e["status"] in ("complete", "verified") else "warn"}">{util.esc(e["status"])}</span></td>'
                 f'<td class="small">{util.esc(e["scope_type"])} #{e["scope_id"] or ""}</td><td>{util.esc(e["source"])}<div class="muted small">{util.esc(e["note"])}</div></td></tr>')
    body += '</table></div>'

    calc = c.execute('SELECT * FROM calculation_runs WHERE tenant_id=? AND case_id=? ORDER BY id DESC LIMIT 5', (tid, cid)).fetchall()
    body += f'''<div class="card section"><h2>7 · Case-level scenario workbench</h2>
<p class="muted small">Ad hoc "what if" exploration, not tied to a specific import line. For a real calculation backed by evidence, use the
Trace page for an individual import line.</p><form method="post" action="/calculate"><input type="hidden" name="case_id" value="{cid}">
<input type="hidden" name="csrf" value="{util.esc(csrf)}"><div class="formgrid3">
<div class="field"><label>Quantity (t)</label><input name="quantity" value="0"></div>
<div class="field"><label>Specific embedded emissions (tCO2e/t)</label><input name="specific_embedded_emissions" value="0"></div>
<div class="field"><label>Free allocation adjustment (tCO2e)</label><input name="free_allocation_adjustment" value="0"></div>
<div class="field"><label>Carbon price already paid (€)</label><input name="carbon_price_credit_eur" value="0"></div>
<div class="field"><label>Certificate price (€/tCO2e)</label><input name="certificate_price_eur" value="75.28"></div></div>
<button class="btn">Run scenario</button></form>'''
    if calc:
        r = json.loads(calc[0]['result_json'])
        body += (f'<div class="section successbox"><b>Latest run · {util.esc(calc[0]["created"])}</b><br>'
                 f'Gross embedded: <b>{util.esc(r.get("gross_embedded_emissions_tco2e"))} tCO2e</b><br>'
                 f'Net after free allocation input: <b>{util.esc(r.get("net_after_free_allocation_tco2e"))} tCO2e</b><br>'
                 f'Indicative certificate equivalent: <b>{util.esc(r.get("indicative_certificate_equivalent") if r.get("indicative_certificate_equivalent") is not None else "not computable")}</b>'
                 f'<div class="muted small">{util.esc(r.get("note", ""))}</div></div>')
    body += '</div>'
    return layout(actor, case['case_name'], body, 'cases')


# ---------------------------------------------------------------------------
# Import line detail = the visible evidence graph (§19)
# ---------------------------------------------------------------------------

def import_line_detail(c, actor, line, csrf):
    tid = actor['tenant_id']
    case = c.execute('SELECT * FROM cases WHERE id=? AND tenant_id=?', (line['case_id'], tid)).fetchone()
    supplier = c.execute('SELECT * FROM suppliers WHERE id=? AND tenant_id=?', (line['supplier_id'], tid)).fetchone() if line['supplier_id'] else None
    installation = c.execute('SELECT * FROM installations WHERE id=? AND tenant_id=?', (line['installation_id'], tid)).fetchone() if line['installation_id'] else None
    product = c.execute('SELECT * FROM product_catalog WHERE cn_code=? ORDER BY id DESC LIMIT 1', (line['cn_code'],)).fetchone()
    facts = c.execute('SELECT * FROM evidence_facts WHERE tenant_id=? AND import_line_id=? ORDER BY id DESC', (tid, line['id'])).fetchall()
    exceptions = c.execute("SELECT * FROM exceptions WHERE tenant_id=? AND case_id=? AND status NOT IN ('RESOLVED','ACCEPTED_WITH_RISK','WAIVED') ORDER BY id DESC", (tid, line['case_id'])).fetchall()
    risk_score, risk_reasons = engine.import_line_risk(c, tid, line['id'])
    body = f'''<div class="top"><div><div class="eyebrow">Import line #{line['id']} · evidence graph</div><div class="title">{util.esc(line['description'] or line['cn_code'])}</div><div class="sub">{util.esc(case['case_name'] if case else 'Case missing')} · {util.esc(case['period'] if case else '')} · CN {util.esc(line['cn_code'])}</div></div><div class="actions"><a class="btn secondary" href="/case/{line['case_id']}">Back to case</a></div></div>
<div class="grid"><div class="card"><div class="label">Control risk score</div><div class="kpi">{risk_score}/100</div><span class="pill {'good' if risk_score >= 80 else ('warn' if risk_score >= 55 else 'bad')}">{'LOW' if risk_score >= 80 else ('MEDIUM' if risk_score >= 55 else 'HIGH')} WORKFLOW RISK</span></div><div class="card"><div class="label">Quantity</div><div class="kpi">{util.esc(line['quantity'] or '—')} {util.esc(line['quantity_unit'])}</div></div><div class="card"><div class="label">Evidence facts</div><div class="kpi">{len(facts)}</div><div class="muted small">{sum(1 for f in facts if f['status']=='verified')} human-verified</div></div><div class="card"><div class="label">Open exceptions</div><div class="kpi">{len(exceptions)}</div></div></div>'''
    if risk_reasons:
        body += '<div class="warnbox"><b>Risk drivers</b><ul>' + ''.join(f'<li>{util.esc(x)}</li>' for x in risk_reasons) + '</ul></div>'
    body += '<div class="card section"><h2>Evidence lineage</h2><div class="trace">'
    body += f'<div class="node"><b>Import line</b> {util.esc(line["description"] or line["cn_code"])} · {util.esc(line["quantity"])} {util.esc(line["quantity_unit"])} · {util.esc(line["origin_country"])}</div><div class="arrow">↓</div>'
    body += f'<div class="node"><b>Product / CN</b> {util.esc(line["cn_code"])}' + (f' · {util.esc(product["description"])} ({util.esc(product["sector"])})' if product else ' · not catalogued yet') + '</div><div class="arrow">↓</div>'
    body += f'<div class="node"><b>Supplier</b> {util.esc(supplier["name"]) if supplier else "unassigned"}' + (f' · {util.esc(supplier["country"])}' if supplier else '') + '</div><div class="arrow">↓</div>'
    body += f'<div class="node"><b>Installation</b> {util.esc(installation["name"]) if installation else "unassigned"}' + (f' · {util.esc(installation["production_route"] or "route not documented")}' if installation else '') + '</div><div class="arrow">↓</div>'
    emissions = c.execute("SELECT * FROM emissions_records WHERE tenant_id=? AND import_line_id=? ORDER BY id DESC LIMIT 1", (tid, line['id'])).fetchone()
    if emissions:
        body += f'<div class="node"><b>Emissions record</b> {util.esc(emissions["specific_embedded_emissions"])} tCO2e/t · status {util.esc(emissions["status"])} · source {util.esc(emissions["source_type"])}</div><div class="arrow">↓</div>'
    else:
        body += '<div class="node bad"><b>Emissions record</b> Missing. Actual emissions or an approved legal default are required before calculation.</div><div class="arrow">↓</div>'
    body += '<div class="node"><b>Evidence facts</b> Candidate facts remain unverified until human review. Documents do not silently become verified data.</div></div></div>'
    body += '<div class="card section"><h2>Evidence facts · human review</h2><table><tr><th>Fact</th><th>Value</th><th>Status</th><th>Source</th></tr>'
    for fact in facts:
        body += f'<tr><td>{util.esc(fact["fact_key"])}</td><td>{util.esc(fact["fact_value"])}</td><td>{pill_for_status(fact["status"])}</td><td>{util.esc(fact["source_excerpt"] or "No excerpt")}</td></tr>'
    if not facts:
        body += '<tr><td colspan="4">No candidate facts extracted for this line.</td></tr>'
    body += '</table></div>'
    body += '<div class="card section"><h2>Current exceptions</h2><table><tr><th>Title</th><th>Severity</th><th>Status</th><th>Detail</th></tr>'
    for ex in exceptions:
        body += f'<tr><td>{util.esc(ex["title"])}</td><td>{pill_for_status(ex["severity"])}</td><td>{pill_for_status(ex["status"])}</td><td>{util.esc(ex["detail"])}</td></tr>'
    if not exceptions:
        body += '<tr><td colspan="4">No open case exceptions.</td></tr>'
    body += '</table></div>'
    return layout(actor, 'Import line', body, 'cases')


def suppliers_list(c, actor, csrf):
    tid = actor['tenant_id']
    suppliers = c.execute('SELECT * FROM suppliers WHERE tenant_id=? ORDER BY name', (tid,)).fetchall()
    cases = c.execute('SELECT id FROM cases WHERE tenant_id=?', (tid,)).fetchall()
    body = f'''<div class="top"><div><div class="eyebrow">Supplier operations</div><div class="title">Suppliers</div>
<div class="sub">This is the operationally painful layer in CBAM 2026: supplier data collection, not certificate purchasing. Every number here is computed, not narrated.</div></div></div>
<div class="card section"><form method="post" action="/supplier/create"><input type="hidden" name="csrf" value="{util.esc(csrf)}"><div class="formgrid3">
<div class="field"><label>Name</label><input name="name" required></div><div class="field"><label>Country</label><input name="country"></div>
<div class="field"><label>Contact email</label><input name="contact_email"></div></div><button class="btn secondary small">+ Add supplier</button></form></div>
<div class="card section"><table><tr><th>Supplier</th><th>Country</th><th>Import lines</th><th>Supported</th><th>Blocked</th><th>Evidence complete</th><th>Overdue requests</th><th></th></tr>'''
    for s in suppliers:
        agg = {'lines_total': 0, 'lines_supported': 0, 'lines_blocked': 0, 'evidence_complete_pct': 0, 'overdue_requests': 0}
        n_cases = 0
        for cs in cases:
            sc = supplier_ops.supplier_scorecard(c, tid, cs['id'], s['id'])
            if sc['lines_total']:
                n_cases += 1
            agg['lines_total'] += sc['lines_total']; agg['lines_supported'] += sc['lines_supported']
            agg['lines_blocked'] += sc['lines_blocked']; agg['evidence_complete_pct'] += sc['evidence_complete_pct']
            agg['overdue_requests'] += sc['overdue_requests']
        avg_ev = round(agg['evidence_complete_pct'] / n_cases) if n_cases else 100
        body += (f'<tr><td><b>{util.esc(s["name"])}</b></td><td>{util.esc(s["country"])}</td><td>{agg["lines_total"]}</td>'
                 f'<td>{agg["lines_supported"]}</td><td style="color:{"var(--red)" if agg["lines_blocked"] else "inherit"}">{agg["lines_blocked"]}</td>'
                 f'<td>{avg_ev}%</td><td style="color:{"var(--amber)" if agg["overdue_requests"] else "inherit"}">{agg["overdue_requests"]}</td>'
                 f'<td><a class="btn secondary small" href="/supplier/{s["id"]}">Manage</a></td></tr>')
    if not suppliers:
        body += '<tr><td colspan="8">No suppliers yet. Create one or add them through a case workflow.</td></tr>'
    body += '</table></div>'
    return layout(actor, 'Suppliers', body, 'suppliers')
def supplier_detail(c, actor, supplier, csrf):
    tid = actor['tenant_id']
    sid = supplier['id']
    installations = c.execute('SELECT * FROM installations WHERE tenant_id=? AND supplier_id=?', (tid, sid)).fetchall()
    lines = c.execute('SELECT * FROM import_lines WHERE tenant_id=? AND supplier_id=?', (tid, sid)).fetchall()
    requests = c.execute('SELECT * FROM supplier_requests WHERE tenant_id=? AND supplier_id=? ORDER BY id DESC', (tid, sid)).fetchall()
    cases = c.execute('SELECT DISTINCT c.* FROM cases c JOIN import_lines l ON l.case_id=c.id WHERE l.tenant_id=? AND l.supplier_id=?', (tid, sid)).fetchall()

    body = f'''<div class="top"><div><div class="eyebrow">Supplier</div><div class="title">{util.esc(supplier["name"])}</div>
<div class="sub">{util.esc(supplier["country"])} · {util.esc(supplier["contact_email"] or "no contact on file")}</div></div></div>'''

    scorecards = [(cs, supplier_ops.supplier_scorecard(c, tid, cs['id'], sid)) for cs in cases]
    for cs, sc in scorecards:
        body += (f'<div class="card section"><h2>{util.esc(cs["case_name"])}</h2>'
                 f'<p>Supplier <b>{util.esc(supplier["name"])}</b> has <b>{sc["lines_total"]}</b> affected import lines. '
                 f'<b>{sc["lines_supported"]}</b> are supported. <b>{sc["lines_blocked"]}</b> are blocked. '
                 f'Evidence requirements {sc["evidence_complete_pct"]}% complete. {sc["open_requests"]} open request(s), '
                 f'{sc["overdue_requests"]} overdue.</p>'
                 f'<form method="post" action="/supplier/{sid}/generate_requests"><input type="hidden" name="case_id" value="{cs["id"]}">'
                 f'<input type="hidden" name="csrf" value="{util.esc(csrf)}"><div class="field"><label>Deadline</label><input type="date" name="deadline"></div>'
                 f'<button class="btn secondary small">Generate missing-evidence requests</button></form></div>')

    body += '<div class="card section"><h2>Installations</h2>' \
            f'<form method="post" action="/installation/create"><input type="hidden" name="supplier_id" value="{sid}">' \
            f'<input type="hidden" name="csrf" value="{util.esc(csrf)}"><div class="formgrid3">' \
            '<div class="field"><label>Name</label><input name="name" required></div><div class="field"><label>Country</label><input name="country"></div>' \
            '<div class="field"><label>Production route</label><input name="production_route" placeholder="e.g. Basic oxygen furnace"></div></div>' \
            '<button class="btn secondary small">+ Add installation</button></form>' \
            '<table class="section"><tr><th>Installation</th><th>Country</th><th>Route</th><th></th></tr>'
    for i in installations:
        body += f'<tr><td><b>{util.esc(i["name"])}</b></td><td>{util.esc(i["country"])}</td><td>{util.esc(i["production_route"])}</td><td><a class="btn secondary small" href="/installation/{i["id"]}">Open</a></td></tr>'
    body += '</table></div>'

    body += '<div class="card section"><h2>Import lines from this supplier</h2><table><tr><th>Line</th><th>CN</th><th>Qty</th><th>Status</th><th></th></tr>'
    for l in lines:
        body += f'<tr><td>#{l["id"]}</td><td>{util.esc(l["cn_code"])}</td><td>{util.esc(l["quantity"])}</td><td>{pill_for_status(l["status"])}</td><td><a class="btn secondary small" href="/line/{l["id"]}">Trace →</a></td></tr>'
    body += '</table></div>'

    body += '<div class="card section"><h2>Evidence request history</h2><table><tr><th>Requirement</th><th>Status</th><th>Deadline</th><th>Escalation</th><th></th></tr>'
    for r in requests:
        actions = ''
        if r['status'] == 'DRAFT':
            actions = f'<form method="post" action="/supplier_request/{r["id"]}/send" style="display:inline"><input type="hidden" name="csrf" value="{util.esc(csrf)}"><button class="btn small">Send</button></form>'
        elif r['status'] in ('SENT', 'WAITING', 'OVERDUE'):
            actions = (f'<form method="post" action="/supplier_request/{r["id"]}/respond" style="display:inline"><input type="hidden" name="csrf" value="{util.esc(csrf)}">'
                       f'<input type="hidden" name="validated" value="0"><button class="btn secondary small">Mark responded</button></form> '
                       f'<form method="post" action="/supplier_request/{r["id"]}/respond" style="display:inline"><input type="hidden" name="csrf" value="{util.esc(csrf)}">'
                       f'<input type="hidden" name="validated" value="1"><button class="btn small">Mark validated</button></form>')
        body += (f'<tr><td><b>{util.esc(r["requirement_name"])}</b><div class="source small">{util.esc(r["draft"])[:180]}</div></td>'
                 f'<td>{pill_for_status(r["status"])}</td><td>{util.esc(r["deadline"])}</td><td>{r["escalation_level"]}</td><td>{actions}</td></tr>')
    if not requests:
        body += '<tr><td colspan="5" class="muted">No requests generated yet.</td></tr>'
    body += '</table></div>'
    return layout(actor, supplier['name'], body, 'suppliers')


# ---------------------------------------------------------------------------
# Installations
# ---------------------------------------------------------------------------

def installations_list(c, actor):
    tid = actor['tenant_id']
    rows = c.execute('SELECT i.*,s.name sname FROM installations i LEFT JOIN suppliers s ON s.id=i.supplier_id WHERE i.tenant_id=? ORDER BY i.name', (tid,)).fetchall()
    body = '<div class="top"><div><div class="eyebrow">Installations</div><div class="title">Producing installations</div>' \
           '<div class="sub">Verification readiness is computed per installation, not per shipment.</div></div></div>' \
           '<div class="card section"><table><tr><th>Installation</th><th>Supplier</th><th>Country</th><th>Route</th><th>Readiness</th><th></th></tr>'
    for i in rows:
        rd = engine.verification_readiness(c, tid, i['id'])
        body += (f'<tr><td><b>{util.esc(i["name"])}</b></td><td>{util.esc(i["sname"] or "—")}</td><td>{util.esc(i["country"])}</td>'
                 f'<td>{util.esc(i["production_route"] or "—")}</td><td>{pill_for_status(rd["status"])} {rd["score"]}%</td>'
                 f'<td><a class="btn secondary small" href="/installation/{i["id"]}">Open</a></td></tr>')
    if not rows:
        body += '<tr><td colspan="6" class="muted">No installations yet -- add one from a supplier page.</td></tr>'
    body += '</table></div>'
    return layout(actor, 'Installations', body, 'installations')


def installation_detail(c, actor, installation, csrf):
    tid = actor['tenant_id']
    iid = installation['id']
    supplier = c.execute('SELECT * FROM suppliers WHERE id=?', (installation['supplier_id'],)).fetchone() if installation['supplier_id'] else None
    lines = c.execute('SELECT * FROM import_lines WHERE tenant_id=? AND installation_id=?', (tid, iid)).fetchall()
    emissions = c.execute('SELECT * FROM emissions_data WHERE tenant_id=? AND installation_id=? ORDER BY id DESC', (tid, iid)).fetchall()
    methodologies = c.execute('SELECT * FROM methodologies').fetchall()
    readiness = engine.verification_readiness(c, tid, iid)

    body = f'''<div class="top"><div><div class="eyebrow">Installation</div><div class="title">{util.esc(installation["name"])}</div>
<div class="sub">{util.esc(installation["country"])} · supplier {util.esc(supplier["name"]) if supplier else "unassigned"} · route {util.esc(installation["production_route"] or "not documented")}</div></div></div>'''

    body += f'<div class="card section"><h2>Verification readiness</h2><div class="kpi">{readiness["score"]}%</div>{pill_for_status(readiness["status"])}<ul class="checklist section">'
    for label, ok, reason in readiness['checklist']:
        body += f'<li><span class="tick {"yes" if ok else "no"}">{"✓" if ok else "✗"}</span><div><b>{util.esc(label)}</b><div class="muted">{util.esc(reason)}</div></div></li>'
    flabel, fok, freason = readiness['future_item']
    body += f'<li><span class="tick {"yes" if fok else "no"}">{"✓" if fok else "○"}</span><div><b>{util.esc(flabel)}</b> <span class="pill info">not yet applicable</span><div class="muted">{util.esc(freason)}</div></div></li>'
    body += '</ul></div>'

    method_opts = ''.join(f'<option value="{m["id"]}">{util.esc(m["name"])}</option>' for m in methodologies)
    body += f'''<div class="card section"><h2>Emissions data</h2>
<form method="post" action="/installation/{iid}/emissions/add"><input type="hidden" name="csrf" value="{util.esc(csrf)}"><div class="formgrid3">
<div class="field"><label>Direct intensity (tCO2e/t)</label><input name="direct_intensity" required></div>
<div class="field"><label>Indirect intensity (tCO2e/t)</label><input name="indirect_intensity" value="0"></div>
<div class="field"><label>Methodology</label><select name="methodology_id">{method_opts}</select></div></div>
<div class="field"><label>Status</label><select name="status"><option value="candidate">Candidate — not ready to use</option><option value="validated">Validated — reviewed</option></select></div>
<button class="btn">Record emissions data</button></form>
<table class="section"><tr><th>Recorded</th><th>Direct</th><th>Indirect</th><th>Methodology</th><th>Status</th></tr>'''
    for e in emissions:
        m = c.execute('SELECT name FROM methodologies WHERE id=?', (e['methodology_id'],)).fetchone()
        body += f'<tr><td>{util.esc(e["created"])}</td><td>{util.esc(e["direct_intensity"])}</td><td>{util.esc(e["indirect_intensity"])}</td><td>{util.esc(m["name"] if m else "—")}</td><td>{pill_for_status(e["status"])}</td></tr>'
    body += '</table></div>'
    body += '<div class="card section"><h2>Import lines referencing this installation</h2><table><tr><th>Line</th><th>CN</th><th>Quantity</th><th>Status</th><th></th></tr>'
    for l in lines:
        body += f'<tr><td>#{l["id"]}</td><td>{util.esc(l["cn_code"])}</td><td>{util.esc(l["quantity"])}</td><td>{pill_for_status(l["status"])}</td><td><a class="btn secondary small" href="/line/{l["id"]}">Trace →</a></td></tr>'
    body += '</table></div>'
    return layout(actor, installation['name'], body, 'installations')


# ---------------------------------------------------------------------------
# Exceptions queue
# ---------------------------------------------------------------------------

def exceptions_queue(c, actor, csrf):
    tid = actor['tenant_id']
    rows = c.execute('SELECT e.*,ca.case_name FROM exceptions e JOIN cases ca ON ca.id=e.case_id WHERE e.tenant_id=? '
                       "ORDER BY CASE WHEN e.status IN ('RESOLVED','ACCEPTED_WITH_RISK','WAIVED') THEN 1 ELSE 0 END,"
                       "CASE e.severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, e.id DESC LIMIT 200", (tid,)).fetchall()
    open_n = sum(1 for r in rows if r['status'] not in ('RESOLVED', 'ACCEPTED_WITH_RISK', 'WAIVED'))
    body = f'''<div class="top"><div><div class="eyebrow">Exception queue</div><div class="title">The operational product</div>
<div class="sub">{open_n} open across the portfolio. Every discrepancy is actionable: owner, deadline, and a state machine, not a silent AI guess.</div></div></div>'''
    for e in rows:
        cls = 'dangerbox' if e['status'] not in ('RESOLVED', 'ACCEPTED_WITH_RISK', 'WAIVED') else 'card'
        body += f'<div class="{cls} section" id="e{e["id"]}"><b>{util.esc(e["title"])}</b> {pill_for_status(e["severity"])} {pill_for_status(e["status"])} ' \
                f'<span class="muted small">· case {util.esc(e["case_name"])} · category {util.esc(e["category"])}</span>' \
                f'<div class="muted small" style="margin-top:5px">{util.esc(e["detail"])}</div>'
        if e['recommended_action']:
            body += f'<div class="small" style="margin-top:5px"><b>Recommended:</b> {util.esc(e["recommended_action"])}</div>'
        if e['status'] not in ('RESOLVED', 'ACCEPTED_WITH_RISK', 'WAIVED'):
            body += f'''<form method="post" action="/exception/transition" style="margin-top:8px" class="formgrid3">
<input type="hidden" name="id" value="{e["id"]}"><input type="hidden" name="csrf" value="{util.esc(csrf)}">
<div class="field"><label>New status</label><select name="status">
<option value="UNDER_REVIEW">Under review</option><option value="WAITING_SUPPLIER">Waiting on supplier</option>
<option value="WAITING_INTERNAL">Waiting internally</option><option value="RESOLVED">Resolved</option>
<option value="ACCEPTED_WITH_RISK">Accept with risk</option><option value="BLOCKED">Blocked</option>
<option value="WAIVED">Waived</option></select></div>
<div class="field"><label>Owner</label><input name="owner" value="{util.esc(e["owner"])}"></div>
<div class="field"><label>Deadline</label><input type="date" name="deadline" value="{util.esc(e["deadline"])}"></div>
<div class="field" style="grid-column:1/-1"><label>Resolution note</label><textarea name="resolution"></textarea></div>
<button class="btn small">Update</button></form>'''
        body += '</div>'
    if not rows:
        body += '<div class="successbox">No exceptions recorded yet.</div>'
    return layout(actor, 'Exceptions', body, 'exceptions')


# ---------------------------------------------------------------------------
# Verification overview
# ---------------------------------------------------------------------------

def verification_overview(c, actor):
    tid = actor['tenant_id']
    rows = c.execute('SELECT i.*,s.name sname FROM installations i LEFT JOIN suppliers s ON s.id=i.supplier_id WHERE i.tenant_id=? ORDER BY i.name', (tid,)).fetchall()
    scored = [(i, engine.verification_readiness(c, tid, i['id'])) for i in rows]
    avg = round(sum(r['score'] for _, r in scored) / len(scored)) if scored else 0
    ready_n = sum(1 for _, r in scored if r['status'] == 'READY')
    body = f'''<div class="top"><div><div class="eyebrow">Verification readiness</div><div class="title">The trust layer</div>
<div class="sub">Installation-level readiness -- the bridge between your evidence and what a verifier will still need.</div></div></div>
<div class="grid3"><div class="card"><div class="label">Installations</div><div class="kpi">{len(rows)}</div></div>
<div class="card"><div class="label">Ready</div><div class="kpi" style="color:var(--mint)">{ready_n}</div></div>
<div class="card"><div class="label">Portfolio average</div><div class="kpi">{avg}%</div></div></div>
<div class="card section"><table><tr><th>Installation</th><th>Supplier</th><th>Readiness</th><th>Status</th><th></th></tr>'''
    for i, r in scored:
        body += (f'<tr><td><b>{util.esc(i["name"])}</b></td><td>{util.esc(i["sname"] or "—")}</td>'
                 f'<td>{r["score"]}%</td><td>{pill_for_status(r["status"])}</td>'
                 f'<td><a class="btn secondary small" href="/installation/{i["id"]}">Open</a></td></tr>')
    body += '</table></div>'
    return layout(actor, 'Verification', body, 'verification')


# ---------------------------------------------------------------------------
# Declaration package
# ---------------------------------------------------------------------------

def declaration_view(c, actor, case, csrf):
    tid, cid = actor['tenant_id'], case['id']
    packages = c.execute('SELECT * FROM declaration_packages WHERE tenant_id=? AND case_id=? ORDER BY id DESC', (tid, cid)).fetchall()
    sc, rd = engine.readiness(c, tid, cid)
    body = f'''<div class="top"><div><div class="eyebrow">Declaration package · {util.esc(case["case_name"])}</div>
<div class="title">Verifier / management handoff</div>
<div class="sub">A structured, hashed evidence manifest. This prepares declaration-ready data; it does not submit anything to the CBAM Registry
(that step requires the authorised declarant acting through the official channel).</div></div>
<div class="actions"><form method="post" action="/case/{cid}/declaration/generate"><input type="hidden" name="csrf" value="{util.esc(csrf)}">
<button class="btn" {"disabled" if not rd["ready"] else ""}>Generate package</button></form></div></div>'''
    if not rd['ready']:
        body += '<div class="warnbox">Generating is still allowed for review purposes, but the case has open blockers: ' + '; '.join(rd['blockers']) + '</div>'
    for p in packages:
        manifest = json.loads(p['manifest_json'])
        body += f'''<div class="card section"><h2>Package #{p["id"]} · {util.esc(p["generated_at"])}</h2>
<div class="kv"><div>SHA-256</div><div class="source">{util.esc(p["sha256"])}</div>
<div>Readiness at generation</div><div>{manifest["readiness"]["score"]}%</div>
<div>Import lines</div><div>{len(manifest.get("import_lines", []))}</div>
<div>Suppliers</div><div>{len(manifest.get("suppliers", []))}</div>
<div>Installations</div><div>{len(manifest.get("installations", []))}</div>
<div>Documents in manifest</div><div>{len(manifest.get("documents", []))}</div>
<div>Open exceptions at generation</div><div>{manifest["readiness"]["open_issues"]}</div></div>
<div class="muted small section">IMPLEMENTED: evidence manifest, provenance, hash. REQUIRES EXTERNAL INTEGRATION: authorised submission to the
CBAM Registry, and independent legal/verifier sign-off before any figure here is relied upon externally.</div></div>'''
    if not packages:
        body += '<div class="card section muted">No declaration package generated yet.</div>'
    return layout(actor, 'Declaration package', body, 'cases')


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def audit_view(c, actor):
    tid = actor['tenant_id']
    ok, break_id = engine.verify_audit_chain(c, tid)
    rows = c.execute('SELECT * FROM audit WHERE tenant_id=? ORDER BY id DESC LIMIT 250', (tid,)).fetchall()
    body = f'''<div class="top"><div><div class="eyebrow">Audit trail</div><div class="title">Append-only, hash-chained</div>
<div class="sub">Every consequential action is recorded with who/what/when and a hash of the previous entry.</div></div></div>
{"<div class=\"successbox\">Chain integrity verified: no breaks detected.</div>" if ok else f"<div class=\"dangerbox\">Chain integrity check FAILED at audit id {break_id}.</div>"}
<div class="card section"><table><tr><th>When</th><th>Action</th><th>Detail</th><th>Hash</th></tr>'''
    for r in rows:
        body += f'<tr><td class="small">{util.esc(r["created"])}</td><td><b>{util.esc(r["action"])}</b></td><td class="small">{util.esc(r["detail"])}</td><td class="source">{util.esc(r["hash"][:16])}…</td></tr>'
    body += '</table></div>'
    return layout(actor, 'Audit', body, 'audit')


# ---------------------------------------------------------------------------
# Regulatory sources
# ---------------------------------------------------------------------------

def sources_view(c, actor):
    rows = c.execute('SELECT s.*,r.code rcode,r.version FROM regulatory_sources s LEFT JOIN rule_sets r ON r.source_id=s.id ORDER BY s.id', ()).fetchall()
    updates = c.execute('SELECT * FROM regulatory_updates ORDER BY announced_date DESC', ()).fetchall()
    body = '<div class="top"><div><div class="eyebrow">Regulatory source governance</div><div class="title">Rule sources &amp; version control</div>' \
           '<div class="sub">Every consequential rule must point to a legal source, effective date and version. This registry distinguishes official, secondary-sourced and illustrative values.</div></div></div>'
    body += '<div class="card section"><h2>Source register</h2><table><tr><th>Code</th><th>Title</th><th>Effective</th><th>Version</th><th>Notes</th></tr>'
    for r in rows:
        body += f'<tr><td><b>{util.esc(r["code"])}</b></td><td><a href="{util.esc(r["url"])}" target="_blank" rel="noopener">{util.esc(r["title"])}</a></td><td>{util.esc(r["effective_date"])}</td><td>{util.esc(r["version"] or "—")}</td><td class="small">{util.esc(r["notes"])}</td></tr>'
    body += '</table></div><div class="card section"><h2>Regulatory change log</h2><table><tr><th>Announced</th><th>Change</th><th>Effective</th><th>Scope / impact</th><th>Product implication</th></tr>'
    for u in updates:
        body += f'<tr><td>{util.esc(u["announced_date"])}</td><td><b>{util.esc(u["title"])}</b></td><td>{util.esc(u["effective_date"])}</td><td class="small">{util.esc(u["affected_scope"])}<div class="muted">{util.esc(u["impact"])}</div></td><td class="small">{util.esc(u["product_implication"])}</td></tr>'
    body += '</table></div>'
    body += '<div class="card section"><h2>Default-value confidence and source status</h2><table><tr><th>CN prefix</th><th>Sector</th><th>Country</th><th>Route</th><th>Total</th><th>Confidence</th><th>Notes</th></tr>'
    vals = c.execute('SELECT * FROM default_values ORDER BY sector,cn_prefix,id', ()).fetchall()
    for v in vals:
        body += f'<tr><td>{util.esc(v["cn_prefix"] or "sector fallback")}</td><td>{util.esc(v["sector"])}</td><td>{util.esc(v["country"] or "all")}</td><td>{util.esc(v["production_route"] or "all")}</td><td>{util.esc(v["total_default"])}</td><td>{pill_for_status(v["confidence"])}</td><td class="small">{util.esc(v["markup_note"])}</td></tr>'
    body += '</table><div class="dangerbox">Illustrative defaults are not legal inputs. The corrected official default-value dataset has not yet been fully reconciled and promoted in this build.</div></div>'
    return layout(actor, 'Regulatory sources', body, 'sources')


# ---------------------------------------------------------------------------
# Settings (admin)
# ---------------------------------------------------------------------------

def settings_view(c, actor, csrf, message=''):
    tid = actor['tenant_id']
    users = c.execute('SELECT * FROM users WHERE tenant_id=? ORDER BY id', (tid,)).fetchall()
    body = f'''<div class="eyebrow">Settings</div><div class="title">Tenant &amp; users</div>
<div class="sub">Role-based access: admin (users/settings), manager (approvals/calculations/suppliers), reviewer (evidence/exceptions), viewer (read-only).</div>'''
    if message:
        body += f'<div class="successbox">{util.esc(message)}</div>'
    body += f'''<div class="card section"><h2>Users</h2><table><tr><th>Email</th><th>Role</th><th>Active</th></tr>'''
    for u in users:
        body += f'<tr><td>{util.esc(u["email"])}</td><td>{util.esc(u["role"])}</td><td>{"Yes" if u["active"] else "No"}</td></tr>'
    body += f'''</table>
<form method="post" action="/settings/user/create" class="section"><input type="hidden" name="csrf" value="{util.esc(csrf)}"><div class="formgrid3">
<div class="field"><label>Email</label><input name="email" type="email" required></div>
<div class="field"><label>Temporary password</label><input name="password" required></div>
<div class="field"><label>Role</label><select name="role"><option value="viewer">Viewer</option><option value="reviewer">Reviewer</option>
<option value="manager">Manager</option><option value="admin">Admin</option></select></div></div>
<button class="btn secondary small">+ Add user</button></form></div>'''
    body += '''<div class="card section"><h2>Data retention &amp; deletion</h2><p class="small muted">Policy-defined for this build (not yet code-enforced):
evidence documents and audit history are retained for the statutory CBAM record-keeping period. A tenant-initiated deletion request is handled
manually today and is logged as a REQUIRES EXTERNAL INTEGRATION item pending a retention-and-deletion engine (see README).</p></div>'''
    return layout(actor, 'Settings', body, 'settings')
