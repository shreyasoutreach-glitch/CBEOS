"""Low-level helpers shared across the codebase. No business logic here."""
import datetime, html, hashlib, hmac, re, secrets
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def esc(v) -> str:
    return html.escape(str(v if v is not None else ''))


def num(v, d=Decimal('0')) -> Decimal:
    try:
        return Decimal(str(v).replace(',', '').strip())
    except (InvalidOperation, ValueError, AttributeError):
        return d


def money(v) -> str:
    return f"€{num(v):,.2f}"


def q(v) -> str:
    """Quantize a decimal to 4dp string for consistent storage/display."""
    return str(num(v).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))


def norm(v) -> str:
    """Normalise a string for fuzzy-equality comparisons (case/punctuation-insensitive)."""
    return re.sub(r'[^a-z0-9]+', ' ', str(v or '').lower()).strip()


def password_hash(p: str, salt: str = None) -> str:
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac('sha256', p.encode(), salt.encode(), 240000).hex()
    return salt + '$' + h


def password_ok(p: str, stored: str) -> bool:
    try:
        salt, h = stored.split('$', 1)
        return hmac.compare_digest(password_hash(p, salt).split('$', 1)[1], h)
    except Exception:
        return False


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8', 'replace')).hexdigest()


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def short(s: str, n: int = 500) -> str:
    s = str(s or '')
    return s if len(s) <= n else s[:n - 1] + '…'
