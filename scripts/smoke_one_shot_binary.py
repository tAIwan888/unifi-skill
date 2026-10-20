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
        # Test the generic Collector inside the frozen one-file executable too.
        profiles = [
            ["--capabilities"],
            ["--collect", "inventory", "--mock", "--out", "-"],
            ["--collect", "network", "--mock", "--out", "-"],
            ["--collect", "all", "--mock", "--out", "-"],
        ]
        for options in profiles:
            out = subprocess.run([str(executable), *options], timeout=120,
                                 capture_output=True, text=True, check=False)
            if out.returncode:
                raise ValueError("Frozen generic CLI failed offline smoke")
            data = json.loads(out.stdout)
            if options[0] == "--capabilities":
                if "inventory" not in data["implemented_profiles"]:
                    raise ValueError("Generic capabilities not embedded in one-file binary")
                continue
            if data.get("collector_profile") != options[1] or data.get("device_access") != "NONE":
                raise ValueError("Generic CLI emitted invalid or nonmock evidence")
            if data.get("verification_status") != "INCOMPLETE":
                raise ValueError("No-access mock incorrectly passed evidence readiness")
            if options[1] == "all" and "access_validated_status" not in data["missing_metrics"]:
                raise ValueError("Unimplemented Access capability was not marked missing")
        print("Portable one-shot offline smoke PASS: mock only, no UniFi access")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(test_binary(args.dist))
