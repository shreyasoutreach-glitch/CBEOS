"""Read-only integration inventory. Never returns secret values or claims legal readiness."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


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
            "status": "not_connected",
            "configured": False,
            "scope": "drafting/tracking only; no supplier messages are sent",
        },
        "external_cbam_registry": {
            "status": "not_connected",
            "configured": False,
            "scope": "no filing, declaration submission, or registry write access",
        },
        "customer_data_mode": {
            "status": "sandbox_only",
            "live_document_processing": False,
            "scope": "do not upload live customer documents until storage, retention, access, contracts and security review are approved",
        },
    }
