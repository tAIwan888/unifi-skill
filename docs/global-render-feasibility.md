# Global official releases and downloads: rendered public feasibility

Normal GitHub Runner source audit reports 29 / 31 successes. Two global sources remain degraded:
- https://community.ui.com/releases?view=latest : UNREADABLE_OR_JS_ONLY
- https://www.ui.com/download/unifi : NO_VERIFIABLE_RELEASE_ENTRIES

The normal raw-HTML reader sees only loading shells or generic landing-page content. This standalone branch-only, read-only GitHub Actions research job tests whether a standard anonymous headless Chrome can render the exact two official public URLs while respecting robots.txt. It reuses the production hostname allowlist, robots check, and same-host redirect policy before browser execution.

No authentication, private controller, API key, bypass, firmware binary download, GitHub write permission, scheduled task, source-catalog change or knowledge promotion. It saves only sanitized visible text digests, capped unreviewed phrase samples, and explicit failures, never the DOM or browser stderr.

A partial rendered result DOES NOT establish a comprehensive all-product catalog, Official/RC/EA release channel, binary/download authenticity, hardware compatibility or stable version. Even if both pages yield candidate text, the existing two global sources remain DEGRADED and Issue #7 remains OPEN until independent machine-verifiable exhaustive evidence exists. GitHub branch-only test; no ChatGPT scheduled job.
