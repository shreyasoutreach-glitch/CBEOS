"""Render runtime environment contract tests."""
import importlib
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import server


class RenderRuntimeTests(unittest.TestCase):
    def test_render_port_is_used_when_cbam_port_is_not_explicit(self):
        old_port = os.environ.get("PORT")
        old_cbam_port = os.environ.get("CBAM_PORT")
        try:
            os.environ["PORT"] = "54321"
            os.environ.pop("CBAM_PORT", None)
            importlib.reload(server)
            self.assertEqual(server.PORT, 54321)
            os.environ["CBAM_PORT"] = "8123"
            importlib.reload(server)
            self.assertEqual(server.PORT, 8123)
        finally:
            if old_port is None:
                os.environ.pop("PORT", None)
            else:
                os.environ["PORT"] = old_port
            if old_cbam_port is None:
                os.environ.pop("CBAM_PORT", None)
            else:
                os.environ["CBAM_PORT"] = old_cbam_port
            importlib.reload(server)


if __name__ == "__main__":
    unittest.main(verbosity=2)
