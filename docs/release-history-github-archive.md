# GitHub-only archive of validated, UNREVIEWED UniFi release pointers

The seven-category product-scoped RSS scanner is **read-only**:
it has contents: read and actions: read, uses checkout with no persisted
credentials, and has no repository writes. It runs Tuesday/Friday
**15:00 Asia/Taipei** (UTC 07:00).

Its JSON Artifacts expire after 30 days. For a collection intended to
hold up to 5,000 distinct public release pointers, an Artifact-only
chain is not a durable long-term history. This standalone GitHub
Actions *companion* workflow addresses retention without giving the
crawler write privileges.

## Two-stage trust and permission model

1. A successful, scoped, read-only scanner on main emits a verified
   rolling inventory and historical JSON Artifact. A scan on a PR,
   research branch, failed scan, or repository fork cannot trigger an
   archival write.
2. The separate release-history-archive.yml listens for completed
   workflow_run events and requires head_branch=main, same source
   repository, conclusion=success, and source event either schedule or
   workflow_dispatch. It downloads only the named Artifact from the
   exact successful source run. The privileged step never executes
   artifact content.
3. validate_release_history_archive.py independently revalidates every
   public release pointer's structural identity, SHA, release UUID,
   unapproved status, current snapshot inclusion, previous archived
   provenance, nondecreasing pointer set, and nonconflicting metadata.
4. Only after those checks, the workflow writes two JSON files to
   the dedicated branch unifi-release-pointer-archive:
   history/public-release-pointers.json and
   history/source-provenance.json. It never writes main, knowledge
   modules, review digests, API keys, devices or firmware.
   The Git push is non-force; any branch restriction may reject it,
   in which case the archive job fails rather than bypassing it.
5. If one archive job fails but later successful scans continue, the
   archiver can catch up from a complete later Artifact without losing
   previously saved pointers. An incoming ledger that omits even one
   pointer previously archived fails closed rather than quietly
   resetting the archive. Before the first archive commit, there is
   no claim of observations earlier than the original valid evidence.

This is a public-source metadata archive, not vendor-signed evidence,
global release coverage, Official/RC/EA, hardware compatibility,
download availability or approved knowledge. The dedicated branch
is Git repository history subject to its branch permissions and
maintenance; its pointers remain UNREVIEWED. The global-source
blockers in Issue #7 remain DEGRADED.

## Workflow scope

- The separate 31-source official knowledge sync remains Tue/Fri
  17:00 Asia/Taipei (UTC 09:00), with Draft PR and Issue maintenance
  permissions. It does not auto-approve knowledge.
- The seven-source scanner keeps its existing Tue/Fri 15:00 schedule
  and read-only permissions.
- The archive companion has no additional cron. It runs only after
  a successful main-branch scanner, and alone has GitHub contents:
  write and actions: read. No ChatGPT recurring task, controller
  credential or private device access is required.
- Offline unit tests and GitHub PR CI can verify the archive's
  validation logic, but GitHub's workflow_run event is effective
  only after a separately authorized merge into default main.
  No live archival outcome is claimed before that deployment.

No automatic merge of this Draft PR or of any reviewed knowledge.
