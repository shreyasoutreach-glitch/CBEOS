"""Security primitives for authentication, session/CSRF, RBAC, rate limiting and upload safety."""
import os
import time
import zipfile
import hmac as _hmac
from http import cookies
from . import db as dbm
from . import util

SESSION_COOKIE = 'cbam_session'
SESSION_TTL_HOURS = 12
MAX_UPLOAD = int(os.getenv('CBAM_MAX_UPLOAD_BYTES', str(25 * 1024 * 1024)))
ALLOWED_EXTENSIONS = ('.pdf', '.xlsx', '.csv', '.txt')
MAGIC_BYTES = {'.pdf': (b'%PDF-',), '.xlsx': (b'PK\\x03\\x04',)}
_LOGIN_ATTEMPTS = {}
LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_ATTEMPTS = 8

def rate_limited(key: str) -> bool:
    now = time.time()
    hist = [t for t in _LOGIN_ATTEMPTS.get(key, []) if now - t < LOGIN_WINDOW_SECONDS]
    _LOGIN_ATTEMPTS[key] = hist
    return len(hist) >= LOGIN_MAX_ATTEMPTS

def record_attempt(key: str):
    _LOGIN_ATTEMPTS.setdefault(key, []).append(time.time())

def clear_attempts(key: str):
    _LOGIN_ATTEMPTS.pop(key, None)

def scan_upload(filename: str, data: bytes):
    """A minimal heuristic scanner, not a substitute for an AV engine."""
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS: return False, f'Unsupported file type: {ext or "(none)"}'
    if not data: return False, 'Empty file'
    if b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR' in data[:4096]: return False, 'Matched anti-malware test signature (EICAR)'
    for bad_magic in (b'MZ', b'\\x7fELF', b'\\xca\\xfe\\xba\\xbe'):
        if data.startswith(bad_magic): return False, 'File begins with an executable/binary signature, not a document'
    expect = MAGIC_BYTES.get(ext)
    if expect and not any(data.startswith(m) for m in expect): return False, f'File content does not match its {ext} extension (possible spoofed upload)'
    if ext == '.xlsx':
        try:
            import io
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                infos = archive.infolist()
                if len(infos) > 5000: return False, 'XLSX contains too many archive members'
                if sum(i.file_size for i in infos) > 100 * 1024 * 1024: return False, 'XLSX expands beyond the 100 MiB safety limit'
                for info in infos:
                    name = info.filename.replace('\\', '/')
                    if name.startswith('/') or any(part == '..' for part in name.split('/')): return False, 'XLSX contains an unsafe archive path'
                    if info.flag_bits & 0x1: return False, 'Encrypted XLSX members are not supported'
                    if 'vbaproject.bin' in name.lower(): return False, 'Macro-enabled workbook payloads are not accepted as .xlsx'
                    if info.file_size > 1024 * 1024 and info.compress_size > 0 and info.file_size / info.compress_size > 200: return False, 'XLSX member has a suspicious compression ratio'
        except (zipfile.BadZipFile, OSError, ValueError): return False, 'XLSX is not a valid ZIP-based workbook container'
    return True, ''

def password_hash(p, salt=None): return util.password_hash(p, salt)
def password_ok(p, stored): return util.password_ok(p, stored)

def create_session(c, user_id: int, ip: str = ''):
    import datetime
    sid, csrf = util.new_token(32), util.new_token(24)
    exp = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=SESSION_TTL_HOURS)).isoformat()
    c.execute('INSERT INTO sessions(id,user_id,csrf,expires,created,ip) VALUES(?,?,?,?,?,?)', (sid, user_id, csrf, exp, util.now(), ip))
    return sid, csrf

def actor_from_session_id(sid: str):
    if not sid: return None
    c = dbm.db()
    r = c.execute('SELECT s.*,u.email,u.role,u.tenant_id FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.id=? AND s.expires>? AND u.active=1', (sid, util.now())).fetchone()
    c.close()
    return r

def parse_cookies(header: str): return cookies.SimpleCookie(header or '')
def csrf_ok(session_csrf: str, submitted: str) -> bool:
    return bool(session_csrf and submitted and _hmac.compare_digest(session_csrf, submitted))
def require_permission(role: str, perm: str) -> bool:
    return dbm.has_permission(role, perm)
