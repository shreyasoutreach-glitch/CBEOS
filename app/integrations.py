"""Read-only integration inventory. Never returns secret values or claims legal readiness."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
from . import ops_readiness


def _model_status() -> dict:
    key_present = bool(os.getenv("CBAM_LLM_API_KEY", "").strip())
    model = os.getenv("CBAM_LLM_MODEL", "").strip()
    base = os.getenv("CBAM_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    parsed = urlparse(base)
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    endpoint_valid = bool(
        parsed.hostname and not parsed.username and not parsed.password
        and (parsed.scheme == "https" or
             (parsed.scheme == "http" and parsed.hostname.lower() in local_hosts))
    )
    configured = key_present and bool(model) and endpoint_valid
    if not key_present or not model:
        status = "not_configured"
    elif not endpoint_valid:
        status = "blocked_invalid_endpoint"
    else:
        status = "configured_not_live_tested"
    return {
        "status": status,
        "configured": configured,
        "model": model or None,
        "base_url_host": parsed.hostname if endpoint_valid else None,
        "secret_present": key_present,
        "scope": "advisory commentary only; deterministic controls remain authoritative",
    }


def _knowledge_status() -> dict:
    index_path = ROOT / "knowledge" / "index.json"
    manifest_path = ROOT / "knowledge" / "manifest.json"
    if not index_path.is_file() or not manifest_path.is_file():
        return {
            "status": "not_available",
            "index_present": index_path.is_file(),
            "manifest_present": manifest_path.is_file(),
            "legal_reconciliation": "not_verified",
            "scope": "retrieval integrity does not establish regulatory correctness",
        }
    try:
        raw = index_path.read_bytes()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        valid = bool(manifest.get("index_sha256")) and hashlib.sha256(raw).hexdigest() == manifest["index_sha256"]
        index = json.loads(raw.decode("utf-8")) if valid else {}
        if not valid:
            status = "integrity_check_failed"
        else:
            status = "index_hash_valid"
        return {
            "status": status,
            "index_present": True,
            "manifest_present": True,
            "index_hash_valid": valid,
            "document_count": len(index.get("documents", [])) if isinstance(index.get("documents", []), list) else 0,
            "legal_reconciliation": "not_verified",
            "scope": "retrieval integrity does not establish regulatory correctness",
        }
    except (OSError, ValueError, TypeError, KeyError):
        return {
            "status": "integrity_check_failed",
            "index_present": True,
            "manifest_present": True,
            "legal_reconciliation": "not_verified",
            "scope": "retrieval integrity does not establish regulatory correctness",
        }


def status_snapshot() -> dict:
    """Summarize external and local dependencies without returning credentials."""
    return {
        "model_provider": _model_status(),
        "regulatory_knowledge": _knowledge_status(),
        "supplier_messaging": {
            "status": "configured_not_live_tested" if (
                os.getenv("RESEND_API_KEY", "").strip() and os.getenv("CBAM_EMAIL_FROM", "").strip()
            ) else "not_configured",
            "configured": bool(
                os.getenv("RESEND_API_KEY", "").strip() and os.getenv("CBAM_EMAIL_FROM", "").strip()
            ),
            "provider": "resend",
            "delivery_confirmation": "not_implemented",
            "scope": "only the authenticated human Send action invokes the provider; provider acceptance is not confirmed delivery",
        },
        "external_cbam_registry": {
            "status": "not_connected",
            "configured": False,
            "scope": "no filing, declaration submission, or registry write access",
        },
        "customer_data_mode": {
            **ops_readiness.customer_data_snapshot(),
            "live_document_processing": ops_readiness.customer_data_snapshot()["production_allowed"],
            "scope": "environment flags are not proof by themselves; every approval must be backed by reviewed evidence",
        },
    }


def _probe_json(url: str, api_key: str, timeout: float = 6.0) -> dict:
    """Perform a bounded authenticated GET and return status only, never provider payloads."""
    import urllib.error
    import urllib.request

    request = urllib.request.Request(
        url,
        headers={"Authorization": "Bearer " + api_key, "Accept": "application/json",
                 "User-Agent": "CBEOS-Integration-Probe/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            # Read only a tiny amount to ensure the body can be received. Never log it.
            response.read(1024)
            status = int(response.status)
        return {"status": "live_test_passed" if 200 <= status < 300 else "provider_error",
                "http_status": status}
    except urllib.error.HTTPError as exc:
        code = int(exc.code)
        return {"status": "auth_failed" if code in (401, 403) else "provider_error",
                "http_status": code}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return {"status": "unreachable", "http_status": None}


def probe_external_integrations(timeout: float = 6.0) -> dict:
    """Live-test credentials without sending email or exposing secrets."""
    result = {}
    key = os.getenv("CBAM_LLM_API_KEY", "").strip()
    model = os.getenv("CBAM_LLM_MODEL", "").strip()
    base = os.getenv("CBAM_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    parsed = urlparse(base)
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    valid_base = bool(parsed.hostname and not parsed.username and not parsed.password and
                      (parsed.scheme == "https" or
                       (parsed.scheme == "http" and parsed.hostname.lower() in local_hosts)))
    if not key or not model:
        result["model_provider"] = {"status": "not_configured"}
    elif not valid_base:
        result["model_provider"] = {"status": "blocked_invalid_endpoint"}
    else:
        probe = _probe_json(base + "/models", key, timeout)
        probe["model"] = model
        probe["scope"] = "authenticated models endpoint only; generation is not tested"
        result["model_provider"] = probe

    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    sender = os.getenv("CBAM_EMAIL_FROM", "").strip()
    if not resend_key or not sender:
        result["supplier_messaging"] = {"status": "not_configured"}
    else:
        probe = _probe_json("https://api.resend.com/domains", resend_key, timeout)
        probe["scope"] = "Resend credentials/domain endpoint only; no email sent and delivery not tested"
        result["supplier_messaging"] = probe
    return result
