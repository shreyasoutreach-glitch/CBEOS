"""Synthetic HTTP journey: case creation, multipart upload, agent orchestration and audit-safe readback."""
import hashlib
import http.client
import json
import os
import re
import sys
import tempfile
import threading
import unittest
import urllib.parse
from pathlib import Path
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP = tempfile.TemporaryDirectory(prefix="cbeos-full-flow-")
os.environ["CBAM_DB_PATH"] = str(Path(TMP.name) / "full-flow.db")
os.environ["CBAM_UPLOAD_DIR"] = str(Path(TMP.name) / "uploads")
os.environ["CBAM_ADMIN_EMAIL"] = "full-flow@example.test"
os.environ["CBAM_ADMIN_PASSWORD"] = "full-flow-test-password"
os.environ.pop("CBAM_LLM_API_KEY", None)
os.environ.pop("CBAM_LLM_MODEL", None)
os.environ.pop("CBAM_LLM_BASE_URL", None)
os.environ.pop("RESEND_API_KEY", None)
os.environ.pop("CBAM_EMAIL_FROM", None)

from app import db as dbm
from app.server import Handler


class FullWorkflowHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dbm.init()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        TMP.cleanup()

    def request(self, method, path, body=None, cookie=None, content_type=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        headers = {"Origin": f"http://127.0.0.1:{self.port}"}
        data = body
        if isinstance(body, dict):
            data = urllib.parse.urlencode(body)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif content_type:
            headers["Content-Type"] = content_type
        if cookie:
            headers["Cookie"] = cookie
        conn.request(method, path, data, headers)
        response = conn.getresponse()
        result = (response.status, dict(response.getheaders()), response.read().decode("utf-8", "replace"))
        conn.close()
        return result

    def csrf(self, page):
        match = re.search(r'name="csrf" value="([^"]+)"', page)
        self.assertIsNotNone(match, "CSRF token missing from authenticated form")
        return match.group(1)

    def multipart(self, fields, filename, data):
        boundary = "----CBEOSBoundaryForSyntheticTests"
        chunks = []
        for key, value in fields.items():
            chunks.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
                str(value).encode(),
                b"\r\n",
            ])
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
            b"Content-Type: text/plain\r\n\r\n",
            data,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ])
        return b"".join(chunks), f"multipart/form-data; boundary={boundary}"

    def login(self):
        status, headers, body = self.request(
            "POST", "/login",
            {"email": "full-flow@example.test", "password": "full-flow-test-password"},
        )
        self.assertEqual(status, 303, body)
        return headers["Set-Cookie"].split(";", 1)[0]

    def test_admin_integration_probe_is_safe_and_does_not_send_email(self):
        cookie = self.login()
        status, _, settings = self.request("GET", "/settings", cookie=cookie)
        self.assertEqual(status, 200, settings)
        self.assertIn("Production safety gate", settings)
        self.assertIn("Run live provider probe", settings)
        status, _, body = self.request("GET", "/api/integrations/probe", cookie=cookie)
        self.assertEqual(status, 200, body)
        payload = json.loads(body)
        self.assertIn("configuration", payload)
        self.assertEqual(payload["live_probe"]["model_provider"]["status"], "not_configured")
        self.assertEqual(payload["live_probe"]["supplier_messaging"]["status"], "not_configured")
        self.assertNotIn("test-password", body)
        self.assertNotIn("api_key", body.lower())

    def test_upload_to_ordered_agent_handoff_is_visible_and_tenant_scoped(self):
        cookie = self.login()
        status, _, form = self.request("GET", "/case/new", cookie=cookie)
        self.assertEqual(status, 200)
        token = self.csrf(form)
        status, headers, body = self.request("POST", "/case/create", {
            "csrf": token,
            "company": "Synthetic Metals GmbH",
            "case_name": "Synthetic 2026 steel evidence case",
            "period": "2026",
            "sector": "iron_steel",
            "notes": "Synthetic test fixture only",
        }, cookie=cookie)
        self.assertEqual(status, 303, body)
        case_path = headers.get("Location", "")
        match = re.fullmatch(r"/case/(\d+)", case_path)
        self.assertIsNotNone(match, f"Unexpected case redirect: {case_path}")
        case_id = int(match.group(1))

        # The buyer-facing recovery workbook must be downloadable only through
        # the authenticated, tenant-scoped case route.
        status, report_headers, report_body = self.request(
            "GET", f"/case/{case_id}/recovery-report.xlsx", cookie=cookie
        )
        self.assertEqual(status, 200, report_body[:300])
        self.assertIn("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                      report_headers.get("Content-Type", ""))
        self.assertIn(f"cbeos-recovery-case-{case_id}.xlsx",
                      report_headers.get("Content-Disposition", ""))

        status, _, detail = self.request("GET", case_path, cookie=cookie)
        self.assertEqual(status, 200)
        token = self.csrf(detail)
        fixture = (
            b"Supplier: Synthetic Steel Supplier\n"
            b"Installation: Demo Plant\n"
            b"Product: steel coil\n"
            b"Evidence note: source record requires human review.\n"
        )
        body, content_type = self.multipart(
            {"case_id": case_id, "csrf": token, "doc_type": "supplier_evidence"},
            "synthetic-supplier-evidence.txt",
            fixture,
        )
        status, headers, response = self.request("POST", "/upload", body, cookie, content_type)
        self.assertEqual(status, 303, response)
        self.assertEqual(headers.get("Location"), case_path)

        c = dbm.db()
        try:
            doc = c.execute(
                "SELECT id,filename,sha256,extracted_text FROM documents WHERE case_id=? ORDER BY id DESC LIMIT 1",
                (case_id,),
            ).fetchone()
            self.assertIsNotNone(doc)
            self.assertEqual(doc["filename"], "synthetic-supplier-evidence.txt")
            self.assertEqual(doc["sha256"], hashlib.sha256(fixture).hexdigest())
            self.assertTrue(doc["extracted_text"])
            self.assertGreaterEqual(c.execute("SELECT COUNT(*) FROM facts WHERE case_id=?", (case_id,)).fetchone()[0], 0)
            before = c.execute("SELECT COUNT(*) FROM documents WHERE case_id=?", (case_id,)).fetchone()[0]
        finally:
            c.close()

        # Unsupported file types must be rejected without creating a database row.
        status, _, detail = self.request("GET", case_path, cookie=cookie)
        token = self.csrf(detail)
        bad_body, bad_type = self.multipart(
            {"case_id": case_id, "csrf": token, "doc_type": "supplier_evidence"},
            "not-a-document.exe",
            b"MZ\x00synthetic-invalid-file",
        )
        status, _, _ = self.request("POST", "/upload", bad_body, cookie, bad_type)
        self.assertEqual(status, 415)

        c = dbm.db()
        try:
            after = c.execute("SELECT COUNT(*) FROM documents WHERE case_id=?", (case_id,)).fetchone()[0]
        finally:
            c.close()
        self.assertEqual(before, after)

        status, _, detail = self.request("GET", case_path, cookie=cookie)
        token = self.csrf(detail)
        status, headers, response = self.request(
            "POST", f"/case/{case_id}/agents/run", {"csrf": token}, cookie=cookie
        )
        self.assertEqual(status, 303, response)
        self.assertEqual(headers.get("Location"), f"/case/{case_id}/agents")
        status, _, terminal = self.request("GET", f"/case/{case_id}/agents", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertIn("Intake &amp; Scope Agent", terminal)
        self.assertIn("Evidence Quality Agent", terminal)
        self.assertIn("Supplier Operations Agent", terminal)
        self.assertIn("Declaration Package QA Agent", terminal)
        self.assertIn("Human Reviewer", terminal)
        self.assertIn("BLOCKED", terminal)
        self.assertIn("no evidence was auto-verified", terminal.lower())

        c = dbm.db()
        try:
            run = c.execute("SELECT id,status,summary_json FROM agent_runs WHERE tenant_id=(SELECT tenant_id FROM cases WHERE id=?) AND case_id=? ORDER BY id DESC LIMIT 1", (case_id, case_id)).fetchone()
            self.assertIsNotNone(run)
            self.assertEqual(run["status"], "COMPLETED")
            summary = json.loads(run["summary_json"])
            self.assertEqual(summary["readiness"]["verdict"], "BLOCKED")
            self.assertFalse(summary["llm_enabled"])
            messages = c.execute(
                "SELECT from_agent,to_agent,message_type FROM agent_messages WHERE run_id=? ORDER BY sequence_no",
                (run["id"],),
            ).fetchall()
            handoffs = [(m["from_agent"], m["to_agent"]) for m in messages if m["message_type"] == "handoff"]
            required_handoffs = [
                ("Control Tower Orchestrator", "Intake & Scope Agent"),
                ("Intake & Scope Agent", "Evidence Quality Agent"),
                ("Evidence Quality Agent", "Supplier Operations Agent"),
                ("Supplier Operations Agent", "Reconciliation Agent"),
                ("Reconciliation Agent", "Regulatory Research Agent"),
                ("Regulatory Research Agent", "Calculation Integrity Agent"),
                ("Calculation Integrity Agent", "Commercial Exposure Agent"),
                ("Commercial Exposure Agent", "Verifier Readiness Agent"),
                ("Verifier Readiness Agent", "Declaration Package QA Agent"),
                ("Declaration Package QA Agent", "Control Tower Orchestrator"),
            ]
            for edge in required_handoffs:
                self.assertIn(edge, handoffs, f"Missing ordered handoff: {edge}")
            self.assertEqual(messages[-1]["message_type"], "summary")
            self.assertEqual((messages[-1]["from_agent"], messages[-1]["to_agent"]), ("Control Tower Orchestrator", "Human Reviewer"))
            audit = c.execute("SELECT COUNT(*) FROM audit WHERE case_id=? AND action='agent_workflow_completed'", (case_id,)).fetchone()[0]
            self.assertGreaterEqual(audit, 1)
        finally:
            c.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
