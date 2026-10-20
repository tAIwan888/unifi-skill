#!/usr/bin/env python3
"""Offline smoke for compiled one-file portable Skill CLI; no device access."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def test_binary(folder):
    executable = Path(folder) / ("unifi-skill.exe" if sys.platform == "win32" else "unifi-skill")
    if not executable.is_file():
        raise ValueError("expected one-file executable missing")
    with tempfile.TemporaryDirectory(prefix="unifi-portable-smoke-") as temp:
        evidence = Path(temp) / "sanitized.json"
        done = subprocess.run([str(executable), "--mock", "--out", str(evidence)],
                              timeout=120, capture_output=True, text=True, check=False)
        if done.returncode:
            # This test uses synthetic data and no secrets. Avoid printing even
            # future raw stderr in CI, to be safe.
            raise ValueError("one-shot executable smoke exited with code " + str(done.returncode))
        if not evidence.is_file():
            raise ValueError("mock did not produce diagnostic report")
        report = json.loads(evidence.read_text(encoding="utf-8"))
        if (report.get("device_access") != "NONE" or
                report.get("test_tier") != "MOCK_TESTED" or
                report.get("verification_status") != "INCOMPLETE" or
                report.get("configuration_change_proposals") != []):
            raise ValueError("mock is not fail-closed")
        if len(report["skill"]["loaded_files"]) < 18:
            raise ValueError("bundled Skill provenance incomplete")
        print("Portable one-shot offline smoke PASS: mock only, no UniFi access")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(test_binary(args.dist))
