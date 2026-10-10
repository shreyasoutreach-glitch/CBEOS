"""Routing layer. Every handler here is responsible for:
  1. Resolving the authenticated actor (never trusting client-supplied tenant/user ids)
  2. Checking CSRF on every state-changing POST
  3. Checking RBAC permission for the action
  4. Scoping every query by the actor's tenant_id
No view or engine function is ever called with a tenant_id that didn't come
from require(h)/actor(h). This is the property tests/test_security.py checks
adversarially (cross-tenant IDOR, forged CSRF, path traversal on downloads).
"""
import json
import mimetypes
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import db as dbm
from . import engine
from . import agents
from . import integrations
from . import extraction
from . import security
from . import supplier_ops
from . import util
from . import views
from . import ops_readiness
from . import recovery_report

HOST = os.getenv('CBAM_HOST', '127.0.0.1')
PORT = int(os.getenv('CBAM_PORT') or os.getenv('PORT', '8000'))


def fv(f, k, d=''):
    return f.get(k, [d])[0]


MAX_FORM_BYTES = int(os.getenv('CBAM_MAX_FORM_BYTES', str(1024 * 1024)))

def parse_form(h):
    raw_length = h.headers.get('Content-Length')
    if raw_length is None:
        raise ValueError('Content-Length is required')
    try:
        n = int(raw_length)
    except (TypeError, ValueError):
        raise ValueError('Invalid Content-Length')
    if n < 0 or n > MAX_FORM_BYTES:
        raise ValueError('Form body exceeds configured size limit')
    raw = h.rfile.read(n)
    if len(raw) != n:
        raise ValueError('Incomplete form body')
    try:
        return parse_qs(raw.decode('utf-8', 'strict'), max_num_fields=2000)
    except (UnicodeDecodeError, ValueError):
        raise ValueError('Malformed form body')


def multipart(h):
    """Parse multipart/form-data without splitting binary payloads on boundary bytes."""
    from email.parser import BytesParser
    from email.policy import default as email_policy
    n = int(h.headers.get('Content-Length', '0'))
    if n <= 0:
        raise ValueError('Request body is empty')
    if n > security.MAX_UPLOAD + 1024 * 1024:
        raise ValueError('Upload request exceeds configured size limit')
    raw = h.rfile.read(n)
    ct = h.headers.get('Content-Type', '')
    if not ct.lower().startswith('multipart/form-data') or 'boundary=' not in ct.lower():
        raise ValueError('multipart boundary missing')
    message = BytesParser(policy=email_policy).parsebytes(
        b'Content-Type: ' + ct.encode('latin-1', 'replace') + b'\r\nMIME-Version: 1.0\r\n\r\n' + raw)
    if not message.is_multipart():
        raise ValueError('Malformed multipart request')
    fields, fname, data = {}, None, None
    total_file_bytes = 0
    for part in message.iter_parts():
        name = part.get_param('name', header='content-disposition')
        if not name:
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b''
        if filename is not None:
            total_file_bytes += len(payload)
            if total_file_bytes > security.MAX_UPLOAD:
                raise ValueError('Upload exceeds configured size limit')
            # This endpoint intentionally accepts one file; multiple file parts are rejected.
            if fname is not None:
                raise ValueError('Only one file may be uploaded per request')
            fname = os.path.basename(filename.replace('\\', '/'))
            data = payload
        else:
            charset = part.get_content_charset() or 'utf-8'
            fields.setdefault(name, [payload.decode(charset, 'replace')])
    return fields, fname, data


def require_perm(a, perm):
    return security.require_permission(a['role'], perm)


def do_upload(h):
    c = None
    stored_path = None
    a = require(h)
    if not a:
        return
    try:
        f, fn, data = multipart(h)
        if not fn or data is None:
            return h.send('No file', 400)
        if not h.csrf_ok(f, a):
            return h.send('CSRF validation failed', 403)
        if not require_perm(a, 'upload'):
            return h.send('Forbidden: your role cannot upload documents', 403)
        cid = int(fv(f, 'case_id'))
        tid = a['tenant_id']
        c = dbm.db()
        case = c.execute('SELECT id FROM cases WHERE id=? AND tenant_id=?', (cid, tid)).fetchone()
        if not case:
            c.close()
            return h.send('Case not found', 404)
        ok, reason = security.scan_upload(fn, data)
        if not ok:
            c.close()
            return h.send('Upload rejected: ' + util.esc(reason), 415)
        sha = util.sha256_bytes(data)
        dup = c.execute('SELECT id FROM documents WHERE case_id=? AND sha256=?', (cid, sha)).fetchone()
        if dup:
            c.close()
            return h.redirect('/case/%s' % cid)
        # Validate every user-supplied association BEFORE touching persistent file
        # storage. Returning from an association error after writing the file used
        # to leave orphaned client data in uploads/ with no database record.
        line_id = int(fv(f, 'import_line_id')) if fv(f, 'import_line_id') else None
        installation_id = int(fv(f, 'installation_id')) if fv(f, 'installation_id') else None
        supplier_id = None
        if line_id:
            row = c.execute('SELECT supplier_id,installation_id,case_id FROM import_lines WHERE id=? AND tenant_id=?', (line_id, tid)).fetchone()
            if not row or row['case_id'] != cid:
                c.close()
                return h.send('Import line does not belong to this case', 400)
            supplier_id = row['supplier_id']
            installation_id = installation_id or row['installation_id']
        if installation_id:
            inst = c.execute('SELECT id,supplier_id FROM installations WHERE id=? AND tenant_id=?',
                             (installation_id, tid)).fetchone()
            if not inst:
                c.close()
                return h.send('Installation not found in this tenant', 400)
            if supplier_id and inst['supplier_id'] not in (None, supplier_id):
                c.close()
                return h.send('Installation and supplier do not match', 400)
        text, meta = extraction.extract_file(fn, data)
        doc_type_guess, conf = extraction.classify(fn, text)
        stored = f'{sha}{os.path.splitext(fn)[1].lower()}'
        path = os.path.join(dbm.UP, stored)
        stored_path = path
        with open(path, 'wb') as fh:
            fh.write(data)
        t = util.now()
        mime = mimetypes.guess_type(fn)[0] or 'application/octet-stream'
        meta['classification'] = {'suggested_type': doc_type_guess, 'confidence': conf}
        c.execute('INSERT INTO documents(tenant_id,case_id,import_line_id,supplier_id,installation_id,filename,'
                   'stored_name,mime,doc_type,size_bytes,sha256,uploaded,uploaded_by,extracted_text,meta_json) '
                   'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (tid, cid, line_id, supplier_id, installation_id, fn, stored, mime, fv(f, 'doc_type', 'other'),
                    len(data), sha, t, a['user_id'], text, json.dumps(meta)))
        did = c.execute('SELECT last_insert_rowid()').fetchone()[0]
        found = extraction.infer_facts(text, meta)
        for field, val, unit, loc, excerpt, confidence in found:
            numeric = util.q(util.num(val)) if field in ('eu_tonnes', 'direct_intensity', 'indirect_intensity') else ''
            c.execute('INSERT INTO facts(tenant_id,case_id,document_id,import_line_id,supplier_id,installation_id,'
                       'field,value,numeric_value,unit,location,source_excerpt,confidence,status,created,updated) '
                       'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (tid, cid, did, line_id, supplier_id, installation_id, field, val, numeric, unit, loc, excerpt,
                        confidence, 'candidate', t, t))
        engine.run_reconciliation(c, tid, cid, a['user_id'])
        engine.audit(c, tid, cid, a['user_id'], 'document_uploaded', f'{fn} sha256={sha} type~{doc_type_guess}({conf})')
        c.commit()
        c.close()
        return h.redirect('/case/%s' % cid)
    except ValueError as e:
        import logging
        logging.getLogger('cbeos.upload').info('Upload rejected: %s', str(e))
        if c is not None:
            try: c.rollback(); c.close()
            except Exception: pass
        if stored_path and os.path.exists(stored_path):
            try: os.remove(stored_path)
            except OSError: pass
        return h.send('Upload rejected. Check the file format, size, and case associations.', 400)
    except Exception:
        import logging
        logging.getLogger('cbeos.upload').exception('Upload processing failed')
        if c is not None:
            try: c.rollback(); c.close()
            except Exception: pass
        if stored_path and os.path.exists(stored_path):
            try: os.remove(stored_path)
            except OSError: pass
        return h.send('Upload failed due to an internal processing error. No result was committed.', 500)


def do_download(h, did):
    a = require(h)
    if not a:
        return
    c = dbm.db()
    d = c.execute('SELECT * FROM documents WHERE id=? AND tenant_id=?', (did, a['tenant_id'])).fetchone()
    c.close()
    if not d:
        return h.send('Not found', 404)
    # stored_name is always sha256+ext (never derived from client-controlled path input)
    path = os.path.join(dbm.UP, d['stored_name'])
    safe_root = os.path.realpath(dbm.UP)
    real_path = os.path.realpath(path)
    if not real_path.startswith(safe_root + os.sep):
        return h.send('Invalid path', 400)
    if not os.path.exists(real_path):
        return h.send('File missing from storage', 404)
    with open(real_path, 'rb') as fh:
        data = fh.read()
    h.send_response(200)
    h.send_header('Content-Type', d['mime'] or 'application/octet-stream')
    h.send_header('Content-Disposition', f'attachment; filename="{re.sub(r"[^A-Za-z0-9._-]", "_", d["filename"])}"')
    h.send_header('Content-Length', str(len(data)))
    h.send_header('X-Content-Type-Options', 'nosniff')
    h.end_headers()
    h.wfile.write(data)


def actor(h):
    sid = h.cookies.get(security.SESSION_COOKIE).value if h.cookies.get(security.SESSION_COOKIE) else ''
    return security.actor_from_session_id(sid)


def require(h):
    a = actor(h)
    if not a:
        h.redirect('/login')
        return None
    return a


def handle_post(h, path):
    a = require(h)
    if not a:
        return
    f = parse_form(h)
    tid, uid = a['tenant_id'], a['user_id']
    c = dbm.db()
    if not h.csrf_ok(f, a):
        c.close()
        return h.send('CSRF validation failed', 403)
    try:
        m = re.match(r'^/case/(\d+)/import/create$', path)
        if m:
            cid = int(m.group(1))
            case = c.execute('SELECT id FROM cases WHERE id=? AND tenant_id=?', (cid, tid)).fetchone()
            if not case:
                return h.send('Not found', 404)
            engine.create_import(c, tid, cid, fv(f, 'reference'), fv(f, 'mode', 'sea'), fv(f, 'arrival_date'))
            engine.audit(c, tid, cid, uid, 'import_created', fv(f, 'reference'))
            c.commit()
            return h.redirect('/case/%s' % cid)

        m = re.match(r'^/case/(\d+)/agents/run$', path)
        if m:
            if not require_perm(a, 'manage_evidence'):
                return h.send('Forbidden', 403)
            cid = int(m.group(1))
            case = c.execute('SELECT id FROM cases WHERE id=? AND tenant_id=?', (cid, tid)).fetchone()
            if not case:
                return h.send('Not found', 404)
            agents.run_case_workflow(c, tid, cid, uid)
            c.commit()
            return h.redirect(f'/case/{cid}/agents')

        if path == '/case/create':
            t = util.now()
            c.execute('INSERT INTO cases(tenant_id,company,case_name,period,sector,status,created,updated,notes) '
                       'VALUES(?,?,?,?,?,?,?,?,?)',
                       (tid, fv(f, 'company'), fv(f, 'case_name'), fv(f, 'period'), fv(f, 'sector'), 'working', t, t, fv(f, 'notes')))
            cid = c.execute('SELECT last_insert_rowid()').fetchone()[0]
            engine.create_reporting_period(c, tid, fv(f, 'period'))
            engine.sync_requirements(c, tid, cid)
            engine.audit(c, tid, cid, uid, 'case_created', fv(f, 'case_name'))
            c.commit()
            return h.redirect('/case/%s' % cid)

        if path == '/line/create':
            cid = int(fv(f, 'case_id'))
            case = c.execute('SELECT id FROM cases WHERE id=? AND tenant_id=?', (cid, tid)).fetchone()
            if not case:
                return h.send('Not found', 404)
            product_id = None
            cn_code = fv(f, 'cn_code').strip()
            if cn_code:
                product_id = engine.create_product(c, tid, cn_code)
            lid = engine.create_import_line(
                c, tid, cid,
                import_id=int(fv(f, 'import_id')) if fv(f, 'import_id') else None,
                product_id=product_id, cn_code=cn_code,
                supplier_id=int(fv(f, 'supplier_id')) if fv(f, 'supplier_id') else None,
                installation_id=int(fv(f, 'installation_id')) if fv(f, 'installation_id') else None,
                invoice_ref=fv(f, 'invoice_ref'), origin_country=fv(f, 'origin_country'),
                quantity=fv(f, 'quantity', '0'), quantity_unit='t')
            engine.sync_requirements(c, tid, cid)
            engine.audit(c, tid, cid, uid, 'import_line_created', f'#{lid} {cn_code}')
            c.commit()
            return h.redirect('/case/%s' % cid)

        if path == '/fact/verify' or path == '/fact/reject':
            if not require_perm(a, 'review_fact'):
                return h.send('Forbidden', 403)
            fid = int(fv(f, 'id'))
            row = c.execute('SELECT * FROM facts WHERE id=? AND tenant_id=?', (fid, tid)).fetchone()
            if not row:
                return h.send('Not found', 404)
            status = 'verified' if path.endswith('verify') else 'rejected'
            c.execute('UPDATE facts SET status=?,verified_by=?,verified_at=?,updated=? WHERE id=?',
                       (status, uid, util.now(), util.now(), fid))
            engine.audit(c, tid, row['case_id'], uid, 'fact_' + status, str(fid))
            engine.run_reconciliation(c, tid, row['case_id'], uid)
            c.commit()
            return h.redirect('/case/%s' % row['case_id'])

        if path == '/evidence/add':
            if not require_perm(a, 'manage_evidence'):
                return h.send('Forbidden', 403)
            cid = int(fv(f, 'case_id'))
            t = util.now()
            scope_type = fv(f, 'scope_type', 'case')
            scope_id = int(fv(f, 'scope_id')) if fv(f, 'scope_id') else 0
            c.execute('INSERT INTO evidence(tenant_id,case_id,name,category,status,scope_type,scope_id,owner,source,'
                       'note,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (tid, cid, fv(f, 'name'), fv(f, 'category'), 'complete', scope_type, scope_id, '', fv(f, 'source'), fv(f, 'note'), t))
            engine.audit(c, tid, cid, uid, 'evidence_added', fv(f, 'name'))
            engine.run_reconciliation(c, tid, cid, uid)
            c.commit()
            return h.redirect('/case/%s' % cid)

        if path == '/calculate':
            if not require_perm(a, 'run_calculation'):
                return h.send('Forbidden', 403)
            cid = int(fv(f, 'case_id'))
            engine.compute_scenario(c, tid, uid, cid, f)
            engine.audit(c, tid, cid, uid, 'scenario_calculation_run', 'workbench')
            c.commit()
            return h.redirect('/case/%s' % cid)

        m = re.match(r'^/line/(\d+)/calculate$', path)
        if m:
            if not require_perm(a, 'run_calculation'):
                return h.send('Forbidden', 403)
            lid = int(m.group(1))
            line = c.execute('SELECT case_id FROM import_lines WHERE id=? AND tenant_id=?', (lid, tid)).fetchone()
            if not line:
                return h.send('Not found', 404)
            result, err = engine.compute_import_line_calculation(c, tid, uid, line['case_id'], lid, f)
            if err:
                return h.send(util.esc(err), 400)
            engine.audit(c, tid, line['case_id'], uid, 'import_line_calculation_run', str(lid))
            c.commit()
            return h.redirect('/line/%s' % lid)

        if path == '/supplier/create':
            if not require_perm(a, 'manage_suppliers'):
                return h.send('Forbidden', 403)
            engine.create_supplier(c, tid, fv(f, 'name'), fv(f, 'country'), contact_email=fv(f, 'contact_email'))
            engine.audit(c, tid, None, uid, 'supplier_created', fv(f, 'name'))
            c.commit()
            return h.redirect('/suppliers')

        m = re.match(r'^/supplier/(\d+)/generate_requests$', path)
        if m:
            if not require_perm(a, 'manage_suppliers'):
                return h.send('Forbidden', 403)
            sid = int(m.group(1))
            cid = int(fv(f, 'case_id'))
            n = supplier_ops.generate_requests_for_supplier(c, tid, cid, sid, uid, fv(f, 'deadline'))
            c.commit()
            return h.redirect(f'/supplier/{sid}')

        m = re.match(r'^/supplier_request/(\d+)/send$', path)
        if m:
            if not require_perm(a, 'manage_suppliers'):
                return h.send('Forbidden', 403)
            rid = int(m.group(1))
            sent, message = supplier_ops.send_request(c, tid, rid, uid)
            r = c.execute('SELECT supplier_id FROM supplier_requests WHERE id=? AND tenant_id=?', (rid, tid)).fetchone()
            c.commit()
            if not r:
                return h.send('Supplier request not found', 404)
            # Show the provider outcome explicitly. A redirect alone hid failures and
            # could make an unconfigured transport look like a successful send.
            status = 200 if sent else 409
            return h.send(
                '<!doctype html><html><head><meta charset="utf-8"><title>Supplier request status</title></head>'
                '<body><main><h1>Supplier request status</h1><p>' + util.esc(message) +
                '</p><p><a href="/supplier/' + str(r["supplier_id"]) + '">Return to supplier</a></p></main></body></html>',
                status,
            )

        m = re.match(r'^/supplier_request/(\d+)/respond$', path)
        if m:
            if not require_perm(a, 'manage_suppliers'):
                return h.send('Forbidden', 403)
            rid = int(m.group(1))
            supplier_ops.mark_responded(c, tid, rid, uid, validated=fv(f, 'validated') == '1')
            if fv(f, 'validated') == '1':
                req = c.execute('SELECT * FROM supplier_requests WHERE id=?', (rid,)).fetchone()
                sid = req['supplier_id']
                for inst in c.execute('SELECT id FROM installations WHERE tenant_id=? AND supplier_id=?', (tid, sid)).fetchall():
                    c.execute("INSERT INTO evidence(tenant_id,case_id,name,category,status,scope_type,scope_id,source,updated) "
                               "VALUES(?,?,?,?,?,?,?,?,?)",
                               (tid, req['case_id'], req['requirement_name'], 'supplier', 'complete', 'installation', inst['id'], 'supplier_response', util.now()))
                engine.run_reconciliation(c, tid, req['case_id'], uid)
            r = c.execute('SELECT supplier_id FROM supplier_requests WHERE id=?', (rid,)).fetchone()
            c.commit()
            return h.redirect(f'/supplier/{r["supplier_id"]}')

        if path == '/installation/create':
            if not require_perm(a, 'manage_suppliers'):
                return h.send('Forbidden', 403)
            sid = int(fv(f, 'supplier_id')) if fv(f, 'supplier_id') else None
            iid = engine.create_installation(c, tid, sid, fv(f, 'name'), fv(f, 'country'), fv(f, 'production_route'))
            engine.audit(c, tid, None, uid, 'installation_created', fv(f, 'name'))
            c.commit()
            return h.redirect(f'/supplier/{sid}' if sid else '/installations')

        m = re.match(r'^/installation/(\d+)/emissions/add$', path)
        if m:
            if not require_perm(a, 'manage_suppliers'):
                return h.send('Forbidden', 403)
            iid = int(m.group(1))
            inst = c.execute('SELECT * FROM installations WHERE id=? AND tenant_id=?', (iid, tid)).fetchone()
            if not inst:
                return h.send('Not found', 404)
            t = util.now()
            c.execute('INSERT INTO emissions_data(tenant_id,installation_id,methodology_id,direct_intensity,'
                       'indirect_intensity,status,created,updated) VALUES(?,?,?,?,?,?,?,?)',
                       (tid, iid, int(fv(f, 'methodology_id')) if fv(f, 'methodology_id') else None,
                        fv(f, 'direct_intensity'), fv(f, 'indirect_intensity', '0'), fv(f, 'status', 'candidate'), t, t))
            engine.audit(c, tid, None, uid, 'emissions_data_recorded', f'installation={iid}')
            c.commit()
            return h.redirect(f'/installation/{iid}')

        if path == '/exception/transition':
            eid = int(fv(f, 'id'))
            new_status = fv(f, 'status')
            if new_status in ('ACCEPTED_WITH_RISK', 'WAIVED') and not require_perm(a, 'waive_exception'):
                return h.send('Forbidden: accepting risk or waiving requires manager role', 403)
            if not require_perm(a, 'manage_exceptions'):
                return h.send('Forbidden', 403)
            ok, err = engine.transition_exception(c, tid, eid, uid, new_status, fv(f, 'resolution'), fv(f, 'owner'), fv(f, 'deadline'))
            if not ok:
                return h.send(util.esc(err), 400)
            c.commit()
            return h.redirect('/exceptions')

        if path == '/approve':
            if not require_perm(a, 'approve_case'):
                return h.send('Forbidden', 403)
            cid = int(fv(f, 'case_id'))
            sc, rd = engine.readiness(c, tid, cid)
            if not rd['ready']:
                return h.send('Approval blocked: ' + util.esc('; '.join(rd['blockers'])), 409)
            c.execute("INSERT INTO approvals(tenant_id,case_id,decision,comment,created,actor_id) VALUES(?,?,?,?,?,?)",
                       (tid, cid, 'approved', 'Human reviewer approved operational evidence readiness.', util.now(), uid))
            c.execute("UPDATE cases SET status='approved',approved_at=?,updated=? WHERE id=? AND tenant_id=?",
                       (util.now(), util.now(), cid, tid))
            engine.audit(c, tid, cid, uid, 'case_approved', 'operational evidence readiness')
            c.commit()
            return h.redirect('/case/%s' % cid)

        m = re.match(r'^/case/(\d+)/declaration/generate$', path)
        if m:
            if not require_perm(a, 'generate_declaration'):
                return h.send('Forbidden', 403)
            cid = int(m.group(1))
            case = c.execute('SELECT id FROM cases WHERE id=? AND tenant_id=?', (cid, tid)).fetchone()
            if not case:
                return h.send('Not found', 404)
            engine.generate_declaration_package(c, tid, cid, uid)
            c.commit()
            return h.redirect(f'/case/{cid}/declaration')

        if path == '/settings/user/create':
            if not require_perm(a, 'manage_users'):
                return h.send('Forbidden', 403)
            email = fv(f, 'email').strip().lower()
            c.execute('INSERT INTO users(tenant_id,email,password_hash,role,created) VALUES(?,?,?,?,?)',
                       (tid, email, security.password_hash(fv(f, 'password')), fv(f, 'role', 'viewer'), util.now()))
            engine.audit(c, tid, None, uid, 'user_created', f'{email}:{fv(f, "role")}')
            c.commit()
            return h.redirect('/settings')

        return h.send('Not found', 404)
    except ValueError as e:
        c.rollback()
        return h.send('Request rejected: ' + util.esc(str(e)), 400)
    except Exception:
        import logging
        c.rollback()
        logging.getLogger('cbeos.http').exception('Unhandled POST route error')
        return h.send('Internal server error.', 500)
    finally:
        c.close()


class Handler(BaseHTTPRequestHandler):
    # Avoid disclosing framework/product version through the Server response header.
    server_version = 'CBEOS'
    sys_version = ''

    def log_message(self, *a):
        pass

    def send(self, body, code=200, ctype='text/html'):
        b = body.encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype + '; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        self.send_header('Content-Security-Policy', "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'")
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(b)

    def redirect(self, p):
        self.send_response(303)
        self.send_header('Location', p)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.end_headers()

    def session_csrf(self):
        sid = self.cookies.get(security.SESSION_COOKIE).value if self.cookies.get(security.SESSION_COOKIE) else ''
        if not sid:
            return ''
        c = dbm.db()
        r = c.execute('SELECT csrf FROM sessions WHERE id=? AND expires>?', (sid, util.now())).fetchone()
        c.close()
        return r['csrf'] if r else ''

    def csrf_ok(self, f, a):
        origin_ok = self.headers.get('Origin', '') in ('', 'http://' + self.headers.get('Host', ''), 'https://' + self.headers.get('Host', ''))
        return bool(a and origin_ok and security.csrf_ok(self.session_csrf(), fv(f, 'csrf')))

    def do_GET(self):
        self.cookies = security.parse_cookies(self.headers.get('Cookie', ''))
        try:
            path = urlparse(self.path).path
            # Public liveness probe deliberately reveals no build, version, host,
            # or timestamp details. Readiness verifies the database dependency but
            # returns only a generic failure body to avoid leaking internals.
            if path in ('/health', '/healthz'):
                return self.send(json.dumps({'ok': True}), ctype='application/json')
            if path == '/readyz':
                probe = None
                try:
                    probe = dbm.db()
                    probe.execute('SELECT 1').fetchone()
                    required = {'tenants', 'users', 'cases', 'documents', 'exceptions'}
                    present = {row['name'] for row in probe.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                    if not required.issubset(present):
                        raise RuntimeError('Required schema is missing')
                    blockers = ops_readiness.production_blockers()
                    if os.getenv('CBAM_CUSTOMER_DATA_MODE', 'sandbox').strip().lower() == 'production' and blockers:
                        return self.send(json.dumps({'ready': False, 'mode': 'production', 'blockers': blockers}), 503, ctype='application/json')
                    return self.send(json.dumps({'ready': True}), ctype='application/json')
                except Exception:
                    import logging
                    logging.getLogger('cbeos.health').exception('Readiness probe failed')
                    return self.send(json.dumps({'ready': False}), 503, ctype='application/json')
                finally:
                    if probe is not None:
                        probe.close()
            if path == '/login':
                return self.send(views.login_page())
            if path == '/logout':
                sid = self.cookies.get(security.SESSION_COOKIE).value if self.cookies.get(security.SESSION_COOKIE) else ''
                c = dbm.db()
                c.execute('DELETE FROM sessions WHERE id=?', (sid,))
                c.commit()
                c.close()
                return self.redirect('/login')

            a = require(self)
            if not a:
                return
            c = dbm.db()
            try:
                if path == '/api/integrations/probe':
                    if not require_perm(a, 'manage_users'):
                        return self.send('Forbidden', 403)
                    # This is an explicit admin action. It performs bounded GET
                    # probes only: no email is sent and no provider payload is returned.
                    result = {
                        'configuration': integrations.status_snapshot(),
                        'live_probe': integrations.probe_external_integrations(timeout=6.0),
                    }
                    return self.send(json.dumps(result, ensure_ascii=False), ctype='application/json')
                if path == '/api/integrations':
                    return self.send(json.dumps(integrations.status_snapshot(), ensure_ascii=False), ctype='application/json')
                if path == '/':
                    return self.send(views.dashboard(c, a))
                if path == '/cases':
                    return self.send(views.case_list(c, a))
                if path == '/agents':
                    return self.send(views.agents_home(c, a))
                agent_match = re.match(r'^/case/(\d+)/agents$', path)
                if agent_match:
                    cid = int(agent_match.group(1))
                    case = c.execute('SELECT * FROM cases WHERE tenant_id=? AND id=?', (a['tenant_id'], cid)).fetchone()
                    if not case:
                        return self.send('Not found', 404)
                    return self.send(views.agent_case_terminal(c, a, case, self.session_csrf()))
                if path == '/case/new':
                    return self.send(views.case_form(a, self.session_csrf()))
                if path == '/suppliers':
                    return self.send(views.suppliers_list(c, a, self.session_csrf()))
                if path == '/installations':
                    return self.send(views.installations_list(c, a))
                if path == '/exceptions':
                    return self.send(views.exceptions_queue(c, a, self.session_csrf()))
                if path == '/verification':
                    return self.send(views.verification_overview(c, a))
                if path == '/audit':
                    return self.send(views.audit_view(c, a))
                if path == '/sources':
                    return self.send(views.sources_view(c, a))
                if path == '/settings':
                    if not require_perm(a, 'manage_users'):
                        return self.send('Forbidden', 403)
                    return self.send(views.settings_view(c, a, self.session_csrf()))

                m = re.match(r'^/document/(\d+)/download$', path)
                if m:
                    return do_download(self, int(m.group(1)))

                m = re.match(r'^/supplier/(\d+)$', path)
                if m:
                    s = c.execute('SELECT * FROM suppliers WHERE id=? AND tenant_id=?', (int(m.group(1)), a['tenant_id'])).fetchone()
                    if not s:
                        return self.send('Not found', 404)
                    return self.send(views.supplier_detail(c, a, s, self.session_csrf()))

                m = re.match(r'^/installation/(\d+)$', path)
                if m:
                    i = c.execute('SELECT * FROM installations WHERE id=? AND tenant_id=?', (int(m.group(1)), a['tenant_id'])).fetchone()
                    if not i:
                        return self.send('Not found', 404)
                    return self.send(views.installation_detail(c, a, i, self.session_csrf()))

                m = re.match(r'^/line/(\d+)$', path)
                if m:
                    line = c.execute('SELECT * FROM import_lines WHERE id=? AND tenant_id=?', (int(m.group(1)), a['tenant_id'])).fetchone()
                    if not line:
                        return self.send('Not found', 404)
                    return self.send(views.import_line_detail(c, a, line, self.session_csrf()))

                report_match = re.match(r'^/case/(\d+)/recovery-report\.xlsx$', path)
                if report_match:
                    cid = int(report_match.group(1))
                    report = recovery_report.build_recovery_workbook(c, a['tenant_id'], cid)
                    if report is None:
                        return self.send('Not found', 404)
                    engine.audit(c, a['tenant_id'], cid, a['user_id'], 'recovery_workbook_exported', f'case_id={cid}; workbook_version=1')
                    c.commit()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    self.send_header('Content-Disposition', f'attachment; filename="cbeos-recovery-case-{cid}.xlsx"')
                    self.send_header('Content-Length', str(len(report)))
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self.send_header('X-Frame-Options', 'DENY')
                    self.send_header('Referrer-Policy', 'no-referrer')
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    self.wfile.write(report)
                    return

                m = re.match(r'^/case/(\d+)(/pack|/declaration)?$', path)
                if m:
                    cid = int(m.group(1))
                    case = c.execute('SELECT * FROM cases WHERE tenant_id=? AND id=?', (a['tenant_id'], cid)).fetchone()
                    if not case:
                        return self.send('Not found', 404)
                    if m.group(2) == '/pack':
                        pack = engine.case_pack(c, a['tenant_id'], cid)
                        return self.send(json.dumps(pack, indent=2, default=str), ctype='application/json')
                    if m.group(2) == '/declaration':
                        return self.send(views.declaration_view(c, a, case, self.session_csrf()))
                    engine.sync_requirements(c, a['tenant_id'], cid)
                    engine.run_reconciliation(c, a['tenant_id'], cid, a['user_id'])
                    c.commit()
                    return self.send(views.case_detail(c, a, case, self.session_csrf()))
                return self.send('Not found', 404)
            finally:
                c.close()
        except Exception:
            import logging
            logging.getLogger('cbeos.http').exception('Unhandled GET handler error')
            return self.send('Internal server error.', 500)

    def do_POST(self):
        self.cookies = security.parse_cookies(self.headers.get('Cookie', ''))
        path = urlparse(self.path).path
        if path == '/login':
            try:
                f = parse_form(self)
            except ValueError:
                return self.send('Invalid or oversized request body.', 400)
            origin = self.headers.get('Origin', '')
            host = self.headers.get('Host', '')
            if origin and origin not in ('http://' + host, 'https://' + host):
                return self.send('Cross-origin login request rejected.', 403)
            email = fv(f, 'email').strip().lower()
            pw = fv(f, 'password')
            client_ip = self.client_address[0]
            key = f'{client_ip}:{email}'
            if security.rate_limited(key):
                return self.send('Too many attempts. Try again later.', 429)
            c = dbm.db()
            r = c.execute('SELECT * FROM users WHERE email=? AND active=1 LIMIT 1', (email,)).fetchone()
            if not r or not security.password_ok(pw, r['password_hash']):
                security.record_attempt(key)
                c.close()
                return self.send(views.login_page('Invalid credentials'), 401)
            security.clear_attempts(key)
            sid, csrf = security.create_session(c, r['id'], client_ip)
            c.commit()
            c.close()
            self.send_response(303)
            self.send_header('Location', '/')
            secure_cookie = os.getenv('CBAM_COOKIE_SECURE', '1' if os.getenv('CBAM_ENV', 'development').lower() == 'production' else '0') == '1'
            cookie_attrs = f'{security.SESSION_COOKIE}={sid}; HttpOnly; SameSite=Lax; Path=/; Max-Age={security.SESSION_TTL_HOURS * 3600}'
            if secure_cookie:
                cookie_attrs += '; Secure'
            self.send_header('Set-Cookie', cookie_attrs)
            self.end_headers()
            return
        if path == '/upload':
            return do_upload(self)
        try:
            return handle_post(self, path)
        except ValueError:
            return self.send('Invalid or oversized request body.', 400)
        except Exception:
            import logging
            logging.getLogger('cbeos.http').exception('Unhandled POST handler error')
            return self.send('Internal server error.', 500)


def main():
    # Production mode must fail closed until the database, file storage, recovery,
    # security, regulatory, and data-processing gates are independently evidenced.
    ops_readiness.require_production_ready()
    dbm.init()
    print(f'CBAM Evidence OS (Control Tower) running at http://{HOST}:{PORT}/')
    print('Admin: ' + os.getenv('CBAM_ADMIN_EMAIL', 'admin@example.com'))
    print('Set CBAM_ADMIN_PASSWORD before first run for a non-default local password.')
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == '__main__':
    main()
