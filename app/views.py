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
:root{--bg:#070b12;--panel:#0e1522;--panel2:#111b2a;--line:#223149;--text:#edf4ff;--muted:#8292a9;--mint:#71e2b5;--amber:#f2c66d;--red:#f27b83;--blue:#80aefc}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% -10%,#13243b 0,#070b12 42%);color:var(--text);font:14px Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}
.shell{display:grid;grid-template-columns:225px 1fr;min-height:100vh}
.side{border-right:1px solid var(--line);padding:22px 14px;background:#080d16}
.logo{font-weight:950;font-size:18px;letter-spacing:-.5px;padding:4px 10px 22px}.logo span{color:var(--mint)}
.nav a{display:block;color:#9bacbf;text-decoration:none;padding:9px 12px;border-radius:9px;margin:2px 0;font-size:13px}
.nav a:hover,.nav a.active{background:#142238;color:#fff}
.navgroup{color:#4d5d74;font-size:10px;text-transform:uppercase;letter-spacing:1px;padding:14px 12px 4px}
.sidefoot{position:fixed;bottom:16px;width:195px;color:#526278;font-size:10.5px}
.main{padding:28px 34px;max-width:1560px;width:100%}
.top{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;flex-wrap:wrap}
.eyebrow{text-transform:uppercase;letter-spacing:1.6px;color:var(--mint);font-size:10px;font-weight:900}
.title{font-size:29px;line-height:1.08;margin:6px 0 7px;letter-spacing:-1px}
.sub{color:var(--muted);max-width:800px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin:20px 0}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:13px}
.grid5{display:grid;grid-template-columns:repeat(5,1fr);gap:13px}
.two{display:grid;grid-template-columns:1.5fr 1fr;gap:15px}
.card{background:linear-gradient(180deg,#101a2a,#0c1420);border:1px solid var(--line);border-radius:14px;padding:17px;box-shadow:0 16px 40px #0005}
.kpi{font-size:26px;font-weight:950;margin-top:6px}
.label{color:#788aa2;font-size:10.5px;text-transform:uppercase;letter-spacing:.7px}
.bar{height:7px;background:#1c2a3e;border-radius:9px;overflow:hidden}.fill{height:100%;background:var(--mint)}
table{width:100%;border-collapse:collapse}
th{font-size:9.5px;color:#71829a;text-transform:uppercase;letter-spacing:.6px;text-align:left;padding:9px 7px;border-bottom:1px solid var(--line)}
td{padding:10px 7px;border-bottom:1px solid #1b293c;vertical-align:top;font-size:13px}
a{color:var(--mint)}
.pill{display:inline-flex;padding:3px 8px;border-radius:999px;background:#17243a;color:#b8c7da;font-size:10.5px;font-weight:800;white-space:nowrap}
.pill.good{background:#0d2a20;color:var(--mint)}.pill.warn{background:#302614;color:var(--amber)}.pill.bad{background:#31171b;color:var(--red)}
.pill.info{background:#132338;color:var(--blue)}
.btn{display:inline-block;background:var(--mint);color:#06120d;text-decoration:none;border:0;border-radius:8px;padding:9px 12px;font-weight:900;cursor:pointer;font-size:12.5px}
.btn.secondary{background:#19283d;color:#dbe6f5}.btn.danger{background:#3a1a20;color:#ffb2b7}.btn.small{padding:5px 9px;font-size:11px}
.actions{display:flex;gap:7px;flex-wrap:wrap}
.formgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:11px}.formgrid3{display:grid;grid-template-columns:repeat(3,1fr);gap:11px}
.field{margin-bottom:9px}.field label{display:block;color:#9aabc0;font-size:10.5px;text-transform:uppercase;letter-spacing:.4px}
.field input,.field select,.field textarea{width:100%;margin-top:5px;background:#09111d;color:#eef5ff;border:1px solid #2a3a51;border-radius:8px;padding:9px}
.field textarea{min-height:90px}
.notice,.dangerbox,.successbox,.warnbox{padding:11px 13px;border-radius:10px;margin:11px 0}
.notice{background:#241e10;border-left:3px solid var(--amber)}.dangerbox{background:#281519;border-left:3px solid var(--red)}
.successbox{background:#0b2119;border-left:3px solid var(--mint)}.warnbox{background:#241e10;border-left:3px solid var(--amber)}
.section{margin-top:16px}.small{font-size:11.5px}
.source{font-family:ui-monospace,monospace;font-size:10.5px;color:#9eb0c7;background:#0a111c;padding:6px;border-radius:7px;white-space:pre-wrap}
.login{min-height:100vh;display:grid;place-items:center}.login .card{width:400px}
.footer{margin-top:26px;color:#526278;font-size:10.5px;border-top:1px solid var(--line);padding-top:14px}
.trace{display:flex;flex-direction:column;gap:2px}
.trace .node{background:#0d1826;border:1px solid #233149;border-radius:10px;padding:10px 12px;position:relative}
.trace .arrow{text-align:center;color:#3f5069;font-size:16px;margin:-2px 0}
.checklist{list-style:none;padding:0;margin:0}
.checklist li{padding:7px 0;border-bottom:1px solid #17233650;font-size:12.5px;display:flex;gap:9px;align-items:flex-start}
.tick{width:16px;flex:0 0 16px;font-weight:900}
.tick.yes{color:var(--mint)}.tick.no{color:var(--red)}
.tabs{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}
.tabs a{padding:7px 11px;border-radius:8px;background:#111c2c;color:#9bacbf;text-decoration:none;font-size:12px}
.tabs a.active{background:var(--mint);color:#06120d;font-weight:800}
.kv{display:grid;grid-template-columns:170px 1fr;gap:6px 10px;font-size:12.5px}
.kv div:nth-child(odd){color:#8292a9}
@media(max-width:1080px){.shell{grid-template-columns:1fr}.side{display:none}.main{padding:18px}.grid,.grid3,.grid5,.two,.formgrid,.formgrid3{grid-template-columns:1fr}}
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
    re(f'<a class="{"active" if k == active else ""}" href="{u}">{n}</a>' for k, u, n in NAV)
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{util.esc(title)} · CBAM Evidence OS</title><style>{CSS}</style></head><body><div class="shell">
<aside class="side"><div class="logo">CBAM <span>Control Tower</span></div><nav class="nav">{nav}</nav>
<div class="sidefoot">Evidence graph · reconciliation · exception queue · verification readiness<br><br>
{util.esc(actor["email"])} · {util.esc(actor["role"])}<br><a href="/logout">Sign out</a></div></aside>
<main class="main">{content}<div class="footer">CBAM Evidence OS · Control Tower build · scenario calculations
are not a declaration, legal opinion, or verified submission.</div></main></div></body></html>'''


def login_page(error=''):
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>CBAM Evidence OS · Sign in</title><style>{CSS}</style></head><body><div class="login"><div class="card">
<div class="eyebrow">Compliance Control Tower</div><div class="title">CBAM Evidence OS</div>
<p class="sub">Turn fragmented supplier and trade documents into verified, traceable, submission-ready CBAM records.</p>
{f'<div class="dangerbox">{util.esc(error)}</div>' if error else ''}
<form method="post" action="/login"><div class="field"><label>Email</label><input name="email" type="email" required></div>
<div class="field"><label>Password</label><input name="password" type="password" required></div>
<button class="btn" type="submit">Sign in</button></form>
<p class="muted small">Local demo defaults: admin@example.com / change-me-now. Set CBAM_ADMIN_PASSWORD before any real deployment.</p>
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
    total_lines = c.execute('SELECT COUNT(*) n FROM import_lines WHERE tenant_id=?', (tid,)).fetchone()['n']
    blocked_lines = c.execute("SELECT COUNT(*) n FROM import_lines WHERE tenant_id=? AND status='blocked'", (tid,)).fetchone()['n']
    ready_lines = c.execute("SELECT COUNT(*) n FROM import_lines WHERE tenant_id=? AND status IN ('ready','calculated','approved')", (tid,)).fetchone()['n']
    open_exceptions = c.execute("SELECT COUNT(*) n FROM exceptions WHERE tenant_id=? AND status NOT IN ('RESOLVED','ACCEPTED_WITH_RISK','WAIVED')", (tid,)).fetchone()['n']
    high_exceptions = c.execute("SELECT COUNT(*) n FROM exceptions WHERE tenant_id=? AND status NOT IN ('RESOLVED','ACCEPTED_WITH_RISK','WAIVED') AND severity='high'", (tid,)).fetchone()['n']
    overdue_requests = c.execute("SELECT COUNT(*) n FROM supplier_requests WHERE tenant_id=? AND status='OVERDUE'", (tid,)).fetchone()['n']
    suppliers_n = c.execute('SELECT COUNT(*) n FROM suppliers WHERE tenant_id=?', (tid,)).fetchone()['n']
    installations_n = c.execute('SELECT COUNT(*) n FROM installations WHERE tenant_id=?', (tid,)).fetchone()['n']
    docs_n = c.execute('SELECT COUNT(*) n FROM documents WHERE tenant_id=?', (tid,)).fetchone()['n']
    calc_rows = c.execute("SELECT result_json FROM calculation_runs WHERE tenant_id=? AND run_type='import_line' AND id IN (SELECT MAX(id) FROM calculation_runs WHERE tenant_id=? GROUP BY import_line_id)", (tid, tid)).fetchall()
    exposure = sum((util.num(json.loads(r['result_json']).get('indicative_certificate_equivalent') or 0) * util.num(json.loads(r['result_json']).get('certificate_price_eur_per_tco2e') or 0)) for r in calc_rows)
    rs = engine.latest_rule_set(c)
    latest_price = engine.latest_certificate_price(c, rs['id']) if rs else None
    body = f"""<div class=\"top\"><div><div class=\"eyebrow\">Control tower</div><div class=\"title\">Evidence → exception → financial consequence</div>
<div class=\"sub\">CBAM Evidence OS is not another ca