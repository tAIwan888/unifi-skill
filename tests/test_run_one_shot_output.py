"""Pure offline one-shot machine-readable output contract."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_v6_wifi_skill as runner


class MachineOutputTests(unittest.TestCase):
    def test_mock_stdout_single_json_object(self):
        with tempfile.TemporaryDirectory() as temp:
            flags = SimpleNamespace(
                collector_dir=None, out=Path("-"), mock=True,
                local=None, ca_cert=None)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = runner.execute(flags)
            self.assertEqual(code, 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result["test_tier"], "MOCK_TESTED")
            self.assertEqual(result["device_access"], "NONE")
            self.assertEqual(result["verification_status"], "INCOMPLETE")
            self.assertFalse((Path(temp) / "-").exists())
            self.assertNotIn("Skill gate PASS", output.getvalue())


if __name__ == "__main__":
    unittest.main()
