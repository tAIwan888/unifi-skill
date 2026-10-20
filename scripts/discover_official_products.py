#!/usr/bin/env python3
"""UniFi Tech Specs public product discovery, not an unofficial control API.

Reads only official public category pages. Discovers newly listed products
without a manually-maintained model allowlist. Does NOT infer device capabilities
or claim discontinued/global historical product coverage. Fail closed on partial
pages, disallowed robots, unexpected redirects and unverified counts.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

HOST = "techspecs.ui.com"
ORIGIN = "https://" + HOST
USER_AGENT = "UniFiSkillPublicProductIndexer/1.0"
MAX_BYTES = 2500000
MAX_PRODUCTS = 2000
MAX_PAGES = 70
# These are official PUBLIC CATEGORY paths, not a product/model allowlist.
CATEGORIES = {
    "cloud-gateways": "/unifi",
    "switching": "/unifi/switching",
    "wifi": "/unifi/wifi",
    "physical-security": "/unifi/physical-security",
    "door-access": "/unifi/door-access",
    "integrations": "/unifi/integrations",
    "advanced-hosting": "/unifi/advanced-hosting",
    "accessories": "/unifi/accessories",
}
DETAIL_RE = re.compile(r"^/unifi/[a-z0-9-]+/[a-z0-9-]+/?$")
ALL_RE = re.compile(r"^All\s*\(\s*(\d+)\s*\)$", re.I)
COUNT_RE = re.compile(r"\(\s*(\d+)\s*\)$")


class DiscoveryError(ValueError):
    pass


def canonical_url(href, base):
    p = urllib.parse.urlsplit(urllib.parse.urljoin(base, href))
    if (p.scheme != "https" or p.netloc != HOST or p.username or p.password or
            not p.path.startswith("/unifi") or
            p.fragment or len(p.path) > 200):
        return None
    # Strip harmless site sorting / subcategory state from PRODUCT detail URLs.
    if p.query and not DETAIL_RE.fullmatch(p.path):
        parts = urllib.parse.parse_qs(p.query, keep_blank_values=False)
        if set(parts) != {"subcategory"} or len(parts["subcategory"]) != 1:
            return None
        name = parts["subcategory"][0]
        if not re.fullmatch(r"[a-z0-9-]{1,75}", name):
            return None
        return ORIGIN + p.path.rstrip("/") + "?subcategory=" + name
    return ORIGIN + p.path.rstrip("/")


class AnchorReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchor = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a" and self.anchor is None:
            href = dict(attrs).get("href")
            if isinstance(href, str):
                self.anchor = [href, []]

    def handle_data(self, data):
        if self.anchor is not None:
            self.anchor[1].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.anchor is not None:
            href, parts = self.anchor
            label = re.sub(r"\s+", " ", " ".join(parts)).strip()
            self.links.append((href, label[:180]))
            self.anchor = None


def parse_listing(html, url):
    if not isinstance(html, str) or len(html) > MAX_BYTES:
        raise DiscoveryError("Missing/oversize listing HTML")
    reader = AnchorReader()
    reader.feed(html)
    products = {}
    categories = []
    counts = []
    for href, label in reader.links:
        canonical = canonical_url(href, url)
        if not canonical:
            continue
        route = urllib.parse.urlsplit(canonical)
        if DETAIL_RE.fullmatch(route.path):
            slug = route.path.rstrip("/").rsplit("/", 1)[-1]
            if not label or len(products) >= MAX_PRODUCTS:
                raise DiscoveryError("Missing product label or product count overflow")
            item = {"model_slug": slug, "display_label": label,
                    "source_url": ORIGIN + route.path.rstrip("/"),
                    "identity_status": "OFFICIAL_LISTING_LINK_NOT_MODEL_SPEC_VERIFIED"}
            if canonical in products and products[canonical]["display_label"] != label:
                raise DiscoveryError("Conflicting official labels on one page")
            products[canonical] = item
        else:
            m = ALL_RE.fullmatch(label)
            if m:
                counts.append((int(m.group(1)), canonical))
            n = COUNT_RE.search(label)
            if n and "subcategory=" in canonical:
                categories.append((int(n.group(1)), canonical))
    return products, counts, categories


def _get(url):
    """Bounded HTTPS GET on exact known official host. NO redirects."""
    u = urllib.parse.urlsplit(url)
    if u.scheme != "https" or u.netloc != HOST or not u.path.startswith("/unifi"):
        raise DiscoveryError("Outside approved public Tech Specs path")
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT, "Accept": "text/html",
    }, method="GET")
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            raise DiscoveryError("Redirect blocked; source URL changed")
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=15) as response:
            if response.getcode() != 200:
                raise DiscoveryError("Official source was not HTTP 200")
            if "html" not in response.headers.get("Content-Type", "").lower():
                raise DiscoveryError("Official response is not HTML")
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise DiscoveryError("Official source exceeds limit")
            return raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()
    except (urllib.error.URLError, TimeoutError, UnicodeError, OSError) as exc:
        raise DiscoveryError("Official public catalog not accessible") from exc


def _robots():
    url = ORIGIN + "/robots.txt"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT},
                                 method="GET")
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            target = urllib.parse.urlsplit(newurl)
            # Public hostname only; never include query strings or credentials.
            name = target.hostname or "unknown-host"
            path = target.path[:80]
            raise DiscoveryError("Robots redirect blocked to " + name + path)
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=12) as result:
            if result.getcode() != 200:
                raise DiscoveryError("Robots rules HTTP status invalid")
            raw = result.read(128001)
            if len(raw) > 128000:
                raise DiscoveryError("Robots policy too large")
            text = raw.decode("utf-8")
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(text.splitlines())
            return lambda u: rp.can_fetch(USER_AGENT, u)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:  # RFC9309 only precise robots 404 is permissive.
            return lambda u: True
        raise DiscoveryError("Robots request blocked") from exc
    except (urllib.error.URLError, OSError, UnicodeError, TimeoutError) as exc:
        raise DiscoveryError("Robots policy cannot be established") from exc


def discover(*, fetch=None, permitted=None):
    """No partial evidence may be accepted as a complete current catalog."""
    if fetch is None:
        fetch = _get
    if permitted is None:
        permitted = _robots()
    visited = {}
    source_digests = {}
    product_by_url = {}
    sections = {}

    def visit(url):
        if url in visited:
            return visited[url]
        if len(visited) >= MAX_PAGES:
            raise DiscoveryError("Catalog exceeded bounded page count")
        if not permitted(url):
            raise DiscoveryError("Robots disallows official listing")
        html, digest = fetch(url)
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise DiscoveryError("Source SHA-256 missing")
        result = parse_listing(html, url)
        visited[url] = result
        source_digests[url] = digest
        return result

    for family, path in CATEGORIES.items():
        listing_url = ORIGIN + path
        products, counts, subcats = visit(listing_url)
        collected = dict(products)
        source_urls = [listing_url]
        declared_count = None
        if family == "accessories":
            # Accessories have no single All view. Discover EVERY official
            # subcategory from the official landing page, not a fixed SKU list.
            if not subcats:
                raise DiscoveryError("Accessories subcategory navigation missing")
            branches = {}
            for count, page in subcats:
                if page == listing_url or page in branches:
                    continue
                if not page.startswith(ORIGIN + "/unifi/accessories?subcategory="):
                    raise DiscoveryError("Unexpected accessory category endpoint")
                branch_products, _, _ = visit(page)
                if len(branch_products) != count:
                    raise DiscoveryError("Official accessory subcategory count mismatch")
                branches[page] = count
                source_urls.append(page)
                collected.update(branch_products)
            if not branches:
                raise DiscoveryError("No verified accessory subcategories")
            # Cross-subcategory duplicates are permitted; the complete unique
            # union, NOT the sum, is the supported coverage claim.
            declared_count = sum(branches.values())
        elif family == "advanced-hosting":
            # The official page has no All count; do not fabricate an N.
            if not collected:
                raise DiscoveryError("Empty official advanced hosting page")
        else:
            if len(counts) != 1 or not 1 <= counts[0][0] <= MAX_PRODUCTS:
                raise DiscoveryError("Official All(N) category count missing")
            declared_count, all_url = counts[0]
            if len(collected) != declared_count and all_url != listing_url:
                second, _, _ = visit(all_url)
                source_urls.append(all_url)
                collected = dict(second)
            if len(collected) != declared_count:
                raise DiscoveryError("Official All(N) count versus parsed links differs")
        if not collected:
            raise DiscoveryError("No products from one required official family")
        for url, item in collected.items():
            if url not in product_by_url:
                product_by_url[url] = {**item, "categories": []}
            if family not in product_by_url[url]["categories"]:
                product_by_url[url]["categories"].append(family)
        sections[family] = {
            "source_urls": source_urls,
            "listed_count": declared_count,
            "distinct_links_verified": len(collected),
            "coverage_status": ("VISIBLE_LIST_VERIFIED" if declared_count is not None
                                else "VISIBLE_LINKS_NO_OFFICIAL_TOTAL"),
        }
    if len(product_by_url) < 20 or len(product_by_url) > MAX_PRODUCTS:
        raise DiscoveryError("Unreasonable current UniFi Tech Specs coverage")
    return {
        "schema_version": 1,
        "source": "OFFICIAL_PUBLIC_UNIFI_TECHSPECS_CATEGORY_PAGES",
        "catalog_scope": "CURRENT_VISIBLE_UNIFI_TECHSPECS_NOT_DISCONTINUED_OR_UISP",
        "snapshot_status": "ALL_CONFIGURED_LISTINGS_VERIFIED_NOT_ALL_VENDOR_HISTORY",
        "product_spec_status": "INDEX_ONLY_FEATURES_NOT_YET_VERIFIED_PER_MODEL",
        "sources": sections,
        "source_sha256": dict(sorted(source_digests.items())),
        "unique_product_links": len(product_by_url),
        "products": sorted(product_by_url.values(), key=lambda row: row["source_url"]),
    }


def run(out):
    # A failed fetch/parser/robots check never replaces the prior verified file.
    catalog = discover()
    target = Path(out)
    if target.exists() and target.is_symlink():
        raise DiscoveryError("Refuse symlink destination")
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".pending")
    temp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    temp.replace(target)
    return catalog


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        c = run(a.out)
        print(json.dumps({"status": c["snapshot_status"],
                          "unique_product_links": c["unique_product_links"]}))
        return 0
    except (DiscoveryError, OSError, ValueError) as exc:
        reason = str(exc) if type(exc) is DiscoveryError else type(exc).__name__
        print("FAIL_CLOSED: official Tech Specs inventory not verified: " + reason,
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
