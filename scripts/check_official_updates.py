#!/usr/bin/env python3
"""Public official-source watcher. Fingerprints are *never* knowledge approvals."""
import argparse
import hashlib
import importlib.util
import html
import json
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, parse, request, robotparser

ROOT = Path(__file__).resolve().parents[1]
_CATALOG_SPEC = importlib.util.spec_from_file_location("release_catalog_local", Path(__file__).resolve().parent/"release_catalog.py")
_CATALOG = importlib.util.module_from_spec(_CATALOG_SPEC)
_CATALOG_SPEC.loader.exec_module(_CATALOG)
UA = "UniFiSkillPublicKnowledgeMonitor/0.6 (+https://github.com/tAIwan888/unifi-skill)"
HOSTS = {"help.ui.com", "developer.ui.com", "community.ui.com", "www.ui.com", "ui.com"}
LIMIT = 1500000
MAX_ROBOTS = 512 * 1024
_ROBOTS_CACHE = {}

def load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")

def normalize(raw):
    s = raw.decode("utf-8", "replace")
    if "<html" not in s.lower():
        raise ValueError("not_html")
    s = re.sub(r"(?is)<(script|style|noscript|svg|template)\b[^>]*>.*?</\1>", " ", s)
    match = re.search(r"(?is)<(main|article)\b[^>]*>(.*?)</\1>", s)
    if match:
        s = match.group(2)
    s = html.unescape(re.sub(r"(?s)<[^>]+>", " ", s))
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) < 100:
        raise ValueError("unreadable_or_js_only")
    return s

def allowed_url(url):
    p = parse.urlsplit(url)
    if (p.scheme != "https" or p.hostname not in HOSTS or p.port is not None
        or p.username or p.password or p.fragment):
        raise ValueError("untrusted_source")
    return p

class SafeRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # The robots policy is checked for the *initial* source hostname.
        # A redirect to another vendor-owned hostname is not sufficient:
        # that destination may carry a different robots policy and scope.
        source = allowed_url(req.full_url)
        target = allowed_url(newurl)
        if source.hostname != target.hostname:
            raise ValueError("cross_host_redirect_disallowed")
        if source.path != "/robots.txt":
            # Same host is insufficient: robots.txt can disallow the
            # *destination path* even if the original path was allowed.
            # Source fetches must have called _robot_ok before redirecting.
            missing = object()
            policy = _ROBOTS_CACHE.get(source.hostname, missing)
            if policy is missing:
                raise ValueError("redirect_without_checked_robots")
            if policy is not None and not policy.can_fetch(UA, newurl):
                raise ValueError("robots_disallowed_redirect")
        # A same-host redirect while loading /robots.txt itself is
        # permitted; we parse the returned robots content before fetching
        # any actual document from that hostname.
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def _robot_ok(url, opener):
    p = allowed_url(url)
    host = p.hostname
    if host not in _ROBOTS_CACHE:
        robot_url = "https://" + host + "/robots.txt"
        req = request.Request(robot_url, headers={"User-Agent":UA})
        try:
            with opener.open(req, timeout=12) as response:
                if response.status != 200:
                    raise ValueError("robots_unavailable")
                raw = response.read(MAX_ROBOTS + 1)
        except error.HTTPError as exc:
            if exc.code == 404:
                # RFC 9309 section 2.3.1.3: absent robots.txt is
                # unavailable, not a Disallow rule. Do not equate
                # 403/429/5xx or network errors with 404.
                _ROBOTS_CACHE[host] = None
            else:
                raise
        else:
            if len(raw) > MAX_ROBOTS:
                raise ValueError("robots_too_large")
            parser = robotparser.RobotFileParser()
            parser.parse(raw.decode("utf-8", "replace").splitlines())
            _ROBOTS_CACHE[host] = parser
    policy = _ROBOTS_CACHE[host]
    if policy is not None and not policy.can_fetch(UA, url):
        raise ValueError("robots_disallowed")

def fetch_official_developer_markdown(entry, opener, metadata=None):
    """Fingerprint a pinned, public official API *guide*, not live API capability.

    Markdown body is untrusted remote source data. It must never be executed,
    handed to an agent as an instruction, or automatically promoted to Skill.
    """
    url = entry["url"]
    u = allowed_url(url)
    if u.hostname != "developer.ui.com" or u.query:
        raise ValueError("invalid_developer_markdown_url")
    match = re.fullmatch(r"/(network|protect|site-manager)/v([0-9]+(?:\.[0-9]+){2,3})/ai-gettingstarted\.md",u.path)
    if not match:
        raise ValueError("invalid_developer_markdown_url")
    family, version = match.groups()
    _robot_ok(url, opener)
    req = request.Request(url,headers={"User-Agent":UA,"Accept":"text/markdown, text/plain"})
    with opener.open(req,timeout=18) as response:
        ctype=response.headers.get_content_type()
        if ctype not in ("text/markdown","text/plain"):
            raise ValueError("unexpected_content_type")
        raw=response.read(LIMIT + 1)
    if len(raw)>LIMIT:
        raise ValueError("too_large")
    try:
        body=raw.decode("utf-8","strict")
    except UnicodeError as exc:
        raise ValueError("invalid_developer_markdown_utf8") from exc
    tokens={"network":"Network","site-manager":"Site Manager","protect":"Protect"}
    if len(body)<450 or "UniFi" not in body or tokens[family] not in body:
        raise ValueError("invalid_developer_markdown_content")
    # Normalize whitespace to reduce no-op formatting changes; never
    # rewrite instructions or copy guide text into the public repository.
    text=re.sub(r"\s+"," ",body).strip()
    if metadata is not None:
        metadata.update({
            "fetch_method":"PUBLIC_OFFICIAL_VERSIONED_DEVELOPER_MARKDOWN",
            "api_family":family,
            "doc_version":version,
            "body_word_count":len(text.split()),
            "version_scope":"PINNED_DOCUMENT_NOT_LATEST"
        })
    return ("<html><main>"+html.escape(text)+"</main></html>").encode("utf-8")

NETWORK_RELEASE_RSS_URL = "https://community.ui.com/rss/releases/UniFi-Network-Application/e6712595-81bb-4829-8e42-9e2630fabcfe"
RELEASE_ITEM_LINK = re.compile(r"/releases/(?:[A-Za-z0-9-]+/)?[0-9a-fA-F-]{36}\Z")
_RELEASE_VERSION = r"(?P<version>\d{1,3}(?:\.\d{1,4}){2,3})"
_PRODUCT_TITLE = re.compile(
    r"\A(?P<label>(?:UniFi|Enterprise Campus|UAP|USW)[A-Za-z0-9 &+().,/-]{3,90}?) "
    + _RELEASE_VERSION + r"\Z"
)
NETWORK_RELEASE_TITLE = re.compile(r"\AUniFi Network Application " + _RELEASE_VERSION + r"\Z")

# Exact vendor URL, product title and category must all agree. Category RSS
# does not identify Official/RC/EA or ensure any platform receives a release.
RELEASE_RSS_SPECS = {
    "network_application_release_rss": {
        "url":NETWORK_RELEASE_RSS_URL, "category":"unifi-network",
        "title":NETWORK_RELEASE_TITLE, "label":"UniFi Network Application",
        "scope":"UNIFI_NETWORK_APPLICATION_ONLY"
    },
    "protect_application_release_rss": {
        "url":"https://community.ui.com/rss/releases/UniFi-Protect-Application/aada5f38-35d4-4525-9235-b14bd320e4d0",
        "category":"unifi-protect",
        "title":re.compile(r"\AUniFi Protect Application " + _RELEASE_VERSION + r"\Z"),
        "label":"UniFi Protect Application","scope":"UNIFI_PROTECT_APPLICATION_ONLY"
    },
    "os_server_release_rss": {
        "url":"https://community.ui.com/rss/releases/UniFi-OS-Server/76650b06-fc47-4892-9c12-25c64c39f842",
        "category":"unifi-network",
        "title":re.compile(r"\AUniFi OS Server " + _RELEASE_VERSION + r"\Z"),
        "label":"UniFi OS Server","scope":"UNIFI_OS_SERVER_ONLY"
    },
    "dream_machines_release_rss": {
        "url":"https://community.ui.com/rss/releases/UniFi-OS-Dream-Machines/b0f0a740-021e-4027-a778-ceba983be74b",
        "category":"unifi-gateway-cloudkey",
        "title":re.compile(r"\AUniFi OS - Dream Machines " + _RELEASE_VERSION + r"\Z"),
        "label":"UniFi OS - Dream Machines","scope":"UNIFI_OS_DREAM_MACHINES_ONLY"
    },
    "cloud_keys_release_rss": {
        "url":"https://community.ui.com/rss/releases/UniFi-Cloud-Key-Firmware/c4ccd194-4cbf-4738-b07d-0aa6f04d178e",
        "category":"unifi-gateway-cloudkey",
        "title":re.compile(r"\AUniFi OS - Cloud Keys " + _RELEASE_VERSION + r"\Z"),
        "label":"UniFi OS - Cloud Keys",
        "scope":"UNIFI_OS_CLOUD_KEYS_ONLY",
        "strict_slug":True,
    },
    "wifi_firmware_release_rss": {
        "url":"https://community.ui.com/rss/releases/UAP-USW-Firmware/9fc3b2fa-9e73-449a-924f-470e79884470",
        "category":"unifi-wireless","title":_PRODUCT_TITLE,
        "label":None,"scope":"UNIFI_AP_WIRELESS_FIRMWARE_ONLY"
    },
    "switch_firmware_release_rss": {
        "url":"https://community.ui.com/rss/releases/UniFi-Switch/f5882c6b-e77f-45c1-b019-68fd20000c31",
        "category":"unifi-switching","title":_PRODUCT_TITLE,
        "label":None,"scope":"UNIFI_SWITCH_FIRMWARE_ONLY"
    }
}

def fetch_network_release_rss(entry, opener, metadata=None):
    """Backward-compatible name; validates one exact official product RSS.

    Never infer a release's Official/RC/EA channel or hardware compatibility.
    All vendor titles/links are data, never instructions to the Skill.
    """
    key=entry["id"]
    spec=RELEASE_RSS_SPECS.get(key)
    url=entry["url"]
    if spec is None or url!=spec["url"]:
        raise ValueError("invalid_release_rss_url")
    allowed_url(url)
    _robot_ok(url,opener)
    req=request.Request(url,headers={"User-Agent":UA,"Accept":"application/rss+xml, application/xml"})
    with opener.open(req,timeout=18) as resp:
        if resp.headers.get_content_type() not in ("application/xml","text/xml","application/rss+xml"):
            raise ValueError("unexpected_content_type")
        raw=resp.read(LIMIT+1)
    if len(raw)>LIMIT:raise ValueError("too_large")
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("invalid_release_rss_xml")
    try:
        root=ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("invalid_release_rss_xml") from exc
    if root.tag!="rss":
        raise ValueError("invalid_release_rss_format")
    items=root.findall("./channel/item")
    if not 1<=len(items)<=50:
        raise ValueError("empty_release_rss")
    found=[];links=set()
    for item in items:
        title=item.findtext("title","").strip()
        link=item.findtext("link","").strip()
        p=parse.urlsplit(link)
        if (p.scheme!="https" or p.hostname!="community.ui.com" or p.username
            or p.password or p.port is not None or p.fragment or p.query
            or not RELEASE_ITEM_LINK.fullmatch(p.path)):
            raise ValueError("untrusted_release_item_url")
        if link in links:raise ValueError("duplicate_release_item")
        links.add(link)
        categories=[(cat.text or "").strip() for cat in item.findall("category")]
        # The AP/USW category RSS mixes product groups. Only accept wireless
        # items here; the separate Switch feed handles switching candidates.
        if spec["category"] not in categories:
            continue
        match=spec["title"].fullmatch(title)
        if not match:continue
        label=spec["label"] or match.group("label")
        version=match.group("version")
        if spec.get("strict_slug"):
            # The legacy-named feed includes modern OS titles. Require the
            # exact product/version URL slug before trusting a scoped pointer.
            # A UUID-only canonical post URL is also an acceptable exact ID.
            parts=p.path.split("/")
            if len(parts)==4 and parts[2]!="UniFi-OS-Cloud-Keys-"+version.replace(".","-"):
                raise ValueError("release_rss_title_slug_mismatch")
        date_raw=item.findtext("pubDate")
        try:
            parsed=parsedate_to_datetime(date_raw) if date_raw else None
        except (TypeError,ValueError) as exc:
            raise ValueError("invalid_release_rss_pubdate") from exc
        if parsed is None or parsed.tzinfo is None:
            raise ValueError("invalid_release_rss_pubdate")
        found.append({
            "product_label":label,
            "version":version,
            "source_url":link,
            "publication_date":parsed.isoformat(),
            "release_channel":"UNKNOWN_NOT_VALIDATED_FROM_RSS",
            "verification":"CANDIDATE_UNREVIEWED"
        })
    if not found:
        raise ValueError("release_rss_no_scoped_product_entries")
    found.sort(key=lambda x:x["source_url"])
    if metadata is not None:
        metadata.update({
            "fetch_method":"OFFICIAL_COMMUNITY_SCOPED_RELEASE_RSS",
            "product_scope":spec["scope"],
            "channel_scope":"CHANNEL_UNVERIFIED_MANUAL_REVIEW_REQUIRED",
            "candidate_count":len(found),
            "release_candidates":found
        })
    data=" ".join(x["product_label"]+" "+x["version"]+" "+x["source_url"]+
                  " "+x["publication_date"] for x in found)
    return ("<html><main>"+html.escape(data)+"</main></html>").encode("utf-8")

def fetch_public_help_article(entry, opener, metadata=None):
    """Use Zendesk's official anonymous published article endpoint on help.ui.com.

    The canonical Help Center URL remains in sync/sources.json; API JSON is
    verified against its exact numeric ID before hashing extracted article
    text. No credentials, alternate hosts, or HTML 403 bypass.
    """
    canonical = entry["url"]
    u = allowed_url(canonical)
    if u.hostname != "help.ui.com":
        raise ValueError("invalid_help_article_url")
    matched = re.fullmatch(r"/hc/en-us/articles/(\d+)(?:-[A-Za-z0-9-]+)?", u.path)
    if not matched or u.query:
        raise ValueError("invalid_help_article_url")
    article_id = int(matched.group(1))
    api_url = f"https://help.ui.com/api/v2/help_center/en-us/articles/{article_id}.json"
    allowed_url(api_url)
    _robot_ok(api_url, opener)
    req = request.Request(api_url, headers={"User-Agent":UA,"Accept":"application/json"})
    with opener.open(req, timeout=18) as response:
        if response.headers.get_content_type() != "application/json":
            raise ValueError("unexpected_content_type")
        data = response.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError("too_large")
    try:
        object_data = json.loads(data.decode("utf-8","strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_official_json") from exc
    article = object_data.get("article") if isinstance(object_data,dict) else None
    if not isinstance(article,dict) or type(article.get("id")) is not int or article["id"] != article_id:
        raise ValueError("official_article_id_mismatch")
    if article.get("draft") is not False:
        raise ValueError("official_article_not_published")
    if article.get("locale") not in ("en-us","en"):
        raise ValueError("official_article_locale_mismatch")
    body = article.get("body")
    title = article.get("title")
    if not isinstance(title,str) or len(title.strip()) < 4:
        raise ValueError("official_article_missing_title")
    if not isinstance(body,str) or len(body) < 100:
        raise ValueError("official_article_missing_body")
    # Limit to the exact public article's title and text: no navigation,
    # scripts, timestamps, external embedding or UI boilerplate. Do not
    # store the downloaded HTML body in this public repository.
    text = normalize(("<html><main>"+body+"</main></html>").encode("utf-8"))
    if metadata is not None:
        metadata.update({
            "fetch_method":"PUBLIC_ANONYMOUS_HELP_CENTER_API",
            "article_id":article_id,
            "title":title.strip()[:200],
            "vendor_updated_at":article.get("updated_at") if isinstance(article.get("updated_at"),str) else None,
            "body_word_count":len(text.split())
        })
    return ("<html><main>"+html.escape(title)+" "+html.escape(text)+"</main></html>").encode("utf-8")

def fetch(url, opener):
    allowed_url(url)
    _robot_ok(url, opener)
    req = request.Request(url, headers={"User-Agent":UA,"Accept":"text/html"})
    with opener.open(req, timeout=18) as response:
        if response.headers.get_content_type() not in ("text/html","application/xhtml+xml"):
            raise ValueError("unexpected_content_type")
        raw = response.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError("too_large")
    return raw

_VERSION = re.compile(r"\b(?:\d{1,3}\.){2,3}\d{1,4}\b")
_PRODUCT = re.compile(r"(?i)\bUniFi\s+(?:Network(?:\s+Application)?|OS(?:\s+Server)?|Protect|Access|Talk|Connect|Identity)\b")

def validate_content(entry, text):
    """Reject generic landing-page/nav-only HTML, especially JS-only release pages."""
    if entry.get("kind") != "release_rss" and len(text.split()) < 14:
        raise ValueError("content_too_sparse")
    if entry.get("kind") == "release_rss":
        # The exact product family/category/title/URL is checked by the
        # structured RSS parser and run() requires nonempty candidates.
        # Legacy _PRODUCT only recognizes Apps, not verified Switch or AP
        # firmware titles; do not reject genuine scoped RSS on that basis.
        if not _VERSION.search(text) or not ("UniFi" in text or "Enterprise Campus" in text):
            raise ValueError("release_rss_no_scoped_product_entries")
    if entry.get("kind") == "release_index":
        if not _PRODUCT.search(text) or not _VERSION.search(text) or not _CATALOG.extract(text,entry["url"]):
            raise ValueError("no_verifiable_release_entries")
    return text

def error_code(exc):
    if isinstance(exc, error.HTTPError):
        return "HTTP_"+str(exc.code)
    if isinstance(exc, error.URLError):
        return "NETWORK_ERROR"
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return "NETWORK_ERROR"
    if isinstance(exc, ValueError):
        msg = str(exc)
        if msg in {"not_html","unreadable_or_js_only","untrusted_source",
                   "robots_unavailable","robots_too_large","robots_disallowed",
                   "too_large","unexpected_content_type","content_too_sparse",
                   "no_verifiable_release_entries","unsafe_redirect","cross_host_redirect_disallowed",
                   "redirect_without_checked_robots","robots_disallowed_redirect",
                   "invalid_help_article_url","invalid_official_json",
                   "official_article_id_mismatch","official_article_not_published",
                   "official_article_locale_mismatch","official_article_missing_title",
                   "official_article_missing_body",
                   "invalid_developer_markdown_url","invalid_developer_markdown_utf8",
                   "invalid_developer_markdown_content",
                   "invalid_release_rss_url","invalid_release_rss_xml",
                   "invalid_release_rss_format","empty_release_rss",
                   "untrusted_release_item_url","duplicate_release_item",
                   "invalid_release_rss_pubdate","release_rss_title_slug_mismatch","release_rss_no_scoped_product_entries",
                   "release_rss_missing_structured_candidates"}:
            return msg.upper()
    return "FETCH_ERROR"

def run(fetcher=None, only=None):
    all_sources = load(ROOT/"sync/sources.json", {})["sources"]
    known = {s["id"] for s in all_sources}
    if len(known) != len(all_sources):
        raise ValueError("duplicate_source_id")
    selected = set(only) if only else known
    if not selected or selected - known:
        raise ValueError("unknown_or_empty_source_ids")
    sources = [s for s in all_sources if s["id"] in selected and s.get("enabled", True)]
    if not sources:
        raise ValueError("no_sources_selected")
    observed = load(ROOT/"sync/observed.json", {"schema_version":1, "sources":{}})
    pending = load(ROOT/"sync/pending.json", {"schema_version":1, "changes":{}})
    candidates = load(ROOT/"sync/version-candidates.json", {"schema_version":1, "sources":{}})
    opener = request.build_opener(SafeRedirect())
    results = []
    for entry in sources:
        key, url = entry["id"], entry["url"]
        status, detail = "ERROR", "UNKNOWN"
        evidence = {}
        transport = ("SYNTHETIC_FIXTURE" if fetcher else
                     "PUBLIC_ANONYMOUS_HELP_CENTER_API" if entry.get("kind")=="help_article" else
                     "PUBLIC_OFFICIAL_VERSIONED_DEVELOPER_MARKDOWN" if entry.get("kind")=="developer_markdown" else
                     "OFFICIAL_COMMUNITY_SCOPED_RELEASE_RSS" if entry.get("kind")=="release_rss" else "OFFICIAL_PUBLIC_HTML")
        try:
            allowed_url(url)
            if fetcher:
                raw = fetcher(entry)
            elif entry.get("kind")=="help_article":
                raw = fetch_public_help_article(entry, opener, metadata=evidence)
            elif entry.get("kind")=="developer_markdown":
                raw = fetch_official_developer_markdown(entry, opener, metadata=evidence)
            elif entry.get("kind")=="release_rss":
                raw = fetch_network_release_rss(entry, opener, metadata=evidence)
            else:
                raw = fetch(url, opener)
            value = validate_content(entry, normalize(raw))
            digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
            old = observed["sources"].get(key, {})
            previous = old.get("sha256") if old.get("url")==url else None
            status = "UNCHANGED" if previous == digest else ("FIRST_SEEN" if not previous else "CHANGED")
            release_candidates=evidence.pop("release_candidates",None)
            if entry.get("kind") == "release_rss" and not release_candidates:
                raise ValueError("release_rss_missing_structured_candidates")
            if entry.get("kind")=="release_rss":
                candidates["sources"][key] = {
                    "source_url":url, "source_sha256":digest,
                    "source_scope":RELEASE_RSS_SPECS[key]["scope"],
                    "release_channel":"UNKNOWN_NOT_VALIDATED_FROM_RSS",
                    "source_status":"VALIDATED_THIS_RUN",
                    "review_status":"CANDIDATES_NOT_VERIFIED",
                    "candidates":release_candidates or []
                }
            if entry.get("kind")=="release_index":
                candidates["sources"][key] = {
                    "source_url":url,
                    "source_sha256":digest,
                    "source_status":"VALIDATED_THIS_RUN",
                    "review_status":"CANDIDATES_NOT_VERIFIED",
                    "candidates":_CATALOG.extract(value,url)
                }
            # Commit the observation only after all source-specific
            # parsers and structured candidates have validated successfully.
            observed["sources"][key] = {"sha256":digest, "url":url, **evidence}
            if status != "UNCHANGED":
                pending["changes"][key] = {
                    "url":url, "modules":entry["modules"],"previous_sha256":previous,
                    "current_sha256":digest,"status":"REVIEW_REQUIRED",
                    "public_source_evidence":evidence
                }
            detail = "OK"
        except Exception as exc:
            # Never report FIRST_SEEN/CHANGED when a later validation,
            # indexing or candidate extraction step raises an exception.
            status = "ERROR"
            detail = error_code(exc)
            if entry.get("kind") in ("release_rss","release_index"):
                # Fail closed: a previously valid release list is historical,
                # not a current candidate feed after an unsuccessful fetch.
                # Preserve only its last successful digest/count for auditing;
                # do not re-publish its versions as current observations.
                previous_candidate = candidates["sources"].get(key,{})
                previous_count = previous_candidate.get(
                    "last_successful_candidate_count",
                    len(previous_candidate.get("candidates",[])))
                previous_sha = previous_candidate.get(
                    "last_successful_sha256",
                    previous_candidate.get("source_sha256"))
                candidates["sources"][key] = {
                    "source_url":url,
                    "source_status":"UNAVAILABLE_THIS_RUN",
                    "review_status":"NO_CURRENT_VERIFIABLE_CANDIDATES",
                    "failure_code":detail,
                    "candidates":[],
                    "last_successful_candidate_count":previous_count,
                    "last_successful_sha256":previous_sha,
                    "note":"Historical source fingerprint is NOT a current release or channel verification."
                }
            print(key+": "+detail,file=sys.stderr)
        results.append({"id":key,"status":status,"detail":detail,"url":url,"transport":transport})
    save(ROOT/"sync/observed.json", observed)
    save(ROOT/"sync/pending.json", pending)
    save(ROOT/"sync/version-candidates.json", candidates)
    # This file is intentionally deterministic; timestamped every-run commits create PR spam.
    release_unavailable = sorted(
        source["id"] for source in sources
        if source.get("kind") in ("release_rss","release_index")
        and candidates["sources"].get(source["id"],{}).get("source_status")=="UNAVAILABLE_THIS_RUN")
    health = {
        "schema_version":1,"monitored":len(results),
        "unavailable_release_candidate_sources":release_unavailable,
        "healthy":sum(x["status"]!="ERROR" for x in results),
        "failed":sum(x["status"]=="ERROR" for x in results),
        "freshness":"DEGRADED" if any(x["status"]=="ERROR" for x in results) else "SOURCES_RETRIEVED_UNREVIEWED",
        "results": results
    }
    save(ROOT/"sync/health.json", health)
    lines=["# UniFi 官方來源監測（未審核）","","**不是已驗證的最新 UniFi 知識。**","",
           f"來源：{health['monitored']}；成功：{health['healthy']}；失敗：{health['failed']}；狀態：{health['freshness']}","",
           "| 來源 | 抓取狀態 | 分類 | 官方 URL |","|---|---|---|---|"]
    for x in results:
        lines.append(f"| {x['id']} | {x['status']} | {x['detail']} | {x['url']} |")
    lines += ["",f"等待來源與知識審核：{len(pending['changes'])}","",
              "GitHub Actions 執行時間見 Workflow Run；此報告不自行核准任何摘要。",""]
    (ROOT/"sync/latest-observed.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({x["id"]:x["status"] for x in results},ensure_ascii=False))
    # A green run must mean every configured public source was validated.
    # 2 = all failed; 4 = partial degraded; 0 = all retrieved (not reviewed).
    return 2 if health["healthy"]==0 else (4 if health["failed"] else 0)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--only",nargs="+",help="Fixed official source IDs")
    args = p.parse_args()
    try:
        sys.exit(run(only=args.only))
    except (ValueError, KeyError) as exc:
        print("MONITOR_CONFIG_ERROR: "+str(exc),file=sys.stderr)
        sys.exit(3)
