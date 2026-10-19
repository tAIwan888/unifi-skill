"""Fail-closed static test of the research workflow's no-write contract."""
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
WF=ROOT/'.github/workflows/auto-release-triage-research.yml'

class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.text=WF.read_text(encoding='utf-8')
    def test_read_only_and_branch_bound(self):
        x=self.text
        self.assertIn('  contents: read',x)
        self.assertIn('  actions: read',x)
        self.assertIn('persist-credentials: false',x)
        self.assertIn("github.ref == 'refs/heads/research/automated-release-triage'",x)
        for forbidden in ('contents: write','pull-requests: write','issues: write',
                          'gh pr merge','git push','git commit','GH_PAT','Controller-IP'):
            self.assertNotIn(forbidden,x)
    def test_all_six_scoped_sources_no_global_relabel(self):
        x=self.text
        for name in ('network_application_release_rss', 'protect_application_release_rss',
                     'os_server_release_rss','dream_machines_release_rss',
                     'wifi_firmware_release_rss','switch_firmware_release_rss',
                     'cloud_keys_release_rss'):
            self.assertIn(name,x)
        self.assertNotIn(' --only official_releases',x)
        self.assertIn('auto_release_triage.py',x)
        self.assertIn('validate_release_candidate_evidence.py',x)
    def test_no_success_on_degraded_and_artifact_after_failure(self):
        x=self.text
        self.assertIn('Do not conceal degraded official RSS health',x)
        self.assertIn('if: always()',x)
        self.assertIn('retention-days: 30',x)
        self.assertIn('source-exit-code.txt',x)
        self.assertIn('exit 2',x)
    def test_taiwan_tuesday_friday_1500_schedule(self):
        x=self.text
        # GitHub Actions Cron uses UTC, Taiwan is permanently UTC+08:00.
        self.assertIn("cron: '0 7 * * 2,5'",x)
        self.assertNotIn("cron: '47 2 * * 2,5'",x)
        self.assertIn("Asia/Taipei",x)
        self.assertIn("github.ref == 'refs/heads/main'",x)

    def test_delta_state_restoration_from_prior_success_only(self):
        x=self.text
        self.assertIn('status=success',x)
        self.assertIn('gh run download',x)
        self.assertIn('--previous',x)
        self.assertIn('artifact cannot be verified',x)

if __name__=='__main__':unittest.main()
