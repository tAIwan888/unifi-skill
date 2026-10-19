"""Degraded-issue dedup workflow contract and executable mock GitHub CLI."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

WORKFLOW=Path(__file__).resolve().parents[1]/".github/workflows/official-knowledge-sync.yml"
CLI="#!/usr/bin/env python3\nimport os,sys\nargs=sys.argv[1:]\nwith open(os.environ[\"MOCK_LOG\"],\"a\",encoding=\"utf8\") as fp:\n    fp.write(\" \".join(args[:2])+\"\\n\")\nif args[:2]==[\"issue\",\"view\"]:\n    mode=os.environ[\"MOCK_PRIMARY\"]\n    if mode==\"MISSING\":\n        sys.exit(1)\n    print(mode)\nelif args[:2]==[\"issue\",\"list\"]:\n    print(os.environ.get(\"MOCK_FALLBACK\",\"\"))\nelif args[:2]==[\"issue\",\"create\"]:\n    print(\"https://github.com/tAIwan888/unifi-skill/issues/200\")\nelse:\n    sys.exit(9)\n"

def issue_shell(text):
    m=re.search(
        r"      - name: Open one maintenance issue if public sources are unavailable\n"
        r".*?        run: \|\n(?P<body>.*?)"
        r"(?=\n      - name: Flag degraded source health)",
        text,flags=re.DOTALL)
    if not m:
        raise AssertionError("issue block missing")
    return textwrap.dedent(m.group("body")).strip()+"\n"

class DegradedIssueWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=WORKFLOW.read_text(encoding="utf-8")
        cls.shell=issue_shell(cls.text)

    def test_known_issue_is_matched_by_number(self):
        self.assertIn('gh issue view 7 --repo "$GH_REPO" --json state --jq',self.shell)
        self.assertIn('if [ "$issue_state" = "OPEN" ]; then',self.shell)
        self.assertNotIn('select(.title == "UniFi official-source sync degraded',self.shell)

    def test_marker_fallback_avoids_duplicate(self):
        self.assertIn('<!-- unifi-official-source-degraded -->',self.shell)
        self.assertIn('select(.body | contains(',self.shell)

    def test_review_contract_unchanged(self):
        s=self.text
        self.assertIn('Flag degraded source health',s)
        self.assertIn("SOURCE_DEGRADED == 'true'",s)
        self.assertIn('exit 2',s)
        self.assertIn('gh pr create --draft',s)
        self.assertNotIn('gh pr merge',s)
        self.assertIn("cron: '0 9 * * 2,5'",s)
        self.assertNotIn("cron: '17 2 * * 2,5'",s)

    def test_taipei_tue_fri_1700_vs_read_only_1500(self):
        self.assertIn("cron: '0 9 * * 2,5'",self.text)
        rss=(WORKFLOW.parent/"auto-release-triage-research.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '0 7 * * 2,5'",rss)
        for date in (20, 23):  # Tue/Fri, Oct 2026; Asia/Taipei has no DST
            instant=datetime(2026,10,date,9,0,tzinfo=timezone.utc)
            local=instant.astimezone(ZoneInfo("Asia/Taipei"))
            self.assertIn(local.weekday(),(1,4))
            self.assertEqual((local.hour,local.minute),(17,0))

    @unittest.skipUnless(shutil.which("bash"),"GitHub Runner uses Bash")
    def test_shell_syntax(self):
        p=subprocess.run(["bash","-n"],input=self.shell,text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)

    @unittest.skipUnless(shutil.which("bash"),"GitHub Runner uses Bash")
    def test_issue_scenario_decisions_with_offline_gh_stub(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            stub=root/"gh"
            stub.write_text(CLI,encoding="utf8")
            stub.chmod(0o755)
            scenarios=(
                ("OPEN","",["issue view"]),
                ("CLOSED","11",["issue view","issue list"]),
                ("MISSING","",["issue view","issue list","issue create"]),
            )
            for primary,fallback,expected in scenarios:
                with self.subTest(primary=primary,fallback=fallback):
                    log=root/"calls.log"
                    log.write_text("")
                    env=os.environ.copy()
                    env.update({
                        "PATH":str(root)+os.pathsep+os.environ.get("PATH",""),
                        "GH_REPO":"tAIwan888/unifi-skill",
                        "MOCK_LOG":str(log),
                        "MOCK_PRIMARY":primary,
                        "MOCK_FALLBACK":fallback,
                    })
                    result=subprocess.run(["bash","-c",self.shell],env=env,
                                          capture_output=True,text=True,timeout=10)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertEqual(log.read_text().splitlines(),expected)

if __name__=="__main__":
    unittest.main()
