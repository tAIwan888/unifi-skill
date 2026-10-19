"""Static safety contract for privileged, post-scan PUBLIC history archival."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'.github/workflows/release-history-archive.yml'
SCANNER=ROOT/'.github/workflows/auto-release-triage-research.yml'
KNOWLEDGE=ROOT/'.github/workflows/official-knowledge-sync.yml'

class WorkflowSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive=ARCHIVE.read_text(encoding='utf-8')
        cls.scanner=SCANNER.read_text(encoding='utf-8')
        cls.knowledge=KNOWLEDGE.read_text(encoding='utf-8')

    def test_archive_only_successful_main_schedule_or_dispatch(self):
        s=self.archive
        self.assertIn('workflow_run:',s)
        self.assertIn('types: [completed]',s)
        self.assertIn("head_branch == 'main'",s)
        self.assertIn("conclusion == 'success'",s)
        self.assertIn("event == 'schedule'",s)
        self.assertIn("event == 'workflow_dispatch'",s)
        self.assertIn("head_repository.full_name == 'tAIwan888/unifi-skill'",s)
        self.assertIn('cancel-in-progress: false',s)
        self.assertNotIn('pull_request:',s)
        self.assertNotIn('cron:',s)

    def test_scanner_stays_read_only_and_review_sync_separate(self):
        self.assertIn('  actions: read',self.scanner)
        self.assertIn('  contents: read',self.scanner)
        self.assertIn('persist-credentials: false',self.scanner)
        self.assertIn("cron: '0 7 * * 2,5'",self.scanner)
        self.assertNotIn('contents: write',self.scanner)
        self.assertIn("cron: '0 9 * * 2,5'",self.knowledge)

    def test_archive_writes_only_isolated_history_branch(self):
        s=self.archive
        self.assertIn('  contents: write',s)
        self.assertIn('  actions: read',s)
        self.assertIn('unifi-release-pointer-archive',s)
        self.assertIn('git push origin "HEAD:refs/heads/$archive_branch"',s)
        self.assertIn('history/public-release-pointers.json',s)
        self.assertIn('history/source-provenance.json',s)
        self.assertIn('validate_release_history_archive',s)
        self.assertIn('auto-release-history.json',s)
        for bad in ('git push --force', 'git merge origin/main',
                    'gh pr merge','github.event.pull_request',
                    'sync/reviewed.json','controller.ui.com','unifi-os-update'):
            self.assertNotIn(bad,s)

    def test_no_untrusted_code_execution_or_device_writes(self):
        s=self.archive
        self.assertIn('ref: main',s)
        self.assertIn('gh run download "$SOURCE_RUN_ID"',s)
        self.assertIn('git show "$archive_ref:history/public-release-pointers.json"',s)
        self.assertIn('git diff --cached --quiet',s)
        self.assertNotIn('eval ',s)
        self.assertNotIn('bash "$RUNNER_TEMP/vendor-rss-evidence/',s)
        self.assertNotIn('python3 "$RUNNER_TEMP/vendor-rss-evidence/',s)

if __name__ == '__main__':
    unittest.main()
