"""Fail-closed static policy for the optional read-only SHA recheck workflow."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / '.github/workflows/public-source-sha-recheck.yml'

class ReadOnlyRecheckWorkflowContract(unittest.TestCase):
    def test_no_write_permissions_or_git_mutation(self):
        text = FILE.read_text(encoding='utf-8')
        self.assertIn('workflow_dispatch:', text)
        self.assertIn('permissions:\n  contents: read', text)
        self.assertIn("github.ref == 'refs/heads/main'", text)
        self.assertNotIn('pull-requests: write', text)
        self.assertNotIn('contents: write', text)
        for command in ('git push', 'git commit', 'git merge', 'gh pr merge', 'approve_official_update.py'):
            self.assertNotIn(command, text)
    def test_trusted_script_not_loaded_from_draft_pr_branch(self):
        text = FILE.read_text(encoding='utf-8')
        self.assertIn('ref: main', text)
        self.assertIn('path: trusted', text)
        self.assertIn('path: review-evidence', text)
        self.assertIn('scripts/recheck_pending_sources.py', text)
        self.assertIn('--observed ../review-evidence/sync/observed.json', text)
        self.assertIn('--pending ../review-evidence/sync/pending.json', text)
        self.assertEqual(text.count('persist-credentials: false'), 2)
        self.assertIn('EXPECTED_SHA', text)
        self.assertIn('if: always()', text)
    def test_report_is_not_an_approval(self):
        text = FILE.read_text(encoding='utf-8')
        self.assertIn('not human reviewed', text)
        self.assertIn('Save machine-readable review evidence (not approval)', text)
        self.assertNotIn('sync/reviewed.json', text)
        self.assertIn('public-source-sha-recheck', text)

if __name__=='__main__': unittest.main()
