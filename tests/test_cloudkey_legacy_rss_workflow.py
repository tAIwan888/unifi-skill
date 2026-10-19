"""Static permissions/trigger/test-order guard, synthetic only."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/'.github/workflows/cloudkey-legacy-rss-readonly-probe.yml'

class LiveWorkflowGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.yaml=FILE.read_text(encoding='utf-8')

    def test_read_only_without_credentials(self):
        s=self.yaml
        self.assertIn('permissions:\n  contents: read',s)
        self.assertIn('persist-credentials: false',s)
        self.assertNotIn('contents: write',s)
        self.assertNotIn('pull-requests: write',s)
        for bad in ('GH_TOKEN','GITHUB_TOKEN','gh pr merge','git push','git commit','sync/reviewed.json'):
            self.assertNotIn(bad,s)

    def test_branch_and_approved_action_shas(self):
        s=self.yaml
        self.assertIn('research/cloudkey-legacy-rss-probe',s)
        self.assertIn("github.repository == 'tAIwan888/unifi-skill'",s)
        self.assertIn('ref: ${{ github.sha }}',s)
        self.assertIn('actions/checkout@11d5960a326750d5838078e36cf38b85af677262',s)
        self.assertIn('actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02',s)
        self.assertNotIn('pull_request_target:',s)
        self.assertNotIn('workflow_dispatch:',s)

    def test_synthetic_before_live_and_fail_closed(self):
        s=self.yaml
        self.assertLess(s.index('python3 -m unittest discover'),s.index('python3 -B scripts/probe_cloudkey_legacy_rss.py'))
        self.assertIn("if current == 0:",s)
        self.assertIn('FAIL_CLOSED:',s)
        self.assertIn("report.get('human_reviewed') is not False",s)
        self.assertIn("report.get('complete_current_cloudkey_coverage_verified') is not False",s)

    def test_preserve_failure_artifacts(self):
        s=self.yaml
        self.assertIn('probe-exit-code.txt',s)
        self.assertIn('if: always()',s)
        self.assertIn('retention-days: 14',s)
        self.assertIn('not automatically present-day Cloud Keys OS coverage',s)

if __name__=='__main__': unittest.main()
