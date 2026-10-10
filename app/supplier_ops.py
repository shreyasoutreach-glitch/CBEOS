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
import json
import os
import re
import urllib.error
import urllib.request

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
    """Send only after an authenticated human invokes the Send action.

    Resend's API acceptance is recorded as accepted-by-provider, not as confirmed
    delivery. Delivery confirmation requires a separately configured webhook.
    """
    api_key = os.getenv('RESEND_API_KEY', '').strip()
    sender = os.getenv('CBAM_EMAIL_FROM', '').strip()
    recipient = str(request_row['supplier_email'] or '').strip()
    if not api_key or not sender:
        return {'accepted': False, 'status': 'not_configured', 'transport': 'resend'}
    if not recipient or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", recipient):
        return {'accepted': False, 'status': 'recipient_missing_or_invalid', 'transport': 'resend'}
    payload = {
        'from': sender,
        'to': [recipient],
        'subject': str(request_row['title'] or 'CBAM evidence request')[:200],
        'text': str(request_row['draft'] or '')[:12000],
    }
    req = urllib.request.Request(
        'https://api.resend.com/emails',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = int(getattr(response, 'status', 0))
            raw = response.read(100_000).decode('utf-8')
        if status_code not in (200, 201):
            return {'accepted': False, 'status': 'provider_rejected', 'transport': 'resend'}
        response_data = json.loads(raw)
        message_id = str(response_data.get('id', '')).strip()
        if not message_id:
            return {'accepted': False, 'status': 'provider_response_missing_id', 'transport': 'resend'}
        return {'accepted': True, 'status': 'accepted_by_provider', 'transport': 'resend', 'message_id': message_id}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError):
        return {'accepted': False, 'status': 'provider_error', 'transport': 'resend'}


def send_request(c, tid, req_id, uid):
    r = c.execute(
        'SELECT sr.*, s.contact_email AS supplier_email FROM supplier_requests sr '
        'JOIN suppliers s ON s.id=sr.supplier_id AND s.tenant_id=sr.tenant_id '
        'WHERE sr.id=? AND sr.tenant_id=?',
        (req_id, tid),
    ).fetchone()
    if not r:
        return False, 'Not found'
    delivery = notify_supplier(r)
    if not delivery.get('accepted'):
        state = delivery.get('status', 'provider_error')
        action = 'supplier_request_delivery_not_configured' if state == 'not_configured' else 'supplier_request_delivery_failed'
        audit(c, tid, r['case_id'], uid, action, f"request={req_id}; transport={delivery.get('transport', 'unknown')}; status={state}")
        if state == 'not_configured':
            return False, 'Email transport is not configured; the request remains a draft and was not sent.'
        if state == 'recipient_missing_or_invalid':
            return False, 'Supplier email is missing or invalid; the request remains a draft.'
        return False, 'Email provider did not accept the request; it remains a draft. Check provider configuration and retry.'
    c.execute("UPDATE supplier_requests SET status='SENT',sent_at=?,updated=? WHERE id=? AND tenant_id=?",
              (util.now(), util.now(), req_id, tid))
    audit(c, tid, r['case_id'], uid, 'supplier_request_accepted_by_provider',
          f"request={req_id}; transport={delivery.get('transport', 'unknown')}; message_id={delivery.get('message_id', '')}")
    return True, 'Accepted by email provider; delivery confirmation is not yet available.'


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
