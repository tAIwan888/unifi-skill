#!/usr/bin/env python3
"""Run authorized v6 Windows LAN-only collector, then fail-closed Skill validation.

User's local v6 package remains outside the PUBLIC Skill repository.
Never sends device information, credentials, output, or diagnostics to GitHub.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from convert_v6_wifi_evidence import convert
from check_diagnostic_evidence import validate


def _outside_repo(out_path, root):
    target, base = out_path.resolve(), root.resolve()
    return target != base and base not in target.parents


def execute(args, runner=subprocess.run):
    root = Path(__file__).resolve().parents[1]
    collector = args.collector_dir.resolve() / "unifi_wifi_autodiag.py"
    if not collector.is_file():
        raise ValueError("v6 collector not found; point --collector-dir to the extracted v6 folder")
    if not _outside_repo(args.out, root):
        raise ValueError("Private diagnostic outputs must be saved OUTSIDE the public Skill repository")
    if args.out.is_symlink():
        raise ValueError("Cannot overwrite a symbolic link")
    argv = [sys.executable, str(collector)]
    if args.mock:
        argv += ["--mock"]
    else:
        if not args.local or not args.local.startswith("https://"):
            raise ValueError("Authorized local Network HTTPS API URL required")
        argv += ["--local", args.local]
        if args.ca_cert:
            argv += ["--ca-cert", str(args.ca_cert.resolve())]
    with tempfile.TemporaryDirectory(prefix="unifi-skill-local-") as private:
        raw_path = Path(private) / "private-v6-evidence.json"
        argv += ["--out", str(raw_path)]
        print("Running local-only UniFi v6 collector; API key stays in the local process.", file=sys.stderr)
        done = runner(argv, cwd=str(args.collector_dir.resolve()), check=False)
        if done.returncode:
            raise ValueError("Collector failed; no Skill diagnostic report was generated")
        source = json.loads(raw_path.read_text(encoding="utf-8"))
        evidence = convert(source, root)
        problems = validate(evidence, root)
        if problems:
            raise ValueError("Skill evidence validation failed: " + "; ".join(problems))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Skill gate PASS (format/provenance). Status: INCOMPLETE; no configuration changes.")
    print("Saved sanitized evidence outside public repository: " + str(args.out))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="Windows UniFi Skill M04 v6 local-only evidence runner")
    p.add_argument("--collector-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--mock", action="store_true", help="No controller access; synthetic smoke test")
    mode.add_argument("--local", help="Authorized local Network HTTPS API root")
    p.add_argument("--ca-cert", type=Path, help="Verified local Console PEM certificate")
    args = p.parse_args(argv)
    try:
        return execute(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("STOP: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
