# UniFi Skill versioned product and API capability catalog

2026-10-20. This is a curated, public knowledge catalog, **not a complete model inventory**. Applicable Skill: SKILL.md; M01–M10; RB03/RB04/RB05;
docs/evidence-and-acceptance.md and docs/diagnostic-evidence-contract.md.

## Data and evidence

1. docs/product-capabilities.json: exact vendor Tech Specs URL per model, selected hardware capabilities, app minimums only where documented; unknown firmware/region/release-channel remains unknown.
2. docs/api-capabilities.json: explicit API family, exact DOCUMENT version, GET endpoint, official versioned URL, selected documented fields, authorization/sensitivity classification, and execution approval status.
3. DOC_REVIEWED is neither LAB_TESTED nor PRODUCTION_VERIFIED. An uplink hardware rating does not prove actual negotiated speed; rated IDS/IPS throughput is not a WAN/LAN performance sample. Hardware 6 GHz features do not establish legal spectrum availability in any region.
4. A version not listed in the API catalog is UNKNOWN. A min-app version is not a verified firmware/app compatibility matrix. An unknown model cannot inherit another model's advertised features.
5. Vendor URLs are publicly reviewable, but CI checks schema, allowlisted official URL and version-pinning, not the ongoing vendor webpage contents. A future source-digest and semantic review mechanism needs separate acceptance.

## Scope of initial data

10 models: U7-Pro, U6-Enterprise, U7-Pro-Wall, USW-Pro-XG-8-PoE, UCG-Ultra, UXG-Max, UNVR, UVC-G5-Bullet, UA-Hub-Door, UA-Hub-Door-Mini. Not a global inventory.

The pinned Network v10.6.106 catalog contains Site, Device, Client, Network GET endpoints and newly documented WAN, DNS, Network references and Firewall policies/zones. These last groups are not enabled in the current local Collector merely because their docs exist.

Protect v7.3.70 EA example is not approved for generic image collection. Local Collector cannot assume Site Manager cloud permission. Access safety-related functions remain excluded.

## Offline Agent queries

These commands perform no device API calls, use no credential and start no resident process:

    unifi-skill --catalog-model U7-Pro
    unifi-skill --catalog-model USW-Pro-XG-8-PoE
    unifi-skill --catalog-api '/v1/sites/{siteId}/firewall/policies' --catalog-family network --catalog-version 10.6.106

Returns official-curated data with its source URL, or UNKNOWN_NOT_IN_DOCUMENTED_CATALOG. A runtime requested diagnostic still requires an authorized, local, read-only execution path and the full Evidence Gate.

Offline validation in the repo:

    python3 scripts/validate_capability_catalog.py
    python3 -m unittest discover -s tests -p 'test_capability_catalog.py' -v

## Gates for further growth

- Add exact official Tech Specs and dated Release Notes for each model, firmware, application and release channel before asserting deployment compatibility.
- Check endpoint permissions, page boundaries, response shape, sensitive identifiers and exact API document version before proposing new GET-only runtime modules.
- Test negative cases and privacy in mock CI. Hardware acceptance must separately document OS/App/Firmware versions and observed results.
- Sign/review the portable one-shot binary for each OS before production deployment. Never download/execute unknown Python from the latest main branch.
- Official background source monitoring remains a separate already-deployed process; optional global reference pages are not a blocking defect.


## Official entire visible-model index (automated discovery design)

The old 10 hand-curated Tech Specs capability examples are NOT a full product inventory. The new scripts/discover_official_products.py can enumerate all visible product links from 8 official UniFi Tech Specs categories (including all accessories subcategories), with exact All(N) count checks, per-page SHA-256, robots compliance, source-only canonical URLs, bounded GET and no private Controller calls. Newly listed links do not need model-specific code edits. It never attributes detailed features/firmware compatibility from a listing link alone.

Current official public-source scan remains FAIL_CLOSED because techspecs.ui.com/robots.txt issues a same-host 307 redirect to / rather than readable robots.txt rules. A separate official ui.com sitemap is accessible but contains navigation URLs, NOT equivalent complete product inventory. Therefore sync/official-product-index.json is explicitly NOT_VERIFIED with zero products, and the runtime reports truthful coverage. No alternative source has been silently substituted, and CI's Source Check reports unverified source condition without breaking the independent Skill/Collector mock gates.

When a verifiable official source can be loaded, its index is validated with validate_official_index(), then the Agent can query any newly discovered model slug without modifying per-model Python code. It returns OFFICIAL_VISIBLE_PRODUCT_LINK_ONLY_FEATURES_UNKNOWN for a listed but not separately source-reviewed product. Unknown/absent entries call for an AI Agent public-official-source search, not asking the user to manually upload a screenshot. Full current visible inventory never implies all discontinued products, UISP or a model-by-firmware features matrix.
