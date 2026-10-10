"""Fail-closed operational gates for customer-data processing.

PostgreSQL support is implemented as a compatibility layer, but a live connection and object-storage controls must be verified before production. Sandbox mode remains usable for synthetic demos; production mode must refuse to start until each explicit gate is met.
"""
from __future__ import annotations

import os
from pathlib import Path


_TRUE = {"1", "true", "yes", "on"}


def _enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in _TRUE


def _production_blockers() -> list[str]:
    """Return all production gate blockers, even while the service runs as a sandbox."""
    blockers: list[str] = []

    backend = os.getenv("CBAM_DB_BACKEND", "sqlite").strip().lower()
    database_url = (os.getenv("CBAM_DATABASE_URL") or os.getenv("DATABASE_URL") or "").strip()
    if backend != "postgres":
        blockers.append("database_backend_not_postgres")
    if not database_url:
        blockers.append("database_url_missing")
    if backend != "postgres":
        db_path = os.getenv("CBAM_DB_PATH", "")
        if not db_path or db_path.startswith("/tmp/") or db_path == ":memory:":
            blockers.append("database_storage_not_durable")
    else:
        blockers.append("database_connection_not_verified")
    storage_backend = os.getenv("CBAM_DOCUMENT_STORAGE_BACKEND", "local").strip().lower()
    bucket = os.getenv("CBAM_OBJECT_STORAGE_BUCKET", "").strip()
    if storage_backend not in {"s3", "object_storage"} or not bucket:
        blockers.append("document_storage_not_durable")

    # Explicit approvals are deliberately separate. A configured path or
    # environment variable is not evidence that a recovery/security control works.
    for variable, code in (
        ("CBAM_OBJECT_STORAGE_CONFIG_VERIFIED", "object_storage_configuration_not_verified"),
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


def production_blockers() -> list[str]:
    """Return blockers that must stop startup when production mode is requested."""
    if os.getenv("CBAM_CUSTOMER_DATA_MODE", "sandbox").strip().lower() != "production":
        return []
    return _production_blockers()


def customer_data_snapshot() -> dict:
    """Safe, secret-free operational status for admin diagnostics."""
    mode = os.getenv("CBAM_CUSTOMER_DATA_MODE", "sandbox").strip().lower()
    blockers = _production_blockers()
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
