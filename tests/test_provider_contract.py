"""OpenAI-compatible provider contract tests; no real credentials or network calls."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import agents


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, limit=-1):
        return self.payload[:limit]


class ProviderContractTests(unittest.TestCase):
    def setUp(self):
        self.old = {key: os.environ.get(key) for key in (
            "CBAM_LLM_API_KEY", "CBAM_LLM_MODEL", "CBAM_LLM_BASE_URL"
        )}
        os.environ["CBAM_LLM_API_KEY"] = "test-only-not-a-real-secret"
        os.environ["CBAM_LLM_MODEL"] = "test-model"
        os.environ["CBAM_LLM_BASE_URL"] = "https://llm.example.test/v1"

    def tearDown(self):
        for key, value in self.old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_provider_receives_prior_agent_handoffs_and_returns_advisory_only(self):
        response = FakeResponse({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "commentary": "The evidence count is incomplete.",
                        "questions": ["Which installation does this record refer to?"],
                        "recommended_actions": ["Ask a human reviewer to confirm the source link."]
                    })
                }
            }]
        })
        previous = [{
            "from_agent": "Intake & Scope Agent",
            "to_agent": "Evidence Quality Agent",
            "body": "2 documents, 4 import lines; 3 candidate facts await review."
        }]
        with patch("app.agents.urllib.request.urlopen", return_value=response) as call:
            result = agents._llm_commentary(
                "Evidence Quality Agent",
                {"case_name": "Synthetic case", "period": "2026", "sector": "iron_steel"},
                {"missing_requirement_count": 2},
                previous,
                []
            )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["text"], "The evidence count is incomplete.")
        self.assertEqual(len(result["questions"]), 1)
        self.assertTrue(result["recommended_actions"][0].startswith("Ask a human"))
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, "https://llm.example.test/v1/chat/completions")
        sent = json.loads(request.data.decode("utf-8"))
        prompt = sent["messages"][1]["content"]
        self.assertIn("Intake & Scope Agent", prompt)
        self.assertIn("3 candidate facts await review", prompt)
        self.assertIn("cannot change authoritative state", sent["messages"][0]["content"].lower())

    def test_invalid_public_http_endpoint_is_blocked_before_network(self):
        os.environ["CBAM_LLM_BASE_URL"] = "http://llm.example.test/v1"
        with patch("app.agents.urllib.request.urlopen") as call:
            result = agents._llm_commentary("Evidence Quality Agent", {}, {}, [], [])
        self.assertEqual(result["status"], "blocked_invalid_endpoint")
        call.assert_not_called()

    def test_provider_failure_degrades_to_rules_without_failing_workflow(self):
        with patch("app.agents.urllib.request.urlopen", side_effect=TimeoutError("test timeout")):
            result = agents._llm_commentary("Evidence Quality Agent", {}, {}, [], [])
        self.assertEqual(result, {"status": "provider_error", "text": ""})


if __name__ == "__main__":
    unittest.main(verbosity=2)
