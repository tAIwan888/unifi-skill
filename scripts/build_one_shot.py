#!/usr/bin/env python3
"""Build a *one-file* on-demand Skill CLI, with a pinned, audit-able source snapshot.

Execute only in trusted CI/build workspace. PyInstaller is a build-time dependency;
end users need no Python, git, package manager or persistent background service.
No runtime download or execution of unsigned arbitrary code is supported.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from convert_v6_wifi_evidence import SKILL_FILES

ROOT = Path(__file__).resolve().parents[1]


def build_command(platform, output):
    p = str(platform)
    if p not in ("win32", "darwin", "linux"):
        raise ValueError("unsupported host platform")
    if p != sys.platform and not (p == "linux" and sys.platform.startswith("linux")):
        raise ValueError("cross-compilation not supported: run on target OS")
    target = Path(output).resolve()
    if ROOT == target or ROOT in target.parents:
        raise ValueError("dist path cannot be inside public source repository")
    cmd = [sys.executable, "-m", "PyInstaller",
           "--noconfirm", "--clean", "--onefile", "--console",
           "--name", "unifi-skill", "--distpath", str(target)]
    for name in SKILL_FILES:
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("required Skill snapshot file missing or symlinked: " + name)
        parent = os.path.dirname(name) or "."
        cmd += ["--add-data", str(path) + os.pathsep + parent]
    if p == "darwin":
        # PyObjC is a build-only macOS dependency bundled into the executable.
        cmd += ["--hidden-import", "CoreWLAN"]
    cmd += [str(ROOT / "scripts" / "run_wifi_skill.py")]
    return cmd


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build one-shot UniFi Skill CLI")
    parser.add_argument("--out", type=Path, required=True,
                        help="output directory OUTSIDE the public Skill repository")
    args = parser.parse_args(argv)
    cmd = build_command(sys.platform, args.out)
    # Never put API keys or private endpoints on a build command line.
    subprocess.run(cmd, cwd=str(ROOT), check=True)
    print("Built on-demand executable. NOT code-signed or production released.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
