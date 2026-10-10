"""HTTP-level regression for the outcome-first operator journey."""
import http.client
import json
import os
import re
import sys
import tempfile
import threading
import unittest
import urllib.parse
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP = tempfile.TemporaryDirectory(prefix="cbeos-journey-")
os.environ["CBAM_DB_PATH"] = str(Path(TMP.name) / "journey.db")
os.environ["CBAM_ADMIN_EMAIL"] = "journey@example.test"
os.environ["CBAM_ADMIN_PASSWORD"] = "journey-test-password"

from app import db as dbm, security, util
from app.server import Handler


class OperatorJourneyHTTPTests(unittest.TestCase):
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

    def request(self, method, path, body=None, cookie=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=8)
        headers = {"Origin": f"http://127.0.0.1:{self.port}"}
        data = None
        if body is not None:
            data = urllib.parse.urlencode(body)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if cookie:
            headers["Cookie"] = cookie
        conn.request(method, path, data, headers)
        response = conn.getresponse()
        result = (response.status, dict(response.getheaders()), response.read().decode("utf-8", "replace"))
        conn.close()
        return result

    def test_dashboard_guided_destinations_are_authenticated_and_render(self):
        status, headers, body = self.request(
            "POST", "/login",
            {"email": "journey@example.test", "password": "journey-test-password"},
        )
        self.assertEqual(status, 303, body)
        cookie = headers["Set-Cookie"].split(";", 1)[0]

        status, _, dashboard = self.request("GET", "/", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertIn("Sandbox mode", dashboard)
        self.assertIn("Client outcome view", dashboard)

        destinations = {
            "/cases": "Operational workspaces",
            "/suppliers": "Supplier operations",
            "/exceptions": "Exceptions",
            "/verification": "Verification",
        }
        for path, expected in destinations.items():
            with self.subTest(path=path):
                status, headers, page = self.request("GET", path, cookie=cookie)
                self.assertEqual(status, 200, f"{path} returned {status}: {page[:300]}")
                self.assertIn(expected.lower(), page.lower())
                self.assertIn("Content-Security-Policy", headers)

    def test_guided_destinations_do_not_leak_without_session(self):
        for path in ("/cases", "/suppliers", "/exceptions", "/verification"):
            with self.subTest(path=path):
                status, headers, _ = self.request("GET", path)
                self.assertIn(status, (302, 303))
                self.assertTrue(headers.get("Location", "").endswith("/login"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
