#!/usr/bin/env python3
"""Fail-closed offline checks and lookups for reviewed version-pinned catalogs.

Never contacts a UniFi device, executes API endpoints or infers latest releases.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
APPROVED_GET = {
    "/v1/info", "/v1/sites",
    "/v1/sites/{siteId}/devices", "/v1/sites/{siteId}/devices/{deviceId}",
    "/v1/sites/{siteId}/clients", "/v1/sites/{siteId}/networks",
}
FAMILIES = {"wifi-ap", "switch", "gateway", "cloud-gateway", "nvr", "camera", "access-hub"}


def _official_url(value, host, prefix):
    if not isinstance(value, str):
        return False
    p = urlsplit(value)
    return (p.scheme == "https" and p.netloc == host and
            p.path.startswith(prefix) and not p.username and
            not p.password and not p.query and not p.fragment)


def validate(products, apis):
    """Return actionable errors without accepting document source as a live test."""
    errors = []
    if not isinstance(products, dict) or products.get("schema_version") != 1:
        return ["Invalid product catalog schema"]
    if not isinstance(apis, dict) or apis.get("schema_version") != 1:
        return ["Invalid API catalog schema"]
    if products.get("test_tier") != "DOC_REVIEWED" or products.get("coverage") != "CURATED_EXAMPLES_NOT_ALL_UNIFI_MODELS":
        errors.append("Product catalog must not claim full coverage or lab acceptance")
    if products.get("firmware_release_channel") != "NOT_VERIFIED_PER_DEVICE":
        errors.append("Unreviewed firmware/release channel must be UNKNOWN")
    records = products.get("products")
    if not isinstance(records, list) or not records:
        return errors + ["No documented products"]
    seen_models = set()
    for item in records:
        if not isinstance(item, dict):
            errors.append("Invalid product record")
            continue
        model = item.get("model")
        if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{1,60}", model):
            errors.append("Invalid model")
            continue
        if model in seen_models:
            errors.append("Duplicate model " + model)
        seen_models.add(model)
        if item.get("family") not in FAMILIES:
            errors.append("Unsupported product family " + model)
        if not _official_url(item.get("source_url"), "techspecs.ui.com", "/unifi/"):
            errors.append("Invalid official source " + model)
        req = item.get("app_requirements")
        if not isinstance(req, list):
            errors.append("Invalid app requirements " + model)
        else:
            for row in req:
                if (not isinstance(row, dict) or
                    row.get("status") != "DOCUMENTED_MINIMUM_NOT_RUNTIME_COMPATIBILITY" or
                    not re.fullmatch(r"\d+\.\d+\.\d+", str(row.get("min_version", ""))) or
                    row.get("app") not in ("Network", "Protect", "Access", "Connect")):
                    errors.append("Unverified app minimum version " + model)
        features = item.get("features")
        if not isinstance(features, list) or not features:
            errors.append("No model capability evidence " + model)
            continue
        names = set()
        for entry in features:
            if not isinstance(entry, dict):
                errors.append("Malformed feature " + model)
                continue
            name, value = entry.get("name"), entry.get("value")
            if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", name) or name in names:
                errors.append("Duplicate or invalid feature ID " + model)
            names.add(name)
            if isinstance(value, (dict, type(None))) or type(value) not in (str, list, int, bool):
                errors.append("Invalid feature value " + model)
            if type(value) is list and (not value or
                   any(type(x) not in (str, int, float) for x in value)):
                errors.append("Unsupported list feature " + model)
            if name == "radio_bands_ghz" and isinstance(value, list) and 6 in value:
                if not isinstance(entry.get("constraint"), str) or "6GHz" not in entry["constraint"]:
                    errors.append("6 GHz regulatory constraint absent " + model)
            if name.endswith("rated_throughput_mbps") and not entry.get("constraint"):
                errors.append("Rated bandwidth must not be treated as actual " + model)
    endpoints = apis.get("endpoints")
    if not isinstance(endpoints, list) or not endpoints:
        return errors + ["No documented API endpoints"]
    if apis.get("no_automatic_execution_from_catalog") is not True:
        errors.append("Catalog data MUST NOT be automatically executed")
    if apis.get("latest_version_claim") != "NONE":
        errors.append("Catalog cannot claim global latest version")
    seen_apis = set()
    for ep in endpoints:
        if not isinstance(ep, dict):
            errors.append("Invalid endpoint record")
            continue
        api, version, path = ep.get("api_family"), ep.get("doc_version"), ep.get("path")
        ident = (api, version, path)
        if ident in seen_apis:
            errors.append("Duplicate API endpoint")
        seen_apis.add(ident)
        if not isinstance(path, str) or not path.startswith("/v1/") or "?" in path or ".." in path:
            errors.append("Invalid API path")
            continue
        if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
            errors.append("Missing exact API version " + path)
            continue
        if ep.get("method") != "GET":
            errors.append("Unsafe API method " + path)
        host = "developer.ui.com"
        if not _official_url(ep.get("docs"), host, "/" + str(api) + "/v" + version + "/"):
            # Developer catalog is versioned by API family; do not accept
            # generic help pages or undated release notes as endpoint proof.
            errors.append("Missing version-pinned official API document " + path)
        if ep.get("documentation_status") != "OFFICIAL_DOCUMENT_REVIEW_ONLY":
            errors.append("Documentation must not masquerade as Lab result " + path)
        if ep.get("version_match") != "EXACT_APP_AND_DOCUMENTED_ENDPOINT_REQUIRED":
            errors.append("No exact deployed-version gate " + path)
        state = ep.get("executable_template_approval")
        if state not in ("EXISTING_NETWORK_GET_COLLECTOR_ONLY", "NOT_APPROVED_FOR_AUTOMATIC_EXECUTION"):
            errors.append("Unknown runtime approval state " + path)
        if state == "EXISTING_NETWORK_GET_COLLECTOR_ONLY" and (
                api != "network" or version != "10.6.106" or path not in APPROVED_GET):
            errors.append("Unreviewed API promoted to runnable " + path)
        if api != "network" and state != "NOT_APPROVED_FOR_AUTOMATIC_EXECUTION":
            errors.append("Cross-app API requires separate authorization " + path)
    if not products.get("products") or not apis.get("endpoints"):
        errors.append("Empty catalog")
    return errors


def load(root=ROOT):
    root = Path(root)
    products = json.loads((root / "docs/product-capabilities.json").read_text(encoding="utf-8"))
    api = json.loads((root / "docs/api-capabilities.json").read_text(encoding="utf-8"))
    errors = validate(products, api)
    if errors:
        raise ValueError("; ".join(errors))
    return products, api


def query_model(model, root=ROOT):
    models, _ = load(root)
    return next((p for p in models["products"] if p["model"] == model), None)


def query_endpoint(family, version, path, root=ROOT):
    _, api = load(root)
    return next((p for p in api["endpoints"] if
                 (p["api_family"], p["doc_version"], p["path"]) ==
                 (family, version, path)), None)


def main(argv=None):
    p = argparse.ArgumentParser(description="Offline public UniFi catalog validation and read-only lookup")
    p.add_argument("--repo-root", type=Path, default=ROOT)
    p.add_argument("--model")
    p.add_argument("--endpoint")
    p.add_argument("--family", default="network")
    p.add_argument("--api-version", default="10.6.106")
    args = p.parse_args(argv)
    try:
        products, apis = load(args.repo_root)
        if args.model:
            result = query_model(args.model, args.repo_root)
        elif args.endpoint:
            result = query_endpoint(args.family, args.api_version, args.endpoint, args.repo_root)
        else:
            result = {
                "status": "DOC_REVIEWED_NOT_LAB_VERIFIED",
                "products": len(products["products"]),
                "documented_get_endpoints": len(apis["endpoints"]),
                "auto_execute_catalog_endpoints": False,
                "global_latest_version_verified": False,
            }
        print(json.dumps(result if result is not None else
                         {"status": "UNKNOWN_NOT_IN_DOCUMENTED_CATALOG"},
                         ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError):
        print("Catalog validation failed; no endpoint can be approved", file=sys.stderr)
        return 2


if __name__ == "__main__":
    import sys
    raise SystemExit(main())
