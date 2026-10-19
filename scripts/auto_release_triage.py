#!/usr/bin/env python3
"""Automatic, exception-only triage of official public UniFi release RSS.

Normal validated pointers flow to an unapproved machine-indexed inventory without
manual entry. Official/RC/EA channel, per-model compatibility and global/latest
status remain UNKNOWN unless independent, approved machine evidence exists.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

SHA = re.compile(r'[0-9a-f]{64}\Z')
VERSION = re.compile(r'\d{1,3}(?:\.\d{1,4}){2,3}\Z')
UUID = r'[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}'
POST = re.compile(rf'/releases/(?:[A-Za-z0-9-]{{2,110}}/)?({UUID})\Z')
ALLOWED = (
    'network_application_release_rss', 'protect_application_release_rss',
    'os_server_release_rss', 'dream_machines_release_rss',
    'wifi_firmware_release_rss', 'switch_firmware_release_rss',
    'cloud_keys_release_rss',
)
LIMIT = 3000


def require(condition, code):
    if not condition:
        raise ValueError(code)


def load(path, maximum=2_000_000):
    require(path.stat().st_size <= maximum, 'input_exceeds_bound')
    return json.loads(path.read_text(encoding='utf-8'))


def product_scope_record(candidate, source_id, source_scope):
    """Check a vendor-hosted release pointer's identity; don't infer models."""
    require(isinstance(candidate, dict), 'candidate_not_object')
    require(candidate.get('verification') == 'CANDIDATE_UNREVIEWED'
            and candidate.get('release_channel') == 'UNKNOWN_NOT_VALIDATED_FROM_RSS',
            'candidate_claims_unverified_approval')
    product = candidate.get('product_label')
    version = candidate.get('version')
    url = candidate.get('source_url')
    require(isinstance(product, str) and 3 <= len(product) <= 105
            and not any(c in product for c in '<>\r\n'), 'invalid_product_label')
    require(isinstance(version, str) and VERSION.fullmatch(version), 'invalid_version')
    require(isinstance(url, str), 'invalid_post_url')
    u = urlsplit(url)
    require(u.scheme == 'https' and u.netloc == 'community.ui.com'
            and not u.username and not u.password and not u.query and not u.fragment,
            'untrusted_post_host')
    match = POST.fullmatch(u.path)
    require(match is not None, 'untrusted_post_path')
    stamp = candidate.get('publication_date')
    require(isinstance(stamp, str), 'missing_publication_date')
    try:
        pub = datetime.fromisoformat(stamp)
    except ValueError as exc:
        raise ValueError('invalid_publication_date') from exc
    require(pub.tzinfo is not None and 2020 <= pub.year <= 2100,
            'invalid_publication_date')
    uuid = match.group(1).lower()
    key = source_id + ':' + uuid
    # A product label can contain model names but does not establish a complete
    # or per-hardware verified list. It is an RSS heading, not compatibility.
    return {
        'id': key, 'release_uuid': uuid, 'source_id': source_id,
        'product_label': product, 'version': version, 'source_scope': source_scope,
        'official_post_url': url, 'publication_date': pub.isoformat(),
        'pointer_evidence': 'OFFICIAL_HOSTED_RSS_METADATA_VALIDATED',
        'release_channel': 'UNKNOWN_NOT_VERIFIED_BY_RSS',
        'hardware_compatibility': 'NOT_VERIFIED_FROM_RELEASE_NOTES',
        'download_integrity': 'NOT_VERIFIED',
        'is_latest_official': False, 'is_globally_complete': False,
        'device_upgrade_authorized': False,
    }


def triage(catalog, observed, health, report, previous=None):
    require(isinstance(catalog, dict) and isinstance(catalog.get('sources'), list),
            'bad_catalog')
    require(isinstance(observed, dict) and isinstance(observed.get('sources'), dict),
            'bad_observed')
    require(isinstance(report, dict) and isinstance(report.get('sources'), dict),
            'bad_candidate_report')
    require(isinstance(health, dict) and isinstance(health.get('results'), list),
            'bad_source_health')
    by_id = {x['id']: x for x in catalog['sources'] if isinstance(x, dict) and 'id' in x}
    require(len(by_id) == len(catalog['sources']), 'duplicate_catalog_source_id')
    checks = {x['id']: x for x in health['results'] if isinstance(x, dict) and 'id' in x}
    require(len(checks) == len(health['results']), 'duplicate_health_source_id')
    prior = {}
    if previous is not None:
        require(isinstance(previous, dict)
                and previous.get('schema_version') == 1
                and previous.get('mode') == 'AUTOMATIC_PUBLIC_RSS_TRIAGE_NO_APPROVAL'
                and isinstance(previous.get('inventory'), list), 'invalid_prior_snapshot')
        for item in previous['inventory']:
            require(isinstance(item, dict) and isinstance(item.get('id'), str)
                    and isinstance(item.get('fingerprint_sha256'), str)
                    and SHA.fullmatch(item['fingerprint_sha256']),
                    'invalid_prior_entry')
            require(item['id'] not in prior, 'duplicate_previous_id')
            prior[item['id']] = item
    inventory, events, alerts, source_states = [], [], [], []
    seen_uuid = {}
    rejected_cross_source_uuids = set()
    for sid in ALLOWED:
        cfg = by_id.get(sid)
        require(cfg is not None and cfg.get('kind') == 'release_rss'
                and cfg.get('enabled') is True and isinstance(cfg.get('product_scope'), str),
                'unregistered_or_invalid_rss_source:' + sid)
        src = report['sources'].get(sid)
        h = checks.get(sid)
        o = observed['sources'].get(sid)
        if (not isinstance(src, dict) or not isinstance(h, dict) or not isinstance(o, dict)
                or h.get('status') == 'ERROR'
                or src.get('source_status') != 'VALIDATED_THIS_RUN'):
            reason = 'SOURCE_UNAVAILABLE_NO_CURRENT_VERIFICATION'
            alerts.append({'source_id': sid, 'reason': reason})
            source_states.append({'source_id': sid, 'status': 'UNAVAILABLE_OR_DEGRADED'})
            continue
        src_sha = src.get('source_sha256')
        if (h.get('status') not in ('UNCHANGED', 'FIRST_SEEN', 'CHANGED')
                or h.get('detail') != 'OK'
                or h.get('transport') != 'OFFICIAL_COMMUNITY_SCOPED_RELEASE_RSS'
                or src.get('source_url') != cfg['url'] or h.get('url') != cfg['url']
                or o.get('url') != cfg['url']
                or not isinstance(src_sha, str) or not SHA.fullmatch(src_sha)
                or src_sha != o.get('sha256')
                or src.get('source_scope') != cfg['product_scope']
                or src.get('review_status') != 'CANDIDATES_NOT_VERIFIED'
                or o.get('fetch_method') != 'OFFICIAL_COMMUNITY_SCOPED_RELEASE_RSS'
                or o.get('product_scope') != cfg['product_scope']):
            alerts.append({'source_id': sid, 'reason': 'SOURCE_PROVENANCE_OR_SCOPE_DRIFT'})
            source_states.append({'source_id': sid, 'status': 'REJECTED_SOURCE_EVIDENCE'})
            continue
        group = src.get('candidates')
        if (not isinstance(group, list) or not 1 <= len(group) <= 50
                or o.get('candidate_count') != len(group)):
            alerts.append({'source_id': sid, 'reason': 'INVALID_OR_EMPTY_RSS_CANDIDATES'})
            source_states.append({'source_id': sid, 'status': 'REJECTED_SOURCE_EVIDENCE'})
            continue
        provisional = []
        try:
            keys = set()
            for candidate in group:
                row = product_scope_record(candidate, sid, cfg['product_scope'])
                require(row['id'] not in keys, 'DUPLICATE_POST_IN_SOURCE')
                keys.add(row['id'])
                provisional.append(row)
        except (TypeError, ValueError) as exc:
            # A single malicious/malformed item invalidates the source batch;
            # do not quietly salvage selected items from compromised evidence.
            alerts.append({'source_id': sid, 'reason': 'REJECTED_CANDIDATE_BATCH:' + str(exc)})
            source_states.append({'source_id': sid, 'status': 'REJECTED_SOURCE_EVIDENCE'})
            continue
        for row in provisional:
            uuid = row['release_uuid']
            if uuid in rejected_cross_source_uuids:
                # A third feed must not resurrect a UUID already rejected
                # due to inconsistent official metadata in two feeds.
                continue
            prior_match = seen_uuid.get(uuid)
            if prior_match and any(prior_match[field] != row[field] for field in (
                    'version', 'product_label', 'official_post_url', 'publication_date')):
                alerts.append({'source_id': sid, 'reason': 'CROSS_SOURCE_RELEASE_UUID_CONFLICT',
                               'release_uuid': uuid})
                rejected_cross_source_uuids.add(uuid)
                # Remove both the index entry and its previously emitted
                # change event: rejected data must not count as a new release.
                inventory[:] = [x for x in inventory if x['release_uuid'] != uuid]
                events[:] = [ev for ev in events if not ev['id'].endswith(':' + uuid)]
                continue
            seen_uuid[uuid] = row
            basis = {k: row[k] for k in (
                'source_id', 'product_label', 'version', 'official_post_url',
                'publication_date', 'source_scope'
            )}
            row['fingerprint_sha256'] = hashlib.sha256(json.dumps(
                basis, separators=(',', ':'), sort_keys=True).encode('utf-8')).hexdigest()
            old = prior.get(row['id'])
            if old is None:
                kind = 'NEW_OFFICIAL_RSS_POINTER'
            elif old['fingerprint_sha256'] != row['fingerprint_sha256']:
                kind = 'POINTER_METADATA_CHANGED_RECHECK_REQUIRED'
                alerts.append({'source_id': sid, 'reason': kind, 'id': row['id']})
            else:
                kind = 'UNCHANGED_NO_REVIEW_NEEDED'
            if kind != 'UNCHANGED_NO_REVIEW_NEEDED':
                events.append({'id': row['id'], 'event': kind})
            inventory.append(row)
        source_states.append({'source_id': sid, 'status': 'SCOPED_METADATA_VALIDATED',
                              'candidate_count': len(provisional), 'source_sha256': src_sha})
    require(len(inventory) <= LIMIT, 'inventory_exceeds_bound')
    active_sources = {s['source_id'] for s in source_states
                      if s['status'] == 'SCOPED_METADATA_VALIDATED'}
    current_ids = {x['id'] for x in inventory}
    for key, row in prior.items():
        if row.get('source_id') in active_sources and key not in current_ids:
            events.append({'id': key, 'event': 'OUT_OF_RSS_WINDOW_NOT_WITHDRAWAL'})
    inventory.sort(key=lambda x: (x['source_id'], x['id']))
    events.sort(key=lambda x: (x['event'], x['id']))
    alerts.sort(key=lambda x: (x['source_id'], x['reason'], x.get('id', '')))
    return {
        'schema_version': 1, 'mode': 'AUTOMATIC_PUBLIC_RSS_TRIAGE_NO_APPROVAL',
        'inventory': inventory, 'events': events, 'alerts': alerts,
        'source_states': source_states,
        'counts': {'machine_indexed': len(inventory), 'new_or_changed_events': len(events),
                   'exceptions': len(alerts), 'sources_valid': len(active_sources),
                   'sources_expected': len(ALLOWED)},
        'release_channels_approved': 0, 'device_models_approved': 0,
        'global_release_coverage_verified': False, 'may_drive_device_upgrades': False,
    }


def render_summary(data):
    totals = data['counts']
    lines = [
        '# Automatic UniFi release change triage (no release approvals)', '',
        '**Public official RSS pointers, not Official/stable certifications or hardware compatibility.**', '',
        f"- Machine-indexed current pointers: {totals['machine_indexed']}",
        f"- Sources with validated scoped metadata: {totals['sources_valid']} / {totals['sources_expected']}",
        f"- Changed / newly observed / window-expired events: {totals['new_or_changed_events']}",
        f"- Exceptions requiring investigation: {totals['exceptions']}",
        '- Normal unchanged pointers need **zero manual review**.',
        '- Channel / exact device-model compatibility / downloads remain unknown until independent official evidence.',
        '- A post missing from a rolling RSS window does **not** mean the release was revoked.',
        '- Global Release Index and Downloads coverage are not repaired by these scoped feeds.', '',
        '## Exception queue', ''
    ]
    if data['alerts']:
        lines.extend(f"- `{a['source_id']}` — `{a['reason']}`" for a in data['alerts'])
    else:
        lines.append('None. This does not assert that all releases are globally covered.')
    lines.extend(['', '## Change events', ''])
    if data['events']:
        lines.extend(f"- `{ev['event']}` — `{ev['id']}`" for ev in data['events'][:100])
        if len(data['events']) > 100:
            lines.append(f"- … and {len(data['events'])-100} additional events in the JSON artifact.")
    else:
        lines.append('No additions or changes relative to the supplied previous snapshot.')
    lines.append('')
    return '\n'.join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog', type=Path, required=True)
    p.add_argument('--observed', type=Path, required=True)
    p.add_argument('--health', type=Path, required=True)
    p.add_argument('--source-report', type=Path, required=True)
    p.add_argument('--previous', type=Path)
    p.add_argument('--fail-on-alerts', action='store_true',
                   help='Fail the GitHub job on any triage exception after saving evidence')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--summary', type=Path, required=True)
    args = p.parse_args(argv)
    try:
        result = triage(load(args.catalog), load(args.observed), load(args.health),
                        load(args.source_report), load(args.previous) if args.previous else None)
        data = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
        text = render_summary(result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data, encoding='utf-8')
        args.summary.write_text(text, encoding='utf-8')
        print('AUTOMATIC_RELEASE_TRIAGE', json.dumps(result['counts'], sort_keys=True))
        if args.fail_on_alerts and (
                result['alerts'] or result['counts']['sources_valid'] != result['counts']['sources_expected']):
            print('AUTOMATIC_RELEASE_TRIAGE_EXCEPTIONS_BLOCKED', file=sys.stderr)
            return 2
        return 0
    except (ValueError, KeyError, TypeError, OSError, UnicodeError) as exc:
        print('AUTOMATIC_RELEASE_TRIAGE_FAIL_CLOSED ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
