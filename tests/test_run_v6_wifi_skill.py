"""Synthetic-only tests for the one-command v6 Skill workflow."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_v6_wifi_skill as runner


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.tmp = Path(self.directory.name)
        self.collector = self.tmp / "v6"
        self.collector.mkdir()
        (self.collector / "unifi_wifi_autodiag.py").write_text("# synthetic fixture only\n", encoding="utf-8")

    def args(self, **override):
        base = {"collector_dir": self.collector, "out": self.tmp / "evidence.json",
                "mock": True, "local": None, "ca_cert": None}
        base.update(override)
        return SimpleNamespace(**base)

    def fake_run(self, argv, cwd, check):
        self.assertFalse(check)
        self.assertEqual(Path(cwd), self.collector)
        dest = Path(argv[argv.index("--out") + 1])
        report = {
            "report_schema": "unifi-m04-wifi-evidence-lan-only-v6",
            "collection_mode": "mock",
            "sites": [{"access_points": []}],
            "private": {"api_key": "SYNTHETIC_KEY_MUST_NOT_LEAK"}
        }
        dest.write_text(json.dumps(report), encoding="utf-8")
        return SimpleNamespace(returncode=0)

    def test_mock_runner_produces_skill_gated_report(self):
        self.assertEqual(runner.execute(self.args(), runner=self.fake_run), 0)
        evidence = json.loads((self.tmp / "evidence.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence["verification_status"], "INCOMPLETE")
        self.assertEqual(evidence["device_access"], "NONE")
        self.assertNotIn("SYNTHETIC_KEY_MUST_NOT_LEAK", json.dumps(evidence))

    def test_fails_when_collector_missing(self):
        with self.assertRaisesRegex(ValueError, "collector not found"):
            runner.execute(self.args(collector_dir=self.tmp), runner=self.fake_run)

    def test_output_inside_public_repo_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "OUTSIDE"):
            runner.execute(self.args(out=ROOT / "do-not-create-private.json"), runner=self.fake_run)

    def test_non_https_target_refused_without_running_collector(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            runner.execute(self.args(mock=False, local="http://example.invalid/"), runner=self.fake_run)

    def test_collector_failure_aborts_without_report(self):
        def fail(argv, cwd, check):
            return SimpleNamespace(returncode=2)
        with self.assertRaisesRegex(ValueError, "Collector failed"):
            runner.execute(self.args(), runner=fail)
        self.assertFalse((self.tmp / "evidence.json").exists())

    def test_rejects_external_api_key_destination(self):
        self.assertFalse(runner._authorized_lan_api("https://api.ui.com/proxy/network/integration/v1"))
        self.assertFalse(runner._authorized_lan_api("https://attacker.example/proxy/network/integration/v1"))
        self.assertFalse(runner._authorized_lan_api("https://192.0.2.1/proxy/network/integration/v1"))

    def test_accepts_authorized_private_lan_only(self):
        self.assertTrue(runner._authorized_lan_api("https://unifi.local/proxy/network/integration/v1"))
        self.assertTrue(runner._authorized_lan_api("https://192.168.100.1/proxy/network/integration/v1"))
        self.assertTrue(runner._authorized_lan_api("https://10.20.30.40/integration/v1"))

    def test_runner_command_is_local_only(self):
        captured = {}
        def observe(argv, cwd, check):
            captured["argv"] = argv
            return self.fake_run(argv, cwd, check)
        self.assertEqual(runner.execute(self.args(), runner=observe), 0)
        self.assertNotIn("--lan-target", captured["argv"])
        self.assertNotIn("--cloud", captured["argv"])
        self.assertNotIn("Cloudflare", " ".join(captured["argv"]))


if __name__ == "__main__":
    unittest.main()
