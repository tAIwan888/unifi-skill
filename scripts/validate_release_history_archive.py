#!/usr/bin/env python3
"""Validate an UNREVIEWED public-RSS ledger before GitHub-only archival.

This is not a source fetcher or knowledge approval tool. Its only outputs
are sanitized JSON history/provenance files for an isolated GitHub branch.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from scripts import accumulate_release_pointer_history as hist
from scripts import auto_release_triage as triage

SHA40 = re.compile(r'[0-9a-f]{40}\Z')
MAX_RUN_ID = 10**20
SOURCE_NAME = 'UniFi automated scoped release triage (research only)'
KEYS = {'historical_unique_pointers', 'observed_in_this_scan',
        'historical_not_in_current_rss_window', 'newly_added_to_history',
        'history_capacity'}

def ensure(ok, error):
    if not ok:
        raise ValueError(error)

def read_ledger(data):
    ensure(isinstance(data, dict) and data.get('schema_version') == 1
           and data.get('kind') == hist.KIND
           and isinstance(data.get('entries'), list)
           and isinstance(data.get('counts'), dict)
           and set(data['counts']) == KEYS
           and len(data['entries']) <= hist.LIMIT,
           'archive_invalid_ledger_shape')
    entries = {}
    for item in data['entries']:
        rec = hist.validated_row(item)
        ensure(rec['id'] not in entries, 'archive_duplicate_entry')
        entries[rec['id']] = rec
    ensure([x['id'] for x in data['entries']] == sorted(entries),
           'archive_ledger_not_sorted')
    c = data['counts']
    ensure(c['historical_unique_pointers'] == len(entries)
           and c['history_capacity'] == hist.LIMIT
           and all(isinstance(c[k], int) and not isinstance(c[k], bool)
                   and c[k] >= 0 for k in KEYS)
           and c['observed_in_this_scan'] <= len(entries)
           and c['historical_not_in_current_rss_window']
               == len(entries) - c['observed_in_this_scan']
           and c['newly_added_to_history'] <= len(entries),
           'archive_invalid_count_claims')
    ensure(data.get('historical_evidence_only') is True
           and data.get('all_versions_still_available') is False
           and data.get('all_product_coverage_verified') is False
           and data.get('release_channels_approved') == 0
           and data.get('device_models_approved') == 0
           and data.get('may_drive_device_upgrades') is False,
           'archive_knowledge_promotion_forbidden')
    return entries

def digest(data):
    raw=json.dumps(data, sort_keys=True, separators=(',', ':'),
                   ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

def verify(snapshot, incoming, prior=None, prior_provenance=None,
           *, run_id: int, commit_sha: str):
    ensure(isinstance(run_id,int) and not isinstance(run_id,bool)
           and 0 < run_id < MAX_RUN_ID
           and isinstance(commit_sha,str) and SHA40.fullmatch(commit_sha),
           'archive_invalid_run_identity')
    current = hist.checked_snapshot(snapshot)
    incoming_items = read_ledger(incoming)
    ensure(incoming['counts']['observed_in_this_scan'] == len(current),
           'archive_snapshot_count_mismatch')
    ensure(all(key in incoming_items and incoming_items[key] == row
               for key, row in current.items()),
           'archive_current_snapshot_not_in_ledger')
    if prior is not None:
        prior_items = read_ledger(prior)
        ensure(isinstance(prior_provenance,dict)
               and prior_provenance.get('schema_version') == 1
               and prior_provenance.get('source_workflow') == SOURCE_NAME
               and prior_provenance.get('source_branch') == 'main'
               and isinstance(prior_provenance.get('source_run_id'),int)
               and 0 < prior_provenance['source_run_id'] < run_id
               and isinstance(prior_provenance.get('source_commit_sha'),str)
               and SHA40.fullmatch(prior_provenance['source_commit_sha'])
               and prior_provenance.get('canonical_history_sha256') == digest(prior),
               'archive_missing_or_invalid_prior_provenance')
        ensure(all(k in incoming_items and incoming_items[k] == rec
                   for k,rec in prior_items.items()),
               'archive_rollback_or_metadata_conflict')
        # The archive may legitimately lag behind successful scans if a
        # prior archival job failed. The scanner's new count is relative to
        # its last successful *scanner*, not our last committed archive.
        ensure(incoming['counts']['newly_added_to_history']
               <= len(incoming_items) - len(prior_items),
               'archive_new_count_exceeds_archive_growth')
    else:
        ensure(prior_provenance is None,'archive_unpaired_prior_provenance')
    provenance = {
        'schema_version': 1,
        'source_workflow': SOURCE_NAME,
        'source_branch': 'main',
        'source_run_id': run_id,
        'source_commit_sha': commit_sha,
        'canonical_history_sha256': digest(incoming),
        'archive_kind': 'UNREVIEWED_VENDOR_RSS_POINTER_HISTORY_ONLY',
        'all_product_coverage_verified': False,
        'release_channels_approved': 0,
        'device_upgrades_authorized': False,
    }
    return incoming, provenance

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot','incoming','output-history','output-provenance'):
        p.add_argument('--'+name, required=True, type=Path)
    p.add_argument('--previous-history', type=Path)
    p.add_argument('--previous-provenance', type=Path)
    p.add_argument('--run-id', type=int, required=True)
    p.add_argument('--commit-sha', required=True)
    args=p.parse_args(argv)
    try:
        hist_data=triage.load(args.incoming, maximum=4_000_000)
        snap=triage.load(args.snapshot, maximum=3_000_000)
        if bool(args.previous_history) != bool(args.previous_provenance):
            raise ValueError('archive_previous_files_must_be_paired')
        previous=(triage.load(args.previous_history, maximum=4_000_000)
                  if args.previous_history else None)
        prev_info=(triage.load(args.previous_provenance, maximum=50_000)
                   if args.previous_provenance else None)
        history, provenance=verify(snap,hist_data,previous,prev_info,
                                   run_id=args.run_id,commit_sha=args.commit_sha)
        for path,content in ((args.output_history,history),
                             (args.output_provenance,provenance)):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(content,sort_keys=True,indent=2,
                                       ensure_ascii=False)+'\n',encoding='utf-8')
        print('RELEASE_HISTORY_ARCHIVE_VALIDATED',
              json.dumps({'pointers':len(history['entries']),
                          'source_run_id':args.run_id},sort_keys=True))
        return 0
    except (ValueError,TypeError,KeyError,OSError,UnicodeError) as exc:
        print('RELEASE_HISTORY_ARCHIVE_REJECTED '+str(exc),file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
