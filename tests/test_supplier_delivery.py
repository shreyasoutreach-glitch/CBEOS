"""Supplier status must reflect confirmed delivery, not an attempted send."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP = tempfile.TemporaryDirectory(prefix="cbeos-supplier-delivery-")
os.environ["CBAM_DB_PATH"] = str(Path(TMP.name) / "supplier.db")
os.environ["CBAM_UPLOAD_DIR"] = str(Path(TMP.name) / "uploads")
os.environ["CBAM_ADMIN_EMAIL"] = "supplier@example.test"
os.environ["CBAM_ADMIN_PASSWORD"] = "supplier-test-password"

from app import db as dbm, util, supplier_ops


class SupplierDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dbm.init()

    def setUp(self):
        self.c = dbm.db()
        self.tid = self.c.execute("SELECT id FROM tenants LIMIT 1").fetchone()[0]
        self.uid = self.c.execute("SELECT id FROM users WHERE tenant_id=? LIMIT 1", (self.tid,)).fetchone()[0]
        t = util.now()
        self.c.execute(
            "INSERT INTO cases(tenant_id,company,case_name,period,sector,status,created,updated,notes) VALUES(?,?,?,?,?,?,?,?,?)",
            (self.tid, "Synthetic Importer", "Supplier Delivery Test", "2026", "iron_steel", "working", t, t, ""),
        )
        self.cid = self.c.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.c.execute(
            "INSERT INTO suppliers(tenant_id,name,country,status,created,updated) VALUES(?,?,?,?,?,?)",
            (self.tid, "Synthetic Supplier", "DE", "active", t, t),
        )
        self.sid = self.c.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.c.execute(
            "INSERT INTO supplier_requests(tenant_id,case_id,supplier_id,requirement_name,title,draft,status,deadline,created_by,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (self.tid, self.cid, self.sid, "installation data", "Request: installation data", "Synthetic draft", "DRAFT", "", self.uid, t, t),
        )
        self.rid = self.c.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.c.commit()

    def tearDown(self):
        self.c.close()

    def test_unconfigured_transport_does_not_mark_request_sent(self):
        delivered, message = supplier_ops.send_request(self.c, self.tid, self.rid, self.uid)
        self.assertFalse(delivered)
        self.assertIn("remains a draft", message)
        row = self.c.execute("SELECT status,sent_at FROM supplier_requests WHERE id=? AND tenant_id=?", (self.rid, self.tid)).fetchone()
        self.assertEqual(row["status"], "DRAFT")
        self.assertEqual(row["sent_at"], "")
        audit = self.c.execute(
            "SELECT COUNT(*) FROM audit WHERE case_id=? AND action='supplier_request_delivery_not_configured'",
            (self.cid,),
        ).fetchone()[0]
        self.assertEqual(audit, 1)

    def test_confirmed_transport_marks_request_sent(self):
        with patch("app.supplier_ops.notify_supplier", return_value={"accepted": True, "transport": "test-provider", "message_id": "msg_test_123"}):
            delivered, message = supplier_ops.send_request(self.c, self.tid, self.rid, self.uid)
        self.assertTrue(delivered)
        self.assertIn("Accepted by email provider", message)
        row = self.c.execute("SELECT status,sent_at FROM supplier_requests WHERE id=? AND tenant_id=?", (self.rid, self.tid)).fetchone()
        self.assertEqual(row["status"], "SENT")
        self.assertTrue(row["sent_at"])
        audit = self.c.execute(
            "SELECT COUNT(*) FROM audit WHERE case_id=? AND action='supplier_request_sent'",
            (self.cid,),
        ).fetchone()[0]
        self.assertEqual(audit, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
