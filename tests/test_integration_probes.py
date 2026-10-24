"""Live integration probes are bounded, secret-safe GETs and never send email."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import integrations


class FakeResponse:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self, limit=-1): return b'{"data":[{"id":"redacted"}]}'[:limit]


class IntegrationProbeTests(unittest.TestCase):
    def setUp(self):
        self.keys = ("CBAM_LLM_API_KEY", "CBAM_LLM_MODEL", "CBAM_LLM_BASE_URL",
                     "RESEND_API_KEY", "CBAM_EMAIL_FROM")
        self.old = {key: os.environ.get(key) for key in self.keys}
        os.environ["CBAM_LLM_API_KEY"] = "synthetic-test-token"
        os.environ["CBAM_LLM_MODEL"] = "synthetic-test-model"
        os.environ["CBAM_LLM_BASE_URL"] = "https://llm.example.test/v1"
        os.environ["RESEND_API_KEY"] = "synthetic-resend-token"
        os.environ["CBAM_EMAIL_FROM"] = "sandbox@example.test"

    def tearDown(self):
        for key, value in self.old.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value

    def test_successful_probes_use_get_and_return_no_payload_or_secrets(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse()) as call:
            result = integrations.probe_external_integrations(timeout=2.0)
        self.assertEqual(result["model_provider"]["status"], "live_test_passed")
        self.assertEqual(result["supplier_messaging"]["status"], "live_test_passed")
        self.assertEqual(call.call_count, 2)
        for item in call.call_args_list:
            request = item.args[0]
            self.assertEqual(request.method, "GET")
            self.assertNotIn("synthetic-test-token", str(result))
            self.assertNotIn("synthetic-resend-token", str(result))
        self.assertIn("no email sent", result["supplier_messaging"]["scope"])

    def test_auth_failure_is_reported_without_response_body(self):
        import urllib.error
        error = urllib.error.HTTPError("https://example.test", 401, "unauthorized",
                                       {}, None)
        with patch("urllib.request.urlopen", side_effect=error):
            result = integrations._probe_json("https://example.test", "synthetic-token")
        self.assertEqual(result, {"status": "auth_failed", "http_status": 401})
        self.assertNotIn("synthetic-token", str(result))

    def test_unconfigured_provider_does_not_make_network_call(self):
        for key in self.keys:
            os.environ.pop(key, None)
        with patch("urllib.request.urlopen") as call:
            result = integrations.probe_external_integrations()
        call.assert_not_called()
        self.assertEqual(result["model_provider"]["status"], "not_configured")
        self.assertEqual(result["supplier_messaging"]["status"], "not_configured")


if __name__ == "__main__":
    unittest.main(verbosity=2)
