"""Static guards for the proposed read-only, PR-scoped live workflow.

No network calls. Actual Runner must validate any live security RSS feed.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / '.github' / 'workflows' / 'security-advisory-rss-live-probe.yml'


class LiveRSSWorkflowContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = FILE.read_text(encoding='utf-8')

    def test_permissions_are_strictly_read_only(self):
        self.assertIn('permissions:\n  contents: read', self.text)
        self.assertIn('persist-credentials: false', self.text)
        self.assertNotIn('pull_request_target:', self.text)
        for token in ('contents: write', 'pull-requests: write', 'issues: write',
                      'git push', 'git commit', 'gh pr merge', 'GITHUB_TOKEN:',
                      'approve_official_update.py', 'sync/reviewed.json'):
            with self.subTest(token=token):
                self.assertNotIn(token, self.text)

    def test_runs_only_for_exact_repo_branch_push(self):
        for token in ('push:', 'branches:',
                      "github.ref == 'refs/heads/feature/security-advisory-rss-read-only-probe'",
                      "github.repository == 'tAIwan888/unifi-skill'",
                      'feature/security-advisory-rss-read-only-probe',
                      'ref: ${{ github.sha }}'):
            self.assertIn(token, self.text)

    def test_real_network_request_only_after_synthetic_test(self):
        self.assertLess(self.text.find('python3 -m unittest discover'),
                        self.text.find('python3 -B scripts/probe_official_security_rss.py'))
        self.assertIn('if [ "$result" -ne 0 ]; then', self.text)
        self.assertIn('exit "$result"', self.text)
        self.assertIn("payload.get('human_reviewed') is not False", self.text)
        self.assertIn("payload.get('is_global_release_source') is not False", self.text)

    def test_artifact_is_emitted_even_on_failure(self):
        self.assertIn('actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02', self.text)
        self.assertIn('if: always()', self.text)
        self.assertIn('GITHUB_RUN_ATTEMPT', self.text)
        self.assertIn('GITHUB_SHA', self.text)
        self.assertIn('retention-days: 14', self.text)
        self.assertIn('NOT a global releases/download repair', self.text)

    def test_no_automatic_source_promotion_or_credential_usage(self):
        for token in ('sources.json', 'pending.json', 'reviewed.json', 'secrets.',
                      'workflow_dispatch:', 'schedule:', 'curl -k'):
            # workflow_dispatch mentioned in comment only; no actual event declaration.
            if token == 'workflow_dispatch:':
                self.assertNotRegex(self.text, r'(?m)^\s+workflow_dispatch:')
                continue
            self.assertNotIn(token, self.text)


if __name__ == '__main__':
    unittest.main()
