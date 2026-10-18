#!/usr/bin/env python3
"""Human-reviewed promotion of a specific official-source digest.

Never called from an automated sync workflow. Requires reviewer, notes, and
an updated citation-bearing Markdown file inside the public skill repository.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
def approve(root,source,digest,reviewer,notes,evidence):
    if not re.fullmatch(r'[a-f0-9]{64}',digest):raise ValueError('invalid digest')
    if not (2<=len(reviewer.strip())<=120):raise ValueError('reviewer required')
    if not (10<=len(notes.strip())<=2000):raise ValueError('review notes required')
    pp=root/'sync/pending.json';rp=root/'sync/reviewed.json';op=root/'sync/observed.json'
    pending=json.loads(pp.read_text());reviewed=json.loads(rp.read_text());observed=json.loads(op.read_text())
    change=pending['changes'].get(source)
    if not change:raise ValueError('source not pending')
    if change['current_sha256']!=digest:raise ValueError('pending digest differs')
    if observed['sources'].get(source,{}).get('sha256')!=digest:raise ValueError('observed digest differs')
    if not evidence:raise ValueError('evidence Markdown is required')
    valid=[]
    for supplied in evidence:
        actual=(root/supplied).resolve();rel=actual.relative_to(root.resolve()).as_posix()
        if not actual.is_file() or actual.suffix!='.md' or not rel.startswith(('modules/','runbooks/','decisions/','docs/')):
            raise ValueError('evidence must be a module/runbook/decision/doc Markdown')
        if change['url'] not in actual.read_text(encoding='utf8'):raise ValueError('precise source URL missing: '+rel)
        valid.append(rel)
    reviewed.setdefault('reviews',{})[source]={
        'sha256':digest,'reviewer':reviewer.strip(),'reviewed_at':datetime.now(timezone.utc).isoformat(),
        'notes':notes.strip(),'evidence_files':sorted(set(valid)),'source_url':change['url']}
    del pending['changes'][source]
    rp.write_text(json.dumps(reviewed,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf8')
    pp.write_text(json.dumps(pending,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf8')
    return valid
if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',required=True);ap.add_argument('--digest',required=True)
    ap.add_argument('--reviewer',required=True);ap.add_argument('--notes',required=True)
    ap.add_argument('--evidence',required=True,nargs='+')
    ap.add_argument('--root',type=Path,default=ROOT)
    a=ap.parse_args()
    try:print('REVIEWED:',','.join(approve(a.root,a.source,a.digest,a.reviewer,a.notes,a.evidence)))
    except (ValueError,OSError,KeyError,TypeError) as e:
        print('REVIEW REJECTED: '+str(e),file=sys.stderr);sys.exit(2)
