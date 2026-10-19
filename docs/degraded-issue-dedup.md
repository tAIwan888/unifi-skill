# Degraded official-source issue: stable identifier and no duplicate alert

The 31-source official knowledge-sync workflow can still validate 29 sources while the two global pages remain DEGRADED. Its GitHub issue-maintenance step previously matched the exact original issue title, but Issue #7 was renamed to accurately describe the actual two remaining failures. The next run would otherwise risk creating a duplicate issue.

Issue #7 is now the **stable primary identity** for the existing open source health incident. The workflow uses \`gh issue view 7 --json state\` and returns early if OPEN, regardless of title, labels or language. If #7 has been closed, it searches for a later active issue using a machine-readable body marker rather than an editable title. Only if none exists does it create another issue. It never automatically reopens a legitimately closed Issue #7.

This is an issue de-duplication fix only. The knowledge-sync workflow still operates Tue/Fri UTC 09:00 (Taiwan 17:00), and can write only GitHub review branches, Draft PRs, or maintenance issues (not knowledge approvals or devices). Separately, the seven scoped RSS-only workflow remains read-only at Taiwan Tue/Fri 15:00, UTC 07:00. Global releases and downloads are still DEGRADED; no source approval or merge follows from deduplication.
