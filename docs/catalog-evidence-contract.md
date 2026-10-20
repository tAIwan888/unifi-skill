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
