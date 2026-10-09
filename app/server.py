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
from . import extraction
from . import security
from . import supplier_ops
from . import util
from . import views

HOST = os.getenv('CBAM_HOST', '127.0.0.1')
PORT = int(os.getenv('CBAM_PORT', '8000'))


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
            fh.wr