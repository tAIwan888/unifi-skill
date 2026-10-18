from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class OfficialSyncTriggerTests(unittest.TestCase):
    def test_review_only_official_sync_runs_on_monitored_code_changes(self):
        text=(ROOT/".github/workflows/official-knowledge-sync.yml").read_text(encoding="utf8")
        header=text.split("permissions:",1)[0]
        self.assertIn("push:",header)
        self.assertIn("branches: [main]",header)
        for expected in ("scripts/check_official_updates.py","scripts/release_catalog.py",
                         "scripts/apt_official_index.py","scripts/build_review_triage.py",
                         "sync/sources.json"):
            self.assertIn(expected,header)
        self.assertIn("schedule:",header)
        self.assertIn("workflow_dispatch:",header)
    def test_sync_remains_human_review_only(self):
        text=(ROOT/".github/workflows/official-knowledge-sync.yml").read_text(encoding="utf8")
        self.assertIn("review-triage.md",text)
        self.assertIn("SOURCE_DEGRADED",text)
        self.assertIn("Draft",text)
        self.assertNotIn("gh pr merge",text)
        self.assertNotIn("approve_official_update.py",text)
if __name__=="__main__":unittest.main()
