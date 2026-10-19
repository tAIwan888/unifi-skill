"""Static contract for de-duplicating the mutable-title degraded source issue."""
from pathlib import Path
import unittest

WORKFLOW=(Path(__file__).resolve().parents[1]/".github/workflows/official-knowledge-sync.yml")

class DegradedIssueWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wf=WORKFLOW.read_text(encoding="utf-8")

    def test_known_open_issue_is_matched_by_number_not_title(self):
        s=self.wf
        self.assertIn('gh issue view 7 --repo "$GH_REPO" --json state --jq',s)
        self.assertIn('if [ "$issue_state" = "OPEN" ]; then',s)
        self.assertIn('no duplicate created.',s)
        self.assertNotIn('select(.title == "UniFi official-source sync degraded',s)

    def test_other_open_issues_use_marker_not_old_exact_title(self):
        s=self.wf
        self.assertIn('<!-- unifi-official-source-degraded -->',s)
        self.assertIn("select(.body | contains(",s)
        self.assertIn('if [ -n "$issue" ]; then',s)

    def test_review_gate_remains_fail_closed_and_review_only(self):
        s=self.wf
        self.assertIn('Flag degraded source health',s)
        self.assertIn("SOURCE_DEGRADED == 'true'",s)
        self.assertIn('exit 2',s)
        self.assertIn('gh pr create --draft',s)
        self.assertNotIn('gh pr merge',s)
        self.assertIn("cron: '17 2 * * 2,5'",s)

if __name__=="__main__":
    unittest.main()
