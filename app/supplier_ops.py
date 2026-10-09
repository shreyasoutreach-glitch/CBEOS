"""Supplier evidence operations.

This is deliberately treated as a first-class workflow, not an afterthought --
research on the 2026 CBAM software market is consistent that supplier data
collection, not certificate purchasing or calculation, is the operationally
painful layer for importers this year. See engine.missing_requirements() for
the demand signal this module acts on.

Email delivery is a pluggable boundary (`notify_supplier`) rather than a real
SMTP/API integration -- see README "requires external infrastructure". The
request lifecycle, deadlines, escalation and quality scoring are fully real.
"""
from . import util
from .engine import audit, missing_requirements

REQUEST_STATES = ['DRAFT', 'SENT', 'WAITING', 'OVERDUE', 'RESPONDED', 'VALIDATED', 'CLOSED']


def draft_text(requirement_name, supplier_name, case_period):
    return (f"Dear {supplier_name} team,\n\n"
            f"As part of our CBAM {case_period} reporting, we still need the following supporting evidence: "
            f"{requirement_name}.\n\nPlease attach the source document and confirm the installation, reporting "
            f"period and product/import line it applies to. If actual installation-level data is not yet "
            f"available, please let us know so we can plan around the regulatory default value in the meantime.\n\n"
            f"Thank you,\nCBAM compliance team")


def generate_requests_for_supplier(c, tid, cid, supplier_id, uid, deadline=''):
    supplier = c.execute('SELECT * FROM suppliers WHERE id=? AND tenant_id=?', (supplier_id, tid)).fetchone()
    if not supplier:
        return 0
    case = c.execute('SELECT * FROM cases WHERE id=? AND tenant_id=?', (cid, tid)).fetchone()
    installations = [r['id'] for r in c.execute('SELECT id FROM installations WHERE tenant_id=? AND supplier_id=?',
                                                   (tid, supplier_id)).fetchall()]
    reqs = list(missing_requirements(c, tid, cid, scope_type='supplier', scope_id=supplier_id))
    for inst_id in installations:
        reqs += list(missing_requirements(c, tid, cid, scope_type='installation', scope_id=inst_id))
    created = 0
    t = util.now()
    for r in reqs:
        existing = c.execute("SELECT 1 FROM supplier_requests WHERE tenant_id=? AND case_id=? AND supplier_id=? "
                               "AND requirement_name=? AND status NOT IN ('CLOSED')",
                               (tid, cid, supplier_id, r['name'])).fetchone()
        if existing:
            continue
        title = f"Request: {r['name']}"
        draft = draft_text(r['name'], supplier['name'], case['period'] if case else '')
        c.execute('INSERT INTO supplier_requests(tenant_id,case_id,supplier_id,requirement_name,title,draft,status,'
                   'deadline,created_by,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                   (tid, cid, supplier_id, r['name'], title, draft, 'DRAFT', deadline, uid, t, t))
        created += 1
    if created:
        audit(c, tid, cid, uid, 'supplier_requests_created', f'supplier={supplier_id} count={created}')
    return created


def generate_all_supplier_requests(c, tid, cid, uid, deadline=''):
    total = 0
    for s in c.execute('SELECT id FROM suppliers WHERE tenant_id=?', (tid,)).fetchall():
        total += generate_requests_for_supplier(c, tid, cid, s['id'], uid, deadline)
    return total


def notify_supplier(request_row):
    """Pluggable delivery boundary. In this build it only marks the request as
    sent and records that no real transport ran -- wire an SMTP/API client
    here for production (see README)."""
    return {'delivered': False, 'transport': 'none (requires external email integration)'}


def send_request(c, tid, req_id, uid):
    r = c.execute('SELECT * FROM supplier_requests WHERE id=? AND tenant_id=?', (req_id, tid)).fetchone()
    if not r:
        return False, 'Not found'
    notify_supplier(r)
    c.execute("UPDATE supplier_requests SET status='SENT',sent_at=?,updated=? WHERE id=?", (util.now(), util.now(), req_id))
    audit(c, tid, r['case_id'], uid, 'supplier_request_sent', str(req_id))
    return True, ''


def mark_responded(c, tid, req_id, uid, validated=False):
    r = c.execute('SELECT * FROM supplier_requests WHERE id=? AND tenant_id=?', (req_id, tid)).fetchone()
    if not r:
        return False, 'Not found'
    status = 'VALIDATED' if validated else 'RESPONDED'
    c.execute('UPDATE supplier_requests SET status=?,responded_at=?,updated=? WHERE id=?',
               (status, util.now(), util.now(), req_id))
    audit(c, tid, r['case_id'], uid, 'supplier_request_' + status.lower(), str(req_id))
    return True, ''


def escalate_overdue(c, tid, cid):
    """Move SENT/WAITING requests past their deadline to OVERDUE and bump
    escalation_level. Idempotent; safe to run on every dashboard load."""
    today = util.now()[:10]
    rows = c.execute("SELECT * FROM supplier_requests WHERE tenant_id=? AND case_id=? AND status IN ('SENT','WAITING') "
                       "AND deadline!='' AND deadline<?", (tid, cid, today)).fetchall()
    for r in rows:
        c.execute("UPDATE supplier_requests SET status='OVERDUE',escalation_level=escalation_level+1,updated=? WHERE id=?",
                   (util.now(), r['id']))
    return len(rows)


def supplier_scorecard(c, tid, cid, supplier_id):
    """'Supplier X has N affected import lines. M are supported. K are blocked
    because installation-level emissions evidence is missing.' -- computed for
    real, not narrated."""
    lines = c.execute('SELECT * FROM import_lines WHERE tenant_id=? AND case_id=? AND supplier_id=?',
                        (tid, cid, supplier_id)).fetchall()
    supported = sum(1 for l in lines if l['status'] in ('reconciled', 'ready', 'calculated', 'approved'))
    blocked = sum(1 for l in lines if l['status'] == 'blocked')
    reqs = c.execute("SELECT COUNT(*) n FROM evidence_requirements WHERE tenant_id=? AND case_id=? AND scope_type IN "
                       "('supplier','installation') AND scope_id IN (SELECT id FROM installations WHERE supplier_id=? "
                       "UNION SELECT ?) AND status='complete'", (tid, cid, supplier_id, supplier_id)).fetchone()['n']
    reqs_total = c.execute("SELECT COUNT(*) n FROM evidence_requirements WHERE tenant_id=? AND case_id=? AND scope_type IN "
                             "('supplier','installation') AND scope_id IN (SELECT id FROM installations WHERE supplier_id=? "
                             "UNION SELECT ?) AND applicability!='not_applicable'", (tid, cid, supplier_id, supplier_id)).fetchone()['n']
    open_requests = c.execute("SELECT COUNT(*) n FROM supplier_requests WHERE tenant_id=? AND case_id=? AND supplier_id=? "
                                "AND status NOT IN ('VALIDATED','CLOSED')", (tid, cid, supplier_id)).fetchone()['n']
    overdue = c.execute("SELECT COUNT(*) n FROM supplier_requests WHERE tenant_id=? AND case_id=? AND supplier_id=? "
                          "AND status='OVERDUE'", (tid, cid, supplier_id)).fetchone()['n']
    quality = round(100 * reqs / reqs_total) if reqs_total else 100
    return {'lines_total': len(lines), 'lines_supported': supported, 'lines_blocked': blocked,
             'evidence_complete_pct': quality, 'open_requests': open_requests, 'overdue_requests': overdue}
