"""Fail-closed operational gates for customer-data processing.

The current application backend is SQLite + local filesystem. This module does not
pretend those are production-grade shared storage. Sandbox mode remains usable for
synthetic demos; production mode must refuse to start until each explicit gate is met.
"""
from __future__ import annotations

import os
from pathlib import Path


_TRUE = {"1", "true", "yes", "on"}


def _enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in _TRUE


def production_blockers() -> list[str]:
    """Return machine-readable blocker codes without exposing secrets or file contents."""
    mode = os.getenv("CBAM_CUSTOMER_DATA_MODE", "sandbox").strip().lower()
    if mode != "production":
        return []

    blockers: list[str] = []

    # Current db.py only implements SQLite. A DATABASE_URL by itself does not
    # mean the application actually uses PostgreSQL.
    backend = os.getenv("CBAM_DB_BACKEND", "sqlite").strip().lower()
    if backend != "postgres":
        blockers.append("database_backend_not_postgres")
    if not os.getenv("DATABASE_URL", "").strip():
        blockers.append("database_url_missing")

    db_path = os.getenv("CBAM_DB_PATH", "")
    if not db_path or db_path.startswith("/tmp/") or db_path == ":memory:":
        blockers.append("database_storage_not_durable")
    upload_path = os.getenv("CBAM_UPLOAD_DIR", "")
    if not upload_path or upload_path.startswith("/tmp/"):
        blockers.append("document_storage_not_durable")

    # Explicit approvals are deliberately separate. A configured path or
    # environment variable is not evidence that a recovery/security control works.
    for variable, code in (
        ("CBAM_MALWARE_SCAN_ENABLED", "malware_scanning_not_enabled"),
        ("CBAM_BACKUP_RESTORE_VERIFIED", "backup_restore_not_verified"),
        ("CBAM_SECURITY_REVIEW_APPROVED", "independent_security_review_missing"),
        ("CBAM_RETENTION_POLICY_APPROVED", "retention_policy_not_approved"),
        ("CBAM_CUSTOMER_DATA_PROCESSING_APPROVED", "customer_data_processing_not_approved"),
        ("CBAM_REGULATORY_DATA_APPROVED", "regulatory_data_not_approved"),
    ):
        if not _enabled(variable):
            blockers.append(code)

    return blockers


def customer_data_snapshot() -> dict:
    """Safe, secret-free operational status for admin diagnostics."""
    mode = os.getenv("CBAM_CUSTOMER_DATA_MODE", "sandbox").strip().lower()
    blockers = production_blockers()
    return {
        "mode": mode,
        "production_allowed": mode == "production" and not blockers,
        "status": "blocked" if mode == "production" and blockers else (
            "approved" if mode == "production" else "sandbox_only"
        ),
        "blockers": blockers,
        "scope": "environment flags record approvals; each approval must be backed by reviewed evidence",
    }


def require_production_ready() -> None:
    """Refuse startup in production mode while any customer-data gate is open."""
    blockers = production_blockers()
    if os.getenv("CBAM_CUSTOMER_DATA_MODE", "sandbox").strip().lower() == "production" and blockers:
        raise RuntimeError(
            "CBEOS production mode is blocked by operational safety gates: "
            + ", ".join(blockers)
        )
