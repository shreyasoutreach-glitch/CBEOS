"""Production customer-data gates fail closed until every release control is evidenced."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import ops_readiness


class OperationalReadinessTests(unittest.TestCase):
    def test_sandbox_mode_does_not_claim_production_approval(self):
        with patch.dict(os.environ, {"CBAM_CUSTOMER_DATA_MODE": "sandbox"}, clear=True):
            snapshot = ops_readiness.customer_data_snapshot()
            self.assertEqual(snapshot["status"], "sandbox_only")
            self.assertFalse(snapshot["production_allowed"])
            self.assertEqual(snapshot["blockers"], [])

    def test_production_mode_reports_missing_storage_and_approvals(self):
        env = {
            "CBAM_CUSTOMER_DATA_MODE": "production",
            "CBAM_DB_BACKEND": "sqlite",
            "CBAM_DB_PATH": "/tmp/cbeos.db",
            "CBAM_UPLOAD_DIR": "/tmp/uploads",
        }
        with patch.dict(os.environ, env, clear=True):
            blockers = ops_readiness.production_blockers()
            self.assertIn("database_backend_not_postgres", blockers)
            self.assertIn("database_url_missing", blockers)
            self.assertIn("database_storage_not_durable", blockers)
            self.assertIn("document_storage_not_durable", blockers)
            self.assertIn("backup_restore_not_verified", blockers)
            self.assertIn("regulatory_data_not_approved", blockers)
            with self.assertRaisesRegex(RuntimeError, "production mode is blocked"):
                ops_readiness.require_production_ready()

    def test_production_requires_each_explicit_gate(self):
        env = {
            "CBAM_CUSTOMER_DATA_MODE": "production",
            "CBAM_DB_BACKEND": "postgres",
            "DATABASE_URL": "postgresql://redacted-placeholder",
            "CBAM_DB_PATH": "/var/lib/cbeos/cbeos.db",
            "CBAM_UPLOAD_DIR": "/var/lib/cbeos/uploads",
            "CBAM_MALWARE_SCAN_ENABLED": "true",
            "CBAM_BACKUP_RESTORE_VERIFIED": "true",
            "CBAM_SECURITY_REVIEW_APPROVED": "true",
            "CBAM_RETENTION_POLICY_APPROVED": "true",
            "CBAM_CUSTOMER_DATA_PROCESSING_APPROVED": "true",
            "CBAM_REGULATORY_DATA_APPROVED": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            # This module only records the DB backend contract; it cannot turn
            # the current SQLite db.py implementation into a PostgreSQL driver.
            # The test documents the explicit gates, not an end-to-end migration.
            self.assertEqual(ops_readiness.production_blockers(), [])
            self.assertTrue(ops_readiness.customer_data_snapshot()["production_allowed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
