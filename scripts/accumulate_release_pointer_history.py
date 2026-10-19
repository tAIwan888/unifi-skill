#!/usr/bin/env python3
"""Append-only unapproved historical RSS pointer index, solely from validated triage.

The rolling RSS inventory proves a public pointer was observed during a scan,
NOT that a firmware remains available, suitable or Official/stable.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

from scripts import auto_release_triage as a

KIND = 'PUBLIC_SCOPED_RSS_POINTER_HISTORY_UNREVIEWED'
FIELDS = (
    'id', 'release_uuid', 'source_id', 'product_label', 'version',
    'official_post_url', 'publication_date', 'source_scope',
    'fingerprint_sha256',
)
FINGERPRINT_FIELDS = (
    'source_id', 'product_label', 'version', 'official_post_url',
    'publication_date', 'source_scope',
)
LIMIT = 5000

def require(ok, error):
    if not ok:
        raise ValueError(error)

def validated_row(item):
    require(isinstance(item, dict), 'history_entry_not_object')
    require(all(isinstance(item.get(k), str) for k in FIELDS),
            'history_entry_missing_required_field')
    sid = item['source_id']
    require(sid in a.ALLOWED, 'history_unregistered_source')
    scope = item['source_scope']
    require(3 <= len(scope) <= 100, 'history_invalid_scope')
    candidate = {
        'product_label': item['product_label'],
        'version': item['version'],
        'source_url': item['official_post_url'],
        'publication_date': item['publication_date'],
        'verification': 'CANDIDATE_UNREVIEWED',
        'release_channel': 'UNKNOWN_NOT_VALIDATED_FROM_RSS',
    }
    check = a.product_scope_record(candidate, sid, scope)
    for key in ('id', 'release_uuid', 'source_id', 'product_label', 'version',
                'official_post_url', 'publication_date', 'source_scope'):
        require(check[key] == item[key], 'history_record_identity_drift')
    basis = {k: item[k] for k in FINGERPRINT_FIELDS}
    fp = hashlib.sha256(json.dumps(basis, sort_keys=True,
                       separators=(',', ':')).encode('utf-8')).hexdigest()
    require(item['fingerprint_sha256'] == fp, 'history_fingerprint_mismatch')
    return {k: item[k] for k in FIELDS}

def checked_snapshot(data):
    require(isinstance(data, dict) and data.get('schema_version') == 1
            and data.get('mode') == 'AUTOMATIC_PUBLIC_RSS_TRIAGE_NO_APPROVAL',
            'invalid_snapshot_identity')
    counts = data.get('counts')
    require(isinstance(counts, dict) and isinstance(data.get('inventory'), list)
            and isinstance(data.get('alerts'), list),
            'invalid_snapshot_structure')
    require(counts.get('sources_expected') == len(a.ALLOWED)
            and counts.get('sources_valid') == len(a.ALLOWED)
            and counts.get('exceptions') == 0
            and counts.get('machine_indexed') == len(data['inventory'])
            and not data['alerts']
            and data.get('release_channels_approved') == 0
            and data.get('device_models_approved') == 0
            and data.get('may_drive_device_upgrades') is False
            and data.get('global_release_coverage_verified') is False,
            'snapshot_not_fully_validated_or_promoted')
    require(len(data['inventory']) <= a.LIMIT, 'snapshot_inventory_too_large')
    out = {}
    for item in data['inventory']:
        rec = validated_row(item)
        require(rec['id'] not in out, 'snapshot_duplicate_pointer_id')
        out[rec['id']] = rec
    return out

def build(current_snapshot, previous_history=None, previous_snapshot=None):
    current = checked_snapshot(current_snapshot)
    old = {}
    if previous_history is not None:
        require(isinstance(previous_history, dict)
                and previous_history.get('schema_version') == 1
                and previous_history.get('kind') == KIND
                and isinstance(previous_history.get('entries'), list),
                'invalid_prior_history')
        require(len(previous_history['entries']) <= LIMIT,
                'prior_history_exceeds_limit')
        for item in previous_history['entries']:
            row = validated_row(item)
            require(row['id'] not in old, 'duplicate_prior_history_pointer')
            old[row['id']] = row
    elif previous_snapshot is not None:
        # Backwards-compatible first rollout: older successful Runner artifacts
        # contain a current inventory but no historical pointer file.
        old = checked_snapshot(previous_snapshot)
    added = 0
    for key, row in current.items():
        if key not in old:
            old[key] = row
            added += 1
        else:
            require(old[key] == row, 'previously_observed_pointer_metadata_conflict')
    require(len(old) <= LIMIT, 'history_limit_reached_fail_closed')
    entries = [old[k] for k in sorted(old)]
    return {
        'schema_version': 1, 'kind': KIND, 'entries': entries,
        'counts': {
            'historical_unique_pointers': len(entries),
            'observed_in_this_scan': len(current),
            'historical_not_in_current_rss_window': len(old) - len(current),
            'newly_added_to_history': added,
            'history_capacity': LIMIT,
        },
        'historical_evidence_only': True,
        'all_versions_still_available': False,
        'all_product_coverage_verified': False,
        'release_channels_approved': 0,
        'device_models_approved': 0,
        'may_drive_device_upgrades': False,
    }

def summary(result):
    c = result['counts']
    return '\n'.join((
        '## Historical public RSS pointers (UNREVIEWED)',
        '',
        '- Cumulative distinct pointers: ' + str(c['historical_unique_pointers']),
        '- Observed in latest valid RSS scan: ' + str(c['observed_in_this_scan']),
        '- Only in history (not current RSS window): ' +
            str(c['historical_not_in_current_rss_window']),
        '- Added to historical index this scan: ' + str(c['newly_added_to_history']),
        '- A historical pointer is NOT a current release, Official channel, '
          'download proof or device-model compatibility approval.',
        '',
    ))

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot', required=True, type=Path)
    p.add_argument('--previous-history', type=Path)
    p.add_argument('--previous-snapshot', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--summary', required=True, type=Path)
    args=p.parse_args(argv)
    try:
        current=a.load(args.snapshot, maximum=3_000_000)
        prior=a.load(args.previous_history, maximum=4_000_000) if args.previous_history else None
        baseline=a.load(args.previous_snapshot, maximum=3_000_000) if args.previous_snapshot else None
        result=build(current, prior, baseline)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,sort_keys=True,
                               ensure_ascii=False)+'\n',encoding='utf-8')
        args.summary.write_text(summary(result),encoding='utf-8')
        print('PUBLIC_RSS_HISTORY_UNREVIEWED',json.dumps(result['counts'],sort_keys=True))
        return 0
    except (ValueError,TypeError,KeyError,OSError,UnicodeError) as exc:
        print('PUBLIC_RSS_HISTORY_FAIL_CLOSED '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':
    sys.exit(main())
