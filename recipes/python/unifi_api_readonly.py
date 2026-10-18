#!/usr/bin/env python3
"""UniFi Network v10.6.106 GET-only example; safe mock by default.

Live mode requires explicit --live, --site-id and private environment vars:
 UNIFI_NETWORK_BASE_URL (HTTPS official local Network integration root)
 UNIFI_API_KEY (do not put in CLI arguments or public files)
No TLS bypass, no redirects, no sensitive device-level output.
"""
import argparse
import json
import os
import ssl
import sys
from urllib import parse, request

class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect_refused_to_protect_api_key")

def make_opener():
    return request.build_opener(request.HTTPSHandler(context=ssl.create_default_context()),NoRedirect())

def fetch_page(base, site_id, key, offset, limit=100, opener=None):
    u=parse.urlsplit(base)
    if (u.scheme!="https" or not u.hostname or u.username or u.password or u.fragment
        or not u.path.endswith("/integration/v1")):
        raise ValueError("invalid_network_integration_root")
    if not site_id or "/" in site_id or "?" in site_id or "#" in site_id:
        raise ValueError("invalid_site_id")
    if not key:
        raise ValueError("api_key_required")
    if not (0 <= offset and 1 <= limit <= 100):
        raise ValueError("invalid_pagination")
    url=base.rstrip("/")+"/sites/"+parse.quote(site_id,safe="")+"/devices?offset="+str(offset)+"&limit="+str(limit)
    req=request.Request(url,headers={"X-API-Key":key,"Accept":"application/json"},method="GET")
    with (opener or make_opener()).open(req,timeout=15) as resp:
        if resp.headers.get_content_type()!="application/json":
            raise ValueError("unexpected_content_type")
        data=json.load(resp)
    if not isinstance(data,dict):
        raise ValueError("unexpected_response")
    return data

def collect_summary(fetch, limit=100, max_pages=50):
    """Page completeness strictly checked; never print IP/MAC/device names."""
    offset=0
    expected_total=None
    counts={}
    seen=0
    for _ in range(max_pages):
        page=fetch(offset,limit)
        if not isinstance(page,dict) or not isinstance(page.get("data"),list):
            raise ValueError("invalid_page")
        if not all(k in page for k in ("offset","limit","count","totalCount")):
            raise ValueError("missing_pagination_metadata")
        total=page["totalCount"]; actual=page["count"]
        if not all(type(v) is int for v in (total,actual,page["offset"],page["limit"])):
            raise ValueError("invalid_pagination_type")
        if total<0 or actual !=len(page["data"]) or page["offset"]!=offset or page["limit"]!=limit:
            raise ValueError("pagination_mismatch")
        if expected_total is None: expected_total=total
        elif expected_total!=total: raise ValueError("changing_total_count")
        if offset+actual>total or (actual==0 and offset<total):
            raise ValueError("incomplete_page")
        for obj in page["data"]:
            if not isinstance(obj,dict): raise ValueError("invalid_device")
            state=obj.get("state")
            status=state if state in ("ONLINE","OFFLINE","UPDATING","ADOPTING","ISOLATED") else "OTHER"
            counts[status]=counts.get(status,0)+1
        offset+=actual;seen+=actual
        if offset==total:
            return {"source":"UNIFI_NETWORK_READ_ONLY","complete":True,"total_devices":total,"states":counts}
    raise ValueError("max_pages_exceeded")

def mock_page(offset,limit):
    devices=[{"state":"ONLINE","name":"SYNTHETIC-A","macAddress":"00:00:00:00:00:00"},
             {"state":"OFFLINE","name":"SYNTHETIC-B"},{"state":"ONLINE","name":"SYNTHETIC-C"}]
    return {"offset":offset,"limit":limit,"count":len(devices[offset:offset+limit]),
            "totalCount":len(devices),"data":devices[offset:offset+limit]}

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--live",action="store_true",help="explicitly opt in to a private authorized Controller GET")
    p.add_argument("--site-id",help="only required in --live mode")
    args=p.parse_args(argv)
    if args.live:
        base=os.environ.get("UNIFI_NETWORK_BASE_URL","")
        key=os.environ.get("UNIFI_API_KEY","")
        if not args.site_id or not base or not key:
            p.error("live mode requires --site-id and private UNIFI_NETWORK_BASE_URL, UNIFI_API_KEY")
        result=collect_summary(lambda o,l:fetch_page(base,args.site_id,key,o,l))
    else:
        result=collect_summary(mock_page)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0
if __name__=="__main__":
    try:sys.exit(main())
    except Exception as exc:
        # No token/base URL/device data in public error output
        print("UniFi inventory failed: "+type(exc).__name__,file=sys.stderr)
        sys.exit(1)
