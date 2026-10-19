# UniFi fully automatic public-source monitoring: machine-only trust tier

The source monitor can authenticate transport origin, parse exact Help Center article IDs,
pin Developer Markdown versions and accept seven scoped Community RSS candidate feeds.
It cannot independently validate a human-style interpretation of all prose, certify
Official/RC/EA release channels or decide device compatibility.

## What happens automatically

1. The Tue/Fri 17:00 Asia/Taipei GitHub Runner reads the 31 configured public sources.
2. Each successfully fetched source obtains the canonical URL, normalized SHA-256 and
   parser-specific metadata. 19 Help Center articles, three pinned Developer guides and
   seven scoped RSS feeds can be machine-validated; two global pages may remain DEGRADED.
3. The separate auto_accept_source_observations.py checks the complete source inventory,
   health totals and the exact per-source parser and ID, version or release post metadata.
   It compares any pending change with its observed SHA, URL, modules and parser evidence.
4. Successful entries are stored deterministically in sync/machine-accepted.json, marked
   MACHINE_SOURCE_OBSERVED_UNREVIEWED_NOT_DEVICE_APPROVED. Former pending fingerprint
   rows are reconciled to zero. This is **not** approval in sync/reviewed.json.
5. PR CI runs check_review_gate.py --mode machine and fails for missing/mismatched health,
   source URL, SHA, ID, parser method, channel metadata or lost archive records. Negative
   synthetic tests cover modified SHA, fake Article IDs, promoted release channels,
   degraded sources, changed candidate lists and spoofed manual reviews.
6. A successful GitHub monitor can propose updated machine evidence on its existing
   Draft branch. It NEVER auto merges PRs, modifies private UniFi controllers, triggers
   device upgrades, or promotes observations to procedural knowledge.

A source previously valid but failing this scan is **stale**, not "currently verified".
The health report and 7-feed live inventory independently retain DEGRADED semantics.
A published RSS pointer remains an **unreviewed candidate** even if its source SHA is
machine accepted. No customer secrets or local devices are accessed.

The old check_review_gate.py --mode human remains callable for legacy formal human
knowledge review, but no longer blocks **machine-source-monitoring CI**.
Repository-wide write GitHub permissions remain an independent issue tracked in #46;
this change neither grants additional permissions nor merges its own PR.

Two full-product global sources without a verifiable public API remain DEGRADED (#7).
Machine source acceptance does not imply 31/31 coverage and cannot close Issue #7.
