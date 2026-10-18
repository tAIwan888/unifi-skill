#!/usr/bin/env python3
"""Block promotion of sources with pending changes or without exact review digest."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
def read(root,name,key):
    return json.loads((root/'sync'/name).read_text(encoding='utf-8')).get(key,{})
def validate(root):
    observed=read(root,'observed.json','sources')
    pending=read(root,'pending.json','changes')
    reviewed=read(root,'reviewed.json','reviews')
    issues=[f'PENDING {k}' for k in sorted(pending)]
    for key,item in sorted(observed.items()):
        if reviewed.get(key,{}).get('sha256')!=item.get('sha256'):
            issues.append(f'MISSING_MATCHING_REVIEW {key}')
    return issues
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args()
    issues=validate(args.root)
    if issues:
        print('BLOCKED: '+'; '.join(issues),file=sys.stderr)
        sys.exit(1)
    print('PASS: no pending changes and every observed digest reviewed')
