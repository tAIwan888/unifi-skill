#!/usr/bin/env python3
"""Run authorized v6 Windows LAN-only collector, then fail-closed Skill validation.

User's local v6 package remains outside the PUBLIC Skill repository.
Never sends device information, credentials, output, or diagnostics to GitHub.
"""
import argparse
import ipaddress
import getpass
import json
from pathlib import Path
from urllib.parse import urlsplit
import subprocess
import sys
import tempfile

from convert_v6_wifi_evidence import convert
from check_diagnostic_evidence import validate
from windows_wlan_native import sample as native_wlan_sample
from platform_wifi import current_link
from collect_wifi_lan_local import collect_local, mock_fixture


def _outside_repo(out_path, root):
    target, base = out_path.resolve(), root.resolve()
    return target != base and base not in target.parents



def _authorized_lan_api(address):
    if not isinstance(address, str):
        return False
    try:
        u = urlsplit(address)
        if u.scheme != "https" or not u.hostname or u.username or u.password or u.query or u.fragment:
            return False
        if u.path.rstrip("/") not in ("/proxy/network/integration/v1", "/integration/v1"):
            return False
        host = u.hostname.lower()
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            return host.endswith(".local") and len(host) < 255
        allowed = (ipaddress.ip_network("10.0.0.0/8"),
                   ipaddress.ip_network("172.16.0.0/12"),
                   ipaddress.ip_network("192.168.0.0/16"))
        return ip.version == 4 and any(ip in block for block in allowed)
    except ValueError:
        return False


def execute(args, runner=subprocess.run):
    """Integrated Skill collector is default; optional extracted legacy v6 supported."""
    # PyInstaller one-file unpacks signed-in-release Skill source snapshots
    # to a temporary directory. A local source checkout uses its repo root.
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    if not _outside_repo(args.out, root):
        raise ValueError("Private diagnostic outputs must be saved OUTSIDE the public Skill repository")
    if args.out.is_symlink():
        raise ValueError("Cannot overwrite a symbolic link")
    if args.collector_dir is None:
        if args.mock:
            source = mock_fixture()
        else:
            if not _authorized_lan_api(args.local):
                raise ValueError("Authorized private LAN Network HTTPS API URL required")
            key = getpass.getpass("UniFi Network Integrations API Key (not saved): ").strip()
            if not key:
                raise ValueError("API Key required locally")
            source = collect_local(args.local, key,
                                   str(args.ca_cert.resolve()) if args.ca_cert else None)
            del key
    else:
        if getattr(sys, "frozen", False):
            raise ValueError("Legacy --collector-dir requires Python source mode, not one-shot binary")
        # Compatibility option: run an inspected older v6 ZIP, never pass a
        # credential by command-line argument or write output to a public Repo.
        collector = args.collector_dir.resolve() / "unifi_wifi_autodiag.py"
        if not collector.is_file():
            raise ValueError("v6 collector not found; point --collector-dir to the extracted v6 folder")
        argv = [sys.executable, str(collector)]
        if args.mock:
            argv += ["--mock"]
        else:
            if not _authorized_lan_api(args.local):
                raise ValueError("Authorized private LAN Network HTTPS API URL required")
            argv += ["--local", args.local]
            if args.ca_cert:
                argv += ["--ca-cert", str(args.ca_cert.resolve())]
        with tempfile.TemporaryDirectory(prefix="unifi-skill-local-") as private:
            raw_path = Path(private) / "private-v6-evidence.json"
            argv += ["--out", str(raw_path)]
            print("Running local-only legacy v6 collector.", file=sys.stderr)
            done = runner(argv, cwd=str(args.collector_dir.resolve()), check=False)
            if done.returncode:
                raise ValueError("Collector failed; no Skill diagnostic report was generated")
            source = json.loads(raw_path.read_text(encoding="utf-8"))
        if not args.mock:
            try:
                source["client_wifi_link"] = current_link()
            except (OSError, ValueError, TypeError, AttributeError):
                source["client_wifi_link"] = {"status": "NATIVE_API_UNAVAILABLE"}
    evidence = convert(source, root)
    problems = validate(evidence, root)
    if problems:
        raise ValueError("Skill evidence validation failed: " + "; ".join(problems))
    # No reports inside GitHub worktree, no user identifiers inside evidence.
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Skill gate PASS (format/provenance). Status: " + evidence["verification_status"] + "; no configuration changes.")
    print("Saved sanitized evidence outside public repository: " + str(args.out))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="Cross-platform on-demand UniFi Skill M04 one-shot evidence runner")
    p.add_argument("--collector-dir", type=Path, help="Optional legacy v6 extracted folder; default uses integrated Skill collector")
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
