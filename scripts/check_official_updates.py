#!/usr/bin/env python3
"""Read official public pages and record UNREVIEWED source digests."""
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from urllib import request, parse, robotparser
ROOT = Path(__file__).resolve().parents[1]
UA = "UniFiSkillPublicKnowledgeMonitor/0.4"
HOSTS = {"help.ui.com", "developer.ui.com", "community.ui.com"}
LIMIT = 1500000
def load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
def save(path, value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def normalize(raw):
    s=raw.decode("utf-8","replace")
    if "<html" not in s.lower(): raise ValueError("not_html")
    s=re.sub(r"(?is)<(script|style|noscript|svg|template)\b[^>]*>.*?</\1>", " ",s)
    match=re.search(r"(?is)<(main|article)\b[^>]*>(.*?)</\1>",s)
    if match:s=match.group(2)
    s=html.unescape(re.sub(r"(?s)<[^>]+>"," ",s))
    s=re.sub(r"\s+"," ",s).strip()
    if len(s)<100: raise ValueError("unreadable_or_js_only")
    return s
class SafeRedirect(request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        u=parse.urlsplit(newurl)
        if u.scheme!="https" or u.hostname not in HOSTS or u.username or u.password or u.port: raise ValueError("unsafe_redirect")
        return super().redirect_request(req,fp,code,msg,headers,newurl)
def fetch(url,opener):
    u=parse.urlsplit(url)
    if u.scheme!="https" or u.hostname not in HOSTS or u.username or u.password or u.port: raise ValueError("untrusted_source")
    robots=robotparser.RobotFileParser()
    robots.set_url("https://"+u.hostname+"/robots.txt")
    robots.read()
    if not robots.last_checked() or not robots.can_fetch(UA,url): raise ValueError("robots_not_verified_or_disallowed")
    req=request.Request(url,headers={"User-Agent":UA,"Accept":"text/html"})
    with opener.open(req,timeout=18) as response:
        if response.headers.get_content_type() not in ("text/html","application/xhtml+xml"): raise ValueError("unexpected_content_type")
        raw=response.read(LIMIT+1)
    if len(raw)>LIMIT: raise ValueError("too_large")
    return raw
def run(fetcher=None):
    sources=load(ROOT/"sync/sources.json",{})["sources"]
    observed=load(ROOT/"sync/observed.json",{"schema_version":1,"sources":{}})
    pending=load(ROOT/"sync/pending.json",{"schema_version":1,"changes":{}})
    opener=request.build_opener(SafeRedirect())
    result=[]
    for entry in sources:
        key=entry["id"]; url=entry["url"]
        try:
            digest=hashlib.sha256(normalize(fetcher(entry) if fetcher else fetch(url,opener)).encode()).hexdigest()
            previous=observed["sources"].get(key,{}).get("sha256")
            status="UNCHANGED" if digest==previous else ("FIRST_SEEN" if not previous else "CHANGED")
            observed["sources"][key]={"sha256":digest,"url":url}
            if status!="UNCHANGED":
                pending["changes"][key]={"url":url,"modules":entry["modules"],"previous_sha256":previous,"current_sha256":digest,"status":"REVIEW_REQUIRED"}
        except Exception as exc:
            status="ERROR"; print(key+": "+str(exc),file=sys.stderr)
        result.append((key,status))
    save(ROOT/"sync/observed.json",observed)
    save(ROOT/"sync/pending.json",pending)
    lines=["# UniFi 官方監測（未審核）","","此報告不代表已驗證的官方最新知識。","",
           "| 來源 | 狀態 | 官方網址 |","|---|---|---|"]
    lines += [f"| {key} | {status} | {next(e['url'] for e in sources if e['id']==key)} |" for key,status in result]
    lines += ["","待審核來源："+str(len(pending["changes"])),""]
    (ROOT/"sync/latest-observed.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps(dict(result),ensure_ascii=False))
    return 2 if all(s=="ERROR" for _,s in result) else 0
if __name__=="__main__": sys.exit(run())
