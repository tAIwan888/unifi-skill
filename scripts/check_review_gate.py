#!/usr/bin/env python3
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def data(p,k):return json.loads((root/"sync"/p).read_text()).get(k,{})
observed=data("observed.json","sources")
pending=data("pending.json","changes")
reviewed=data("reviewed.json","reviews")
bad=[k for k,v in observed.items() if reviewed.get(k,{}).get("sha256") != v.get("sha256")]
if bad or pending:
 print("BLOCKED: sources without approval", sorted(set(bad)|set(pending)),file=sys.stderr)
 sys.exit(1)
print("PASS: no unreviewed official changes")
