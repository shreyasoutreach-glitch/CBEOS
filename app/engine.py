"""The product's moat, in code.

Sections below map directly onto the CTO directive:
  - Domain CRUD           (§5 domain model)
  - Reconciliation engine (§8)
  - Exception engine      (§9)
  - Verification readiness(§13)
  - Regulatory rule engine(§11)
  - Calculation engine    (§12)
  - Declaration package   (§14)
  - Audit chain           (§26)

Every function takes an open sqlite3 connection `c` and an explicit tenant_id
`tid` -- there is no code path in this module that can act across tenants,
because nothing here ever infers tenant_id from anything other than the
caller-supplied value, and the caller (server.py) always sources tid from the
authenticated session, never from request parameters.
"""
import json
from decimal import Decimal

from . import util
from .db import REQS, FIELD_LABELS


def calculate_marked_default_total(base_total, markup_pct):
    """Apply the legal default markup to the total field at runtime precision."""
    try:
        base = Decimal(str(base_total))
        pct = Decimal(str(markup_pct))
    except Exception as exc:
        raise ValueError('Default total and markup must be valid decimals.') from exc
    if not base.is_finite() or not pct.is_finite() or base < 0 or pct < 0:
        raise ValueError('Default total and markup must be finite and non-negative.')
    return (base * (Decimal('1') + pct / Decimal('100'))).quantize(Decimal('0.0001'))

# ---------------------------------------------------------------------------
# Audit chain (append-only, per-tenant hash chain)
# ---------------------------------------------------------------------------

def audit(c, tid, cid, uid, action, detail=''):
    prev = c.execute('SELECT hash FROM audit WHERE tenant_id=? ORDER BY id DESC LIMIT 1', (tid,)).fetchone()
    prev = prev['hash'] if prev else ''
    created = util.now()
    payload = f'{tid}|{cid}|{uid}|{action}|{detail}|{created}|{prev}'
    h = util.sha256_text(payload)
    c.execute('INSERT INTO audit(tenant_id,case_id,actor_id,action,detail,created,prev_hash,hash) '
              'VALUES(?,?,?,?,?,?,?,?)', (tid, cid, uid, action, detail, created, prev, h))
    return h


def verify_audit_chain(c, tid):
    """Recompute the hash chain for a tenant and report any break. Used by the
    /audit screen and by tests -- this is what makes 'append-only' a checkable
    claim rather than an assertion in a README."""
    rows = c.execute('SELECT * FROM audit WHERE tenant_id=? ORDER BY id ASC', (tid,)).fetchall()
    prev = ''
    for r in rows:
        payload = f"{r['tenant_id']}|{r['case_id']}|{r['actor_id']}|{r['action']}|{r['detail']}|{r['created']}|{prev}"
        expect = util.sha256_text(payload)
        if expect != r['hash'] or (r['prev_hash'] or '') != prev:
            return False, r['id']
        prev = r['hash']
    return True, None


# ---------------------------------------------------------------------------
# Domain CRUD
# ---------------------------------------------------------------------------

def create_reporting_period(c, tid, code, start_date='', end_date='', declaration_deadline=''):
    row = c.execute('SELECT id FROM reporting_periods WHERE tenant_id=? AND code=?', (tid, code)).fetchone()
    if row:
        return row['id']
    c.execute('INSERT INTO reporting_periods(tenant_id,code,start_date,end_date,declaration_deadline,status,created) '
              'VALUES(?,?,?,?,?,?,?)', (tid, code, start_date, end_date, declaration_deadline, 'open', util.now()))
    return c.execute('SELECT last_insert_rowid()').fetchone()[0]


def create_supplier(c, tid, name, country='', contact_name='', contact_email='', external_ref='', notes=''):
    t = util.now()
    c.execute('INSERT INTO suppliers(tenant_id,name,country,contact_name,contact_email,external_ref,notes,'
              'created,updated) VALUES(?,?,?,?,?,?,?,?,?)',
              (tid, name, country, contact_name, contact_email, external_ref, notes, t, t))
    return c.execute('SELECT last_insert_rowid()').fetchone()[0]


def create_installation(c, tid, supplier_id, name, country='', production_route='', unlocode=''):
    if supplier_id is not None and not c.execute('SELECT 1 FROM suppliers WHERE id=? AND tenant_id=?', (supplier_id, tid)).fetchone():
        raise ValueError('Supplier does not belong to this tenant')
    t = util.now()
    c.execute('INSERT INTO installations(tenant_id,supplier_id,name,country,unlocode,production_route,'
              'created,updated) VALUES(?,?,?,?,?,?,?,?)',
              (tid, supplier_id, name, country, unlocode, production_route, t, t))
    return c.execute('SELECT last_insert_rowid()').fetchone()[0]


def create_product(c, tid, cn_code, description='', sector=''):
    row = c.execute('SELECT id FROM products WHERE tenant_id=? AND cn_code=?', (tid, cn_code)).fetchone()
    if row:
        return row['id']
    if not sector:
        ref = c.execute('SELECT sector,description FROM cn_reference WHERE code=?', (cn_code,)).fetchone()
        if ref:
            sector = ref['sector']
            description = description or ref['description']
    t = util.now()
    c.execute('INSERT INTO products(tenant_id,cn_code,description,sector,created,updated) VALUES(?,?,?,?,?,?)',
              (tid, cn_code, description, sector, t, t))
    return c.execute('SELECT last_insert_rowid()').fetchone()[0]


def create_import(c, tid, cid, reference, mode='sea', arrival_date='', customs_office=''):
    if not c.execute('SELECT 1 FROM cases WHERE id=? AND tenant_id=?', (cid, tid)).fetchone():
        raise ValueError('Case does not belong to this tenant')
    if mode not in ('sea', 'air', 'road', 'rail', 'other'):
        raise ValueError('Unsupported transport mode')
    t = util.now()
    c.execute('INSERT INTO imports(tenant_id,case_id,reference,mode,arrival_date,customs_office,created,updated) '
              'VALUES(?,?,?,?,?,?,?,?)', (tid, cid, reference, mode, arrival_date, customs_office, t, t))
    return c.execute('SELECT last_insert_rowid()').fetchone()[0]


def create_import_line(c, tid, cid, **kw):
    if not c.execute('SELECT 1 FROM cases WHERE id=? AND tenant_id=?', (cid, tid)).fetchone():
        raise ValueError('Case does not belong to this tenant')
    for field, table in (('import_id', 'imports'), ('product_id', 'products'), ('supplier_id', 'suppliers'),
                         ('installation_id', 'installations'), ('reporting_period_id', 'reporting_periods')):
        ref = kw.get(field)
        if ref not in (None, '') and not c.execute(f'SELECT 1 FROM {table} WHERE id=? AND tenant_id=?', (ref, tid)).fetchone():
            raise ValueError(f'{field} does not belong to this tenant')
    if kw.get('import_id') not in (None, ''):
        imp = c.execute('SELECT case_id FROM imports WHERE id=? AND tenant_id=?', (kw['import_id'], tid)).fetchone()
        if not imp or imp['case_id'] != cid:
            raise ValueError('Import does not belong to this case')
    if kw.get('installation_id') not in (None, ''):
        inst = c.execute('SELECT supplier_id FROM installations WHERE id=? AND tenant_id=?', (kw['installation_id'], tid)).fetchone()
        if kw.get('supplier_id') not in (None, '') and inst and inst['supplier_id'] not in (None, kw['supplier_id']):
            raise ValueError('Installation does not belong to the selected supplier')
    if kw.get('product_id') not in (None, '') and kw.get('cn_code'):
        product = c.execute('SELECT cn_code FROM products WHERE id=? AND tenant_id=?', (kw['product_id'], tid)).fetchone()
        if product and str(product['cn_code']) != str(kw['cn_code']):
            raise ValueError('Product CN code does not match the import line')
    if kw.get('quantity') not in (None, ''):
        q = util.num(kw.get('quantity'), None)
        if q is None or not q.is_finite() or q <= 0 or q > Decimal('1000000000000'):
            raise ValueError('Import quantity must be a positive finite number within the supported range')
    if kw.get('customs_value') not in (None, ''):
        v = util.num(kw.get('customs_value'), None)
        if v is None or not v.is_finite() or v < 0 or v > Decimal('1000000000000'):
            raise ValueError('Customs value must be a non-negative finite number within the supported range')
    t = util.now()
    fields = ['import_id', 'product_id', 'supplier_id', 'installation_id', 'reporting_period_id',
              'invoice_ref', 'cn_code', 'description', 'origin_country', 'quantity', 'quantity_unit',
              'customs_value', 'customs_ref', 'production_route', 'applicability', 'status']
    fk_fields = {'import_id', 'product_id', 'supplier_id', 'installation_id', 'reporting_period_id'}

    def default_for(f):
        if f in fk_fields:
            return None
        if f == 'applicability':
            return 'needs_review'
        if f == 'status':
            return 'candidate'
        return ''
    vals = [kw.get(f) if kw.get(f) not in (None, '') else default_for(f) for f in fields]
    c.execute(f'INSERT INTO import_lines(tenant_id,case_id,{",".join(fields)},created,updated) '
              f'VALUES(?,?,{",".join("?" for _ in fields)},?,?)', (tid, cid, *vals, t, t))
    lid = c.execute('SELECT last_insert_rowid()').fetchone()[0]
    return lid


# ---------------------------------------------------------------------------
# Evidence requirements (scope-aware: case / supplier / installation / import_line)
# ---------------------------------------------------------------------------

REQ_ALIASES = {
    'commercial': {'commercial', 'invoice'}, 'shipping': {'shipping', 'packing_list', 'bill_of_lading'},
    'classification': {'classification'}, 'customs': {'customs'}, 'installation': {'installation', 'producer'},
    'activity': {'activity', 'production'}, 'emissions': {'emissions', 'energy'}, 'methodology': {'methodology'},
    'carbon_price': {'carbon_price'}, 'free_allocation': {'free_allocation'}, 'verification': {'verification'},
    'supplier': {'supplier', 'supplier_declaration'},
}


def sync_requirements(c, tid, cid):
    """(Re)generate evidence_requirements rows for every applicable scope
    instance in this case (the case itself, each supplier, each installation,
    each import line), then recompute each requirement's status against the
    evidence ledger. Idempotent -- safe to call on every page load."""
    t = util.now()
    scopes = {'case': [0]}
    scopes['supplier'] = [r['id'] for r in c.execute(
        'SELECT DISTINCT supplier_id id FROM import_lines WHERE tenant_id=? AND case_id=? AND supplier_id IS NOT NULL',
        (tid, cid)).fetchall()]
    scopes['installation'] = [r['id'] for r in c.execute(
        'SELECT DISTINCT installation_id id FROM import_lines WHERE tenant_id=? AND case_id=? AND installation_id IS NOT NULL',
        (tid, cid)).fetchall()]
    scopes['import_line'] = [r['id'] for r in c.execute(
        'SELECT id FROM import_lines WHERE tenant_id=? AND case_id=?', (tid, cid)).fetchall()]

    for name, cat, app, scope_type, why in REQS:
        for scope_id in scopes.get(scope_type, [0]):
            c.execute('INSERT OR IGNORE INTO evidence_requirements(tenant_id,case_id,name,category,applicability,'
                       'status,scope_type,scope_id,reason,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (tid, cid, name, cat, app, 'missing', scope_type, scope_id,
                        'Operational default. Confirm applicability for the actual goods/import line.', t, t))

    for r in c.execute('SELECT * FROM evidence_requirements WHERE tenant_id=? AND case_id=?', (tid, cid)).fetchall():
        if r['applicability'] == 'not_applicable':
            continue
        allowed = REQ_ALIASES.get(r['category'], {r['category']})
        placeholders = ','.join('?' * len(allowed))
        match = c.execute(
            f"SELECT 1 FROM evidence WHERE tenant_id=? AND case_id=? AND status IN ('complete','verified') "
            f"AND category IN ({placeholders}) AND scope_type=? AND (scope_id=? OR ?=0) LIMIT 1",
            (tid, cid, *allowed, r['scope_type'], r['scope_id'], r['scope_id'])).fetchone()
        status = 'complete' if match else 'missing'
        if status != r['status']:
            c.execute('UPDATE evidence_requirements SET status=?,updated=? WHERE id=?', (status, t, r['id']))


def set_requirement_applicability(c, tid, req_id, applicability, reason, uid):
    r = c.execute('SELECT * FROM evidence_requirements WHERE id=? AND tenant_id=?', (req_id, tid)).fetchone()
    if not r:
        return False
    c.execute('UPDATE evidence_requirements SET applicability=?,reason=?,updated=? WHERE id=?',
               (applicability, reason, util.now(), req_id))
    audit(c, tid, r['case_id'], uid, 'requirement_applicability_set', f'{req_id}:{applicability}:{reason}')
    return True


def missing_requirements(c, tid, cid, scope_type=None, scope_id=None):
    q = ("SELECT * FROM evidence_requirements WHERE tenant_id=? AND case_id=? AND status='missing' "
         "AND applicability!='not_applicable'")
    args = [tid, cid]
    if scope_type:
        q += ' AND scope_type=?'
        args.append(scope_type)
    if scope_id is not None:
        q += ' AND scope_id=?'
        args.append(scope_id)
    return c.execute(q, args).fetchall()


# ---------------------------------------------------------------------------
# Reconciliation engine
# ---------------------------------------------------------------------------

RECONCILE_SEVERITY = {
    'eu_tonnes': 'high', 'cn_code': 'high', 'direct_intensity': 'high', 'indirect_intensity': 'high',
    'invoice_number': 'medium', 'supplier': 'medium', 'shipment_reference': 'low', 'origin_country': 'medium',
}


#: Which extracted fields are even *expected* to be single-valued at each
#: scope. An import line should agree on all of these across its documents;
#: an installation legitimately sees a different invoice/CN/quantity on every
#: shipment, so only intensity/identity fields are compared there -- otherwise
#: "installation X shipped 12 different invoices" would misreport as 12 conflicts.
SCOPE_RECONCILE_FIELDS = {
    'import_line_id': {'eu_tonnes', 'cn_code', 'invoice_number', 'supplier', 'origin_country', 'shipment_reference'},
    'installation_id': {'direct_intensity', 'indirect_intensity', 'installation', 'origin_country'},
}


def reconcile_scope(c, tid, cid, scope_col, scope_id):
    """Compare non-rejected fact values for one scope (one import line, or one
    installation) across every source document attached to it. Returns a list
    of (field, sorted distinct values, severity)."""
    relevant = SCOPE_RECONCILE_FIELDS.get(scope_col)
    rows = c.execute(
        f"SELECT field,value FROM facts WHERE tenant_id=? AND case_id=? AND {scope_col}=? AND status!='rejected' "
        f"ORDER BY field,id", (tid, cid, scope_id)).fetchall()
    by = {}
    for r in rows:
        if relevant and r['field'] not in relevant:
            continue
        by.setdefault(r['field'], set()).add(r['value'].strip())
    out = []
    for k, v in by.items():
        if len(v) > 1:
            out.append((k, sorted(v), RECONCILE_SEVERITY.get(k, 'medium')))
    return out


def implausibility_checks(c, tid, cid):
    """Compare validated installation emissions intensity against the
    regulatory default value for that sector; flag values that look too low
    (data-quality risk) or absurdly high (unit error risk)."""
    findings = []
    rs = latest_rule_set(c)
    if not rs:
        return findings
    for ed in c.execute(
            "SELECT e.*,i.name iname,i.tenant_id FROM emissions_data e JOIN installations i ON i.id=e.installation_id "
            "WHERE e.tenant_id=? AND e.status!='superseded'", (tid,)).fetchall():
        installation = c.execute('SELECT * FROM installations WHERE id=?', (ed['installation_id'],)).fetchone()
        if not installation:
            continue
        line = c.execute('SELECT cn_code FROM import_lines WHERE tenant_id=? AND case_id=? AND installation_id=? LIMIT 1',
                          (tid, cid, ed['installation_id'])).fetchone()
        if not line:
            continue
        default = lookup_default_value(c, rs['id'], None, line['cn_code'])
        if not default or default['confidence'] != 'official' or not ed['direct_intensity']:
            continue
        actual = util.num(ed['direct_intensity'])
        default_val = util.num(default['direct_default'])
        if default_val <= 0:
            continue
        ratio = actual / default_val
        if ratio < Decimal('0.1'):
            findings.append((ed['installation_id'], installation['name'],
                              f"Reported direct intensity ({actual} tCO2e/t) is under 10% of the sector default "
                              f"({default_val} tCO2e/t) -- verify units and methodology before trusting this value.",
                              'high'))
        elif ratio > Decimal('3'):
            findings.append((ed['installation_id'], installation['name'],
                              f"Reported direct intensity ({actual} tCO2e/t) is over 3x the sector default "
                              f"({default_val} tCO2e/t) -- check for a unit or transcription error.",
                              'high'))
    return findings


def run_reconciliation(c, tid, cid, uid):
    """The reconciliation pass: run on every case-detail load and after every
    upload/edit. Opens exceptions for new conflicts, auto-closes exceptions
    whose underlying condition has disappeared (e.g. a reviewer rejected the
    bad value). Never silently 'fixes' anything -- it only ever surfaces."""
    t = util.now()
    open_titles_by_key = {}
    for r in c.execute("SELECT id,title,field,affected_entity_type,affected_entity_id FROM exceptions "
                        "WHERE tenant_id=? AND case_id=? AND status='OPEN' AND category='reconciliation'",
                        (tid, cid)).fetchall():
        open_titles_by_key[(r['affected_entity_type'], r['affected_entity_id'], r['field'])] = r['id']

    seen_keys = set()
    for line in c.execute('SELECT id FROM import_lines WHERE tenant_id=? AND case_id=?', (tid, cid)).fetchall():
        for field, vals, sev in reconcile_scope(c, tid, cid, 'import_line_id', line['id']):
            key = ('import_line', line['id'], field)
            seen_keys.add(key)
            if key not in open_titles_by_key:
                label = FIELD_LABELS.get(field, field)
                create_exception(c, tid, cid, title=f'Cross-document conflict: {label}', category='reconciliation',
                                   severity=sev, affected_entity_type='import_line', affected_entity_id=line['id'],
                                   field=field, detail=f"Different non-rejected values found for {label}: {', '.join(vals)}",
                                   source='reconciliation_engine', owner='reviewer')
    for inst in c.execute('SELECT id FROM installations WHERE tenant_id=?', (tid,)).fetchall():
        for field, vals, sev in reconcile_scope(c, tid, cid, 'installation_id', inst['id']):
            key = ('installation', inst['id'], field)
            seen_keys.add(key)
            if key not in open_titles_by_key:
                label = FIELD_LABELS.get(field, field)
                create_exception(c, tid, cid, title=f'Cross-document conflict: {label}', category='reconciliation',
                                   severity=sev, affected_entity_type='installation', affected_entity_id=inst['id'],
                                   field=field, detail=f"Different non-rejected values found for {label}: {', '.join(vals)}",
                                   source='reconciliation_engine', owner='reviewer')

    # auto-close conflicts whose condition disappeared
    for (etype, eid, field), eid_row in open_titles_by_key.items():
        if (etype, eid, field) not in seen_keys:
            c.execute("UPDATE exceptions SET status='RESOLVED',resolution='Auto-resolved: values now consistent.',"
                       "updated=? WHERE id=?", (t, eid_row))

    for installation_id, iname, msg, sev in implausibility_checks(c, tid, cid):
        existing = c.execute("SELECT id FROM exceptions WHERE tenant_id=? AND case_id=? AND category='implausible_value' "
                               "AND affected_entity_type='installation' AND affected_entity_id=? AND status='OPEN'",
                               (tid, cid, installation_id)).fetchone()
        if not existing:
            create_exception(c, tid, cid, title=f'Implausible emissions value: {iname}', category='implausible_value',
                               severity=sev, affected_entity_type='installation', affected_entity_id=installation_id,
                               detail=msg, source='reconciliation_engine', owner='reviewer',
                               recommended_action='Confirm units and recompute with the supplier before relying on this value.')

    if c.execute("SELECT COUNT(*) n FROM facts WHERE tenant_id=? AND case_id=? AND status='candidate'",
                  (tid, cid)).fetchone()['n'] > 0:
        if not c.execute("SELECT 1 FROM exceptions WHERE tenant_id=? AND case_id=? AND title='Candidate facts require review' "
                          "AND status='OPEN'", (tid, cid)).fetchone():
            create_exception(c, tid, cid, title='Candidate facts require review', category='review_required',
                               severity='medium', detail='Extracted facts are not authoritative until a reviewer verifies or rejects them.',
                               source='system', owner='reviewer')
    else:
        c.execute("UPDATE exceptions SET status='RESOLVED',resolution='Auto-resolved: no candidate facts remain.',updated=? "
                   "WHERE tenant_id=? AND case_id=? AND title='Candidate facts require review' AND status='OPEN'", (t, tid, cid))

    sync_requirements(c, tid, cid)
    for r in missing_requirements(c, tid, cid):
        title = f"Missing evidence: {r['name']} ({r['scope_type']})"
        if not c.execute("SELECT 1 FROM exceptions WHERE tenant_id=? AND case_id=? AND title=? AND status='OPEN'",
                          (tid, cid, title)).fetchone():
            create_exception(c, tid, cid, title=title, category='missing_evidence', severity='medium',
                               affected_entity_type=r['scope_type'], affected_entity_id=r['scope_id'],
                               detail=f"Requirement '{r['name']}' has no linked evidence yet.", source='requirements_engine',
                               owner='supplier' if r['scope_type'] in ('supplier', 'installation') else 'reviewer')
    for r in c.execute("SELECT id,title FROM exceptions WHERE tenant_id=? AND case_id=? AND category='missing_evidence' "
                        "AND status='OPEN'", (tid, cid)).fetchall():
        req_name = r['title'].split('Missing evidence: ', 1)[-1].rsplit(' (', 1)[0]
        still_missing = c.execute("SELECT 1 FROM evidence_requirements WHERE tenant_id=? AND case_id=? AND name=? "
                                    "AND status='missing' AND applicability!='not_applicable'", (tid, cid, req_name)).fetchone()
        if not still_missing:
            c.execute("UPDATE exceptions SET status='RESOLVED',resolution='Auto-resolved: evidence now on file.',updated=? "
                       "WHERE id=?", (t, r['id']))


# ---------------------------------------------------------------------------
# Exception engine (state machine)
# ---------------------------------------------------------------------------

EXCEPTION_STATES = ['OPEN', 'UNDER_REVIEW', 'WAITING_SUPPLIER', 'WAITING_INTERNAL', 'RESOLVED',
                     'ACCEPTED_WITH_RISK', 'BLOCKED', 'WAIVED']
TERMINAL_STATES = {'RESOLVED', 'ACCEPTED_WITH_RISK', 'WAIVED'}


def create_exception(c, tid, cid, title, category, severity, detail='', affected_entity_type='', affected_entity_id=None,
                       field='', supporting_evidence='', conflicting_evidence='', recommended_action='', owner='',
                       deadline='', source=''):
    t = util.now()
    c.execute('INSERT INTO exceptions(tenant_id,case_id,title,category,severity,status,affected_entity_type,'
              'affected_entity_id,detail,field,supporting_evidence,conflicting_evidence,recommended_action,owner,'
              'deadline,source,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
              (tid, cid, title, category, severity, 'OPEN', affected_entity_type, affected_entity_id, detail, field,
               supporting_evidence, conflicting_evidence, recommended_action, owner, deadline, source, t, t))
    return c.execute('SELECT last_insert_rowid()').fetchone()[0]


def transition_exception(c, tid, exc_id, uid, new_status, resolution='', owner=None, deadline=None):
    if new_status not in EXCEPTION_STATES:
        return False, 'Unknown status'
    r = c.execute('SELECT * FROM exceptions WHERE id=? AND tenant_id=?', (exc_id, tid)).fetchone()
    if not r:
        return False, 'Not found'
    t = util.now()
    fields = {'status': new_status, 'updated': t}
    if resolution:
        fields['resolution'] = resolution
    if owner is not None:
        fields['owner'] = owner
    if deadline is not None:
        fields['deadline'] = deadline
    if new_status in TERMINAL_STATES:
        fields['closed_by'] = uid
    set_clause = ','.join(f'{k}=?' for k in fields)
    c.execute(f'UPDATE exceptions SET {set_clause} WHERE id=?', (*fields.values(), exc_id))
    audit(c, tid, r['case_id'], uid, 'exception_transition', f'{exc_id}:{r["status"]}->{new_status}:{resolution}')
    return True, ''


# ---------------------------------------------------------------------------
# Case / portfolio readiness
# ---------------------------------------------------------------------------

def readiness(c, tid, cid):
    docs = c.execute('SELECT COUNT(*) n FROM documents WHERE tenant_id=? AND case_id=?', (tid, cid)).fetchone()['n']
    cand = c.execute("SELECT COUNT(*) n FROM facts WHERE tenant_id=? AND case_id=? AND status='candidate'", (tid, cid)).fetchone()['n']
    verified = c.execute("SELECT COUNT(*) n FROM facts WHERE tenant_id=? AND case_id=? AND status='verified'", (tid, cid)).fetchone()['n']
    ev = c.execute('SELECT COUNT(*) n FROM evidence WHERE tenant_id=? AND case_id=?', (tid, cid)).fetchone()['n']
    done = c.execute("SELECT COUNT(*) n FROM evidence WHERE tenant_id=? AND case_id=? AND status IN ('complete','verified')", (tid, cid)).fetchone()['n']
    issues = c.execute("SELECT COUNT(*) n FROM exceptions WHERE tenant_id=? AND case_id=? AND status NOT IN ('RESOLVED','ACCEPTED_WITH_RISK','WAIVED')", (tid, cid)).fetchone()['n']
    high = c.execute("SELECT COUNT(*) n FROM exceptions WHERE tenant_id=? AND case_id=? AND status NOT IN ('RESOLVED','ACCEPTED_WITH_RISK','WAIVED') AND severity='high'", (tid, cid)).fetchone()['n']
    req = c.execute("SELECT COUNT(*) n FROM evidence_requirements WHERE tenant_id=? AND case_id=? AND status='missing' AND applicability!='not_applicable'", (tid, cid)).fetchone()['n']
    lines_total = c.execute('SELECT COUNT(*) n FROM import_lines WHERE tenant_id=? AND case_id=?', (tid, cid)).fetchone()['n']
    lines_blocked = c.execute("SELECT COUNT(*) n FROM import_lines WHERE tenant_id=? AND case_id=? AND status='blocked'", (tid, cid)).fetchone()['n']
    blockers = []
    if not docs:
        blockers.append('No source documents')
    if cand:
        blockers.append(f'{cand} candidate fact(s) require review')
    if not ev:
        blockers.append('Evidence ledger is empty')
    elif done != ev:
        blockers.append(f'{ev - done} evidence item(s) incomplete')
    if issues:
        blockers.append(f'{issues} open exception(s)')
    if req:
        blockers.append(f'{req} applicable evidence requirement(s) missing')
    score = max(0, 100 - 25 * int(not docs) - 20 * int(cand > 0) - 15 * int(not ev) - 15 * int(ev > 0 and done != ev)
                - 15 * int(issues > 0) - 10 * int(req > 0))
    return score, {'docs': docs, 'verified_facts': verified, 'candidate_facts': cand, 'evidence': ev,
                    'evidence_done': done, 'open_issues': issues, 'high_issues': high, 'missing_requirements': req,
                    'import_lines_total': lines_total, 'import_lines_blocked': lines_blocked,
                    'blockers': blockers, 'ready': not blockers}


# ---------------------------------------------------------------------------
# Verification readiness (installation-level, verifier-facing)
# ---------------------------------------------------------------------------

def verification_readiness(c, tid, installation_id):
    inst = c.execute('SELECT * FROM installations WHERE id=? AND tenant_id=?', (installation_id, tid)).fetchone()
    if not inst:
        return None
    ed = c.execute("SELECT * FROM emissions_data WHERE tenant_id=? AND installation_id=? AND status!='superseded' "
                    "ORDER BY id DESC LIMIT 1", (tid, installation_id)).fetchone()
    supplier_req_ok = c.execute("SELECT 1 FROM evidence_requirements WHERE tenant_id=? AND scope_type='supplier' "
                                  "AND scope_id=? AND name='Supplier declaration / upstream evidence' AND status='complete'",
                                  (tid, inst['supplier_id'])).fetchone() if inst['supplier_id'] else None
    activity_ok = c.execute("SELECT 1 FROM evidence_requirements WHERE tenant_id=? AND scope_type='installation' "
                              "AND scope_id=? AND name='Production quantity / activity data' AND status='complete'",
                              (tid, installation_id)).fetchone()
    verification_ok = c.execute("SELECT 1 FROM evidence_requirements WHERE tenant_id=? AND scope_type='installation' "
                                  "AND scope_id=? AND name='Verification report / verifier evidence' AND status='complete'",
                                  (tid, installation_id)).fetchone()
    open_conflict = c.execute("SELECT 1 FROM exceptions WHERE tenant_id=? AND affected_entity_type='installation' "
                                "AND affected_entity_id=? AND status NOT IN ('RESOLVED','ACCEPTED_WITH_RISK','WAIVED')",
                                (tid, installation_id)).fetchone()

    checklist = [
        ('Installation identified', bool(inst['name'] and inst['country']),
         'Name and country on file.' if (inst['name'] and inst['country']) else 'Country of the installation is not recorded.'),
        ('Production route documented', bool(inst['production_route']),
         inst['production_route'] or 'No production route / process recorded.'),
        ('Supplier declaration received', bool(supplier_req_ok),
         'On file.' if supplier_req_ok else 'No validated supplier declaration linked to this installation.'),
        ('Emissions data period-aligned', bool(ed and ed['status'] == 'validated'),
         'Validated emissions record on file.' if (ed and ed['status'] == 'validated') else 'No validated emissions_data record for this installation yet.'),
        ('Methodology recorded', bool(ed and ed['methodology_id']),
         'Methodology set.' if (ed and ed['methodology_id']) else 'No methodology has been recorded for the emissions figure.'),
        ('Activity data evidence present', bool(activity_ok),
         'On file.' if activity_ok else 'Production/activity data evidence requirement is still open.'),
        ('Emissions factor resolved without conflict', bool(ed and ed['direct_intensity']) and not open_conflict,
         'No open conflicts on this installation.' if not open_conflict else 'An open exception affects this installation -- resolve it before treating the factor as resolved.'),
    ]
    met = sum(1 for _, ok, _ in checklist if ok)
    score = round(100 * met / len(checklist))
    status = 'READY' if score >= 90 else ('PARTIAL' if score >= 50 else 'NOT_READY')
    future_item = ('Verifier report registered in the CBAM Registry', bool(verification_ok),
                    'On file.' if verification_ok else
                    'Not yet available system-wide: accredited verifiers register in the CBAM Registry from '
                    '1 Sep 2026 and the first verification reports can be issued there from Jan 2027 -- absence '
                    'here does not by itself block current-period evidence work.')
    c.execute('INSERT INTO verification_records(tenant_id,installation_id,readiness_score,checklist_json,status,computed_at) '
              'VALUES(?,?,?,?,?,?)', (tid, installation_id, score, json.dumps(checklist), status, util.now()))
    return {'installation': dict(inst), 'score': score, 'status': status, 'checklist': checklist, 'future_item': future_item}


# ---------------------------------------------------------------------------
# Regulatory rule engine
# ---------------------------------------------------------------------------

def latest_rule_set(c):
    return c.execute("SELECT * FROM rule_sets WHERE status='active' ORDER BY id DESC LIMIT 1").fetchone()


def lookup_default_value(c, rule_set_id, sector, cn_code, country='', production_route=''):
    """Choose the most specific available rule before any sector fallback.

    Exact CN/TARIC matches must outrank sector rows. If country/route metadata is
    supplied, prefer matching rows; never let an arbitrary first row win when
    multiple regulatory variants exist.
    """
    cn = ''.join(ch for ch in str(cn_code or '') if ch.isdigit())
    country_key = str(country or '').strip().casefold()
    route_key = str(production_route or '').strip().casefold()
    if cn:
        for length in (10, 8, 6, 4, 2):
            if len(cn) < length:
                continue
            rows = c.execute(
                'SELECT * FROM default_values WHERE rule_set_id=? AND cn_prefix=?',
                (rule_set_id, cn[:length])).fetchall()
            if rows:
                def rank(row):
                    rc = str(row['country'] or '').strip().casefold()
                    rr = str(row['production_route'] or '').strip().casefold()
                    # Exact country/route specificity wins; generic rows remain fallback.
                    return (int(bool(rc) and rc == country_key), int(bool(rr) and rr == route_key),
                            int(not rc), int(not rr), -int(row['id']))
                compatible = [r for r in rows if not r['country'] or not country_key or str(r['country']).strip().casefold() == country_key]
                compatible = [r for r in compatible if not r['production_route'] or not route_key or str(r['production_route']).strip().casefold() == route_key]
                if compatible:
                    return max(compatible, key=rank)
    if sector:
        rows = c.execute('SELECT * FROM default_values WHERE rule_set_id=? AND sector=?',
                          (rule_set_id, sector)).fetchall()
        compatible = [r for r in rows if (not r['country'] or not country_key or str(r['country']).strip().casefold() == country_key)
                      and (not r['production_route'] or not route_key or str(r['production_route']).strip().casefold() == route_key)]
        if compatible:
            return max(compatible, key=lambda r: (int(bool(r['country']) and str(r['country']).strip().casefold() == country_key),
                                                 int(bool(r['production_route']) and str(r['production_route']).strip().casefold() == route_key),
                                                 -int(r['id'])))
    if cn:
        ref = c.execute('SELECT sector FROM cn_reference WHERE code=?', (cn,)).fetchone()
        if ref and ref['sector'] != sector:
            return lookup_default_value(c, rule_set_id, ref['sector'], '', country, production_route)
    return None


def lookup_methodology(c, code):
    return c.execute('SELECT * FROM methodologies WHERE code=?', (code,)).fetchone()


def latest_certificate_price(c, rule_set_id):
    return c.execute('SELECT * FROM certificate_prices WHERE rule_set_id=? ORDER BY period DESC LIMIT 1', (rule_set_id,)).fetchone()


def certificate_price_for_period(c, rule_set_id, period):
    """Return the exact published price for a reporting/import quarter when known.
    Falls back to the latest published price only when the period is absent."""
    # If the caller names a period, only that period's published price is valid.
    # Falling back to the latest quarter for an unpublished future quarter would
    # silently price the wrong period. The caller handles latest-price fallback
    # only when no period was supplied at all.
    return c.execute('SELECT * FROM certificate_prices WHERE rule_set_id=? AND period=?', (rule_set_id, period)).fetchone()


def import_line_control_risk(c, tid, cid, line_id):
    """Evidence-control score, deliberately explainable rather than an opaque AI score.
    Starts at 100 and subtracts for missing evidence, unresolved conflicts, candidate facts,
    and default/manual calculation reliance. The score is a workflow priority signal, not
    a compliance probability."""
    sync_requirements(c, tid, cid)
    score = 100
    reasons = []
    missing = c.execute("SELECT name FROM evidence_requirements WHERE tenant_id=? AND case_id=? AND scope_type='import_line' AND scope_id=? AND status='missing' AND applicability!='not_applicable'", (tid,cid,line_id)).fetchall()
    if missing:
        score -= min(35, 10 + 5 * len(missing)); reasons.append(f'{len(missing)} missing line-level evidence item(s)')
    open_exc = c.execute("SELECT category,severity,title FROM exceptions WHERE tenant_id=? AND case_id=? AND affected_entity_type='import_line' AND affected_entity_id=? AND status NOT IN ('RESOLVED','ACCEPTED_WITH_RISK','WAIVED')", (tid,cid,line_id)).fetchall()
    high = sum(1 for e in open_exc if e['severity']=='high')
    if open_exc:
        score -= min(35, high*15 + (len(open_exc)-high)*6); reasons.append(f'{len(open_exc)} open exception(s)')
    candidates = c.execute("SELECT COUNT(*) n FROM facts WHERE tenant_id=? AND case_id=? AND import_line_id=? AND status='candidate'", (tid,cid,line_id)).fetchone()['n']
    if candidates:
        score -= min(20, 5*candidates); reasons.append(f'{candidates} extracted fact(s) awaiting review')
    calc = c.execute("SELECT result_json FROM calculation_runs WHERE tenant_id=? AND case_id=? AND import_line_id=? ORDER BY id DESC LIMIT 1", (tid,cid,line_id)).fetchone()
    if calc:
        r = json.loads(calc['result_json'])
        if r.get('uses_default_value'):
            score -= 10; reasons.append('calculation relies on regulatory default rather than validated installation data')
        if 'manual override' in (r.get('source') or '').lower():
            score -= 15; reasons.append('calculation uses manual override evidence')
    return max(0, score), reasons


def financial_sensitivity(result, prices=(Decimal('70'), Decimal('82.32'), Decimal('100'))):
    """Translate emissions uncertainty into euros at a small, explicit price band."""
    certs = util.num(result.get('indicative_certificate_equivalent') or '0')
    return [{'price_eur_per_tco2e': util.q(p), 'exposure_eur': util.q(certs*p)} for p in prices]


# ---------------------------------------------------------------------------
# Calculation engine
# ---------------------------------------------------------------------------

def compute_import_line_calculation(c, tid, uid, cid, line_id, form):
    """Deterministic, versioned, input-snapshotted per-import-line calculation.
    Resolution order for the emissions intensity input:
      1. A 'validated' emissions_data record for the line's installation (actual, reviewer-approved)
      2. The regulatory default value for the product's sector/CN code (flagged as such)
      3. A manual override supplied on the form (flagged as unvalidated manual input)
    Nothing here is submitted anywhere; it produces a SCENARIO_ONLY result that
    a human must review before it can inform an approval (see §15/§28).
    """
    line = c.execute('SELECT * FROM import_lines WHERE id=? AND tenant_id=? AND case_id=?', (line_id, tid, cid)).fetchone()
    if not line:
        return None, 'Import line not found'
    rs = latest_rule_set(c)

    def decimal_input(name, raw, default='0'):
        if isinstance(raw, (list, tuple)):
            raw = raw[0] if raw else None
        value = default if raw in (None, '') else str(raw).strip().replace(',', '')
        try:
            parsed = Decimal(value)
        except Exception:
            raise ValueError(f'{name} must be a valid decimal number')
        if not parsed.is_finite():
            raise ValueError(f'{name} must be finite')
        if abs(parsed) > Decimal('1000000000000'):
            raise ValueError(f'{name} exceeds the supported range')
        return parsed

    try:
        quantity = decimal_input('Quantity', form.get('quantity') or line['quantity'], '0')
        if quantity <= 0:
            return None, 'Quantity must be greater than zero; calculation was not created.'
        free = decimal_input('Free-allocation adjustment', form.get('free_allocation_adjustment', '0'))
        paid = decimal_input('Carbon-price credit', form.get('carbon_price_credit_eur', '0'))
        cert_input = decimal_input('Certificate price', form.get('certificate_price_eur', '0'))
        override_raw = form.get('specific_embedded_emissions')
        override = decimal_input('Manual emissions intensity', override_raw) if override_raw not in (None, '') else None
        if free < 0 or paid < 0 or cert_input < 0:
            return None, 'Free allocation, carbon-price credit, and certificate price cannot be negative.'
        if override is not None and override <= 0:
            return None, 'Manual emissions intensity must be greater than zero when supplied.'
    except ValueError as exc:
        return None, str(exc)

    methodology_used, direct, indirect, source_note = None, None, Decimal('0'), ''
    ed = None
    default = None
    default_total_intensity = None
    default_base_total_intensity = None
    default_markup_pct = None
    if line['installation_id']:
        ed = c.execute("SELECT * FROM emissions_data WHERE tenant_id=? AND installation_id=? AND status='validated' "
                        "ORDER BY id DESC LIMIT 1", (tid, line['installation_id'])).fetchone()
    if ed and ed['direct_intensity'] not in (None, ''):
        direct = util.num(ed['direct_intensity'])
        indirect = util.num(ed['indirect_intensity'] or '0')
        if not direct.is_finite() or not indirect.is_finite() or direct < 0 or indirect < 0:
            return None, 'Validated emissions record contains invalid/negative intensity; calculation blocked.'
        methodology_used = ed['methodology_id']
        source_note = f"Validated installation emissions_data #{ed['id']}"
    else:
        product = c.execute('SELECT * FROM products WHERE tenant_id=? AND cn_code=?', (tid, line['cn_code'])).fetchone()
        sector = product['sector'] if product else ''
        default = lookup_default_value(c, rs['id'], sector, line['cn_code'], line['origin_country'] or '', line['production_route'] or '') if rs else None
        if override is not None:
            direct = override
            methodology_used = lookup_methodology(c, 'ACTUAL_UNVERIFIED')
            methodology_used = methodology_used['id'] if methodology_used else None
            source_note = 'Manual override entered by reviewer -- not yet backed by validated evidence.'
        elif default:
            # Seeded/secondary/illustrative values are useful for development UI
            # only. Never let them produce a customer-facing calculation. A real
            # default must come from a hash-pinned official workbook import.
            if str(default['confidence'] or '').casefold() != 'official':
                return None, 'Applicable default is not from an imported official dataset. Calculation blocked; import and reconcile the current Commission workbook.'
            direct = util.num(default['direct_default'])
            indirect = util.num(default['indirect_default'] or '0')
            default_base_total_intensity = util.num(default['total_default'] or '')
            if not default_base_total_intensity.is_finite() or default_base_total_intensity <= 0:
                return None, 'Official default row has no valid total-emissions value. Calculation blocked.'
            # Determine the year from the selected import/reporting period, not
            # the current date. The legal markup applies to the total-emissions
            # value and is separate from the informational component columns.
            period_for_markup = form.get('period')
            if isinstance(period_for_markup, (list, tuple)):
                period_for_markup = period_for_markup[0] if period_for_markup else ''
            period_for_markup = str(period_for_markup or '').strip()
            if not period_for_markup and line['reporting_period_id']:
                pr_markup = c.execute('SELECT code FROM reporting_periods WHERE id=? AND tenant_id=?',
                                      (line['reporting_period_id'], tid)).fetchone()
                period_for_markup = str(pr_markup['code']) if pr_markup else ''
            if not period_for_markup:
                case_markup = c.execute('SELECT period FROM cases WHERE id=? AND tenant_id=?', (cid, tid)).fetchone()
                period_for_markup = str(case_markup['period'] or '') if case_markup else ''
            import re as _markup_re
            year_match = _markup_re.match(r'^(\d{4})', period_for_markup)
            if not year_match:
                return None, 'Reporting year is required to select the regulatory default-value markup. Calculation blocked.'
            markup_year = int(year_match.group(1))
            markup_row = c.execute('SELECT markup_pct FROM default_value_markups WHERE rule_set_id=? AND sector=? AND year=?',
                                   (rs['id'], default['sector'], markup_year)).fetchone()
            if not markup_row:
                return None, f'No versioned default-value markup exists for {default["sector"]}/{markup_year}. Calculation blocked.'
            default_markup_pct = util.num(markup_row['markup_pct'])
            if not default_markup_pct.is_finite() or default_markup_pct < 0:
                return None, 'Regulatory default-value markup is invalid. Calculation blocked.'
            default_total_intensity = calculate_marked_default_total(default_base_total_intensity, default_markup_pct)
            m = lookup_methodology(c, 'DEFAULT_VALUE')
            methodology_used = m['id'] if m else None
            source_note = f"Regulatory default value (rule set {rs['code']} v{rs['version']}): {default['markup_note']}"
        else:
            return None, 'No validated emissions data, applicable default value, or explicit manual intensity is available. Calculation blocked to prevent a false zero.'

    if direct is None or indirect is None or not direct.is_finite() or not indirect.is_finite() or direct < 0 or indirect < 0:
        return None, 'Emissions intensity is missing or invalid; calculation blocked.'
    # For official defaults, CBAM calculation uses the workbook's total-emissions
    # column exactly. Direct/indirect component columns are informational and must
    # not be summed to reconstruct the legally relevant total.
    intensity_for_calculation = default_total_intensity if default_total_intensity is not None and override is None and ed is None else (direct + indirect)
    gross = (quantity * intensity_for_calculation).quantize(Decimal('0.0001'))
    if free > gross:
        return None, 'Free-allocation adjustment exceeds gross embedded emissions; calculation blocked for review.'
    # Prefer the published price for the import/reporting quarter. Historical
    # runs must not silently inherit today's latest price when a period is known.
    period_raw = form.get('period')
    if isinstance(period_raw, (list, tuple)):
        period_raw = period_raw[0] if period_raw else ''
    period_key = str(period_raw or '').strip()
    if not period_key and line['reporting_period_id']:
        pr = c.execute('SELECT code FROM reporting_periods WHERE id=? AND tenant_id=?',
                       (line['reporting_period_id'], tid)).fetchone()
        period_key = str(pr['code']) if pr else ''
    if not period_key:
        case_row = c.execute('SELECT period FROM cases WHERE id=? AND tenant_id=?', (cid, tid)).fetchone()
        period_key = str(case_row['period'] or '') if case_row else ''
    import re as _re
    period_key = period_key if _re.fullmatch(r'\d{4}-Q[1-4]', period_key) else ''
    price_row = certificate_price_for_period(c, rs['id'], period_key) if rs and period_key else (latest_certificate_price(c, rs['id']) if rs else None)
    cert = cert_input or (util.num(price_row['price_eur']) if price_row else Decimal('0'))
    if cert <= 0:
        return None, 'No valid certificate price is available. Calculation blocked rather than reporting zero exposure.'
    net = max(Decimal('0'), gross - free)
    if paid > net * cert:
        return None, 'Carbon-price credit exceeds the scenario exposure; review the credit evidence and units.'
    certificate_equiv = max(Decimal('0'), net - (paid / cert)).quantize(Decimal('0.0001'))

    # Commercial control layer: make the cost of uncertainty visible. If a default is
    # being used, calculate the delta versus the validated/actual path when available.
    default_penalty = Decimal('0')
    if cert > 0 and default and default_total_intensity is not None and ed is None and override is not None and direct > 0:
        default_total = default_total_intensity if default_total_intensity is not None else util.num(default['total_default'] or '0')
        default_penalty = max(Decimal('0'), (quantity * default_total) - (quantity * direct)) * cert
    result = {
        'import_line_id': line_id, 'quantity_t': util.q(quantity),
        'direct_intensity_tco2e_per_t': util.q(direct), 'indirect_intensity_tco2e_per_t': util.q(indirect),
        'total_intensity_used_tco2e_per_t': util.q(intensity_for_calculation),
        'default_base_total_intensity_tco2e_per_t': util.q(default_base_total_intensity) if default_base_total_intensity is not None else None,
        'default_markup_pct': util.q(default_markup_pct) if default_markup_pct is not None else None,
        'gross_embedded_emissions_tco2e': util.q(gross), 'free_allocation_adjustment_tco2e': util.q(free),
        'net_after_free_allocation_tco2e': util.q(net), 'carbon_price_credit_eur': util.q(paid),
        'certificate_price_eur_per_tco2e': util.q(cert),
        'certificate_price_period_used': ('MANUAL_OVERRIDE' if cert_input > 0 else (period_key or (price_row['period'] if price_row else None))),
        'certificate_price_source': 'manual_override' if cert_input > 0 else 'published_rule_set_price',
        'indicative_certificate_equivalent': None if certificate_equiv is None else util.q(certificate_equiv),
        'certificate_exposure_eur': None if certificate_equiv is None else util.q(certificate_equiv * cert),
        'default_value_cost_delta_eur': util.q(default_penalty),
        'price_sensitivity': financial_sensitivity({'indicative_certificate_equivalent': certificate_equiv}) if certificate_equiv is not None else [],
        'source': source_note, 'uses_default_value': 'default' in source_note.lower(),
        'default_value_confidence': default['confidence'] if default and 'default' in source_note.lower() else None,
        'status': 'SCENARIO_ONLY',
        'note': 'Deterministic and versioned, but this build does not independently validate every sector-specific '
                'CBAM liability rule (free-allocation phase-out schedule and carbon-price-paid credit must be '
                'confirmed against the Regulation before this number informs a declaration).',
    }
    if ed and ed['direct_intensity'] not in (None, ''):
        emissions_source = {'type': 'validated_installation_data', 'record': dict(ed)}
    elif default and 'default' in source_note.lower():
        emissions_source = {'type': 'regulatory_default', 'record': dict(default)}
    elif override is not None:
        emissions_source = {'type': 'manual_override', 'value': util.q(override)}
    else:
        emissions_source = None
    snap = {
        'form': dict(form),
        'rule_set': dict(rs) if rs else None,
        'import_line': dict(line),
        'emissions_source': emissions_source,
        'certificate_price_record': dict(price_row) if price_row and cert_input == 0 else None,
        'certificate_price_manual_override': util.q(cert_input) if cert_input > 0 else None,
        'generated_at': util.now(),
    }
    c.execute('INSERT INTO calculation_runs(tenant_id,case_id,import_line_id,rule_set_id,methodology_id,run_type,'
              'created,created_by,input_snapshot,result_json) VALUES(?,?,?,?,?,?,?,?,?,?)',
              (tid, cid, line_id, rs['id'] if rs else None, methodology_used, 'import_line',
               util.now(), uid, json.dumps(snap, default=str), json.dumps(result)))
    c.execute("UPDATE import_lines SET status='calculated',updated=? WHERE id=?", (util.now(), line_id))
    return result, None


def compute_scenario(c, tid, uid, cid, form):
    """Validated case-level what-if scenario; never persists malformed inputs."""
    rs = latest_rule_set(c)
    def parse(name, raw, default='0'):
        if isinstance(raw, (list, tuple)):
            raw = raw[0] if raw else None
        value = default if raw in (None, '') else str(raw).strip().replace(',', '')
        try:
            d = Decimal(value)
        except Exception:
            raise ValueError(f'{name} must be a valid decimal number')
        if not d.is_finite() or abs(d) > Decimal('1000000000000'):
            raise ValueError(f'{name} must be finite and within the supported range')
        return d
    quantity = parse('Quantity', form.get('quantity'), '0')
    intensity = parse('Emissions intensity', form.get('specific_embedded_emissions'), '0')
    free = parse('Free-allocation adjustment', form.get('free_allocation_adjustment'), '0')
    paid = parse('Carbon-price credit', form.get('carbon_price_credit_eur'), '0')
    cert_input = parse('Certificate price', form.get('certificate_price_eur'), '0')
    if quantity <= 0 or intensity <= 0:
        raise ValueError('Scenario quantity and emissions intensity must both be greater than zero.')
    if min(free, paid, cert_input) < 0:
        raise ValueError('Free allocation, carbon-price credit, and certificate price cannot be negative.')
    gross = (quantity * intensity).quantize(Decimal('0.0001'))
    if free > gross:
        raise ValueError('Free-allocation adjustment exceeds gross embedded emissions.')
    case_row = c.execute('SELECT period FROM cases WHERE id=? AND tenant_id=?', (cid, tid)).fetchone()
    period_raw = form.get('period')
    if isinstance(period_raw, (list, tuple)):
        period_raw = period_raw[0] if period_raw else ''
    period_key = str(period_raw or (case_row['period'] if case_row else '')).strip()
    import re as _re
    period_key = period_key if _re.fullmatch(r'\d{4}-Q[1-4]', period_key) else ''
    price_row = certificate_price_for_period(c, rs['id'], period_key) if rs and period_key else (latest_certificate_price(c, rs['id']) if rs else None)
    cert = cert_input or (util.num(price_row['price_eur']) if price_row else Decimal('0'))
    if cert <= 0:
        raise ValueError('No valid certificate price is available; scenario was not saved.')
    net = max(Decimal('0'), gross - free)
    if paid > net * cert:
        raise ValueError('Carbon-price credit exceeds scenario exposure; review the evidence and units.')
    certificate_equiv = max(Decimal('0'), net - paid / cert).quantize(Decimal('0.0001'))
    result = {
        'quantity_t': util.q(quantity), 'specific_embedded_emissions_tco2e_per_t': util.q(intensity),
        'gross_embedded_emissions_tco2e': util.q(gross), 'free_allocation_adjustment_tco2e': util.q(free),
        'net_after_free_allocation_tco2e': util.q(net), 'carbon_price_credit_eur': util.q(paid),
        'certificate_price_eur_per_tco2e': util.q(cert),
        'certificate_price_period_used': ('MANUAL_OVERRIDE' if cert_input > 0 else (period_key or (price_row['period'] if price_row else None))),
        'certificate_price_source': 'manual_override' if cert_input > 0 else 'published_rule_set_price',
        'certificate_exposure_eur': util.q(certificate_equiv * cert),
        'indicative_certificate_equivalent': util.q(certificate_equiv),
        'status': 'SCENARIO_ONLY',
        'note': 'Ad hoc scenario, not tied to a specific import line or evidence record.',
    }
    snap = {'form': dict(form), 'rule_set': dict(rs) if rs else None, 'generated_at': util.now()}
    c.execute('INSERT INTO calculation_runs(tenant_id,case_id,rule_set_id,run_type,created,created_by,input_snapshot,result_json) '
              'VALUES(?,?,?,?,?,?,?,?)',
              (tid, cid, rs['id'] if rs else None, 'workbench', util.now(), uid, json.dumps(snap, default=str), json.dumps(result)))
    return result


def case_pack(c, tid, cid):
    case = c.execute('SELECT * FROM cases WHERE tenant_id=? AND id=?', (tid, cid)).fetchone()
    if not case:
        return None
    score, rd = readiness(c, tid, cid)
    tables = ['imports', 'import_lines', 'documents', 'facts', 'suppliers', 'installations', 'products',
              'evidence', 'evidence_requirements', 'exceptions', 'supplier_requests', 'emissions_data',
              'calculation_runs', 'verification_records', 'approvals']
    pack = {'schema_version': '2.0', 'generated_at': util.now(), 'case': dict(case), 'readiness': {'score': score, **rd}}
    for tbl in tables:
        col = 'tenant_id=? AND case_id=?' if tbl not in ('suppliers', 'installations', 'products', 'verification_records') else 'tenant_id=?'
        args = (tid, cid) if 'case_id=?' in col else (tid,)
        try:
            pack[tbl] = [dict(r) for r in c.execute(f'SELECT * FROM {tbl} WHERE {col}', args).fetchall()]
        except Exception:
            pack[tbl] = []
    return pack


def generate_declaration_package(c, tid, cid, uid):
    pack = case_pack(c, tid, cid)
    if pack is None:
        return None
    manifest = json.dumps(pack, indent=2, default=str, sort_keys=True)
    digest = util.sha256_text(manifest)
    c.execute('INSERT INTO declaration_packages(tenant_id,case_id,generated_at,generated_by,manifest_json,sha256,status) '
              'VALUES(?,?,?,?,?,?,?)', (tid, cid, util.now(), uid, manifest, digest, 'draft'))
    pkg_id = c.execute('SELECT last_insert_rowid()').fetchone()[0]
    audit(c, tid, cid, uid, 'declaration_package_generated', f'id={pkg_id} sha256={digest}')
    return pkg_id, digest, pack
