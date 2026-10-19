"""No-network validation for a permanent, unreviewed GitHub-only release history."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts import auto_release_triage as a
from scripts import accumulate_release_pointer_history as h
from scripts import validate_release_history_archive as archive

SHA='a'*40

def pointer(i):
    uid=f'{i:08x}-0000-4000-8000-{i:012x}'
    sid=a.ALLOWED[i%7]
    ver=f'5.{i//100}.{i%100}'
    fields={
        'source_id':sid,
        'product_label':'UniFi Synthetic Test Product',
        'version':ver,
        'official_post_url':'https://community.ui.com/releases/'+uid,
        'publication_date':'2026-10-19T09:00:00+00:00',
        'source_scope':'SYNTHETIC_TEST_SCOPE',
    }
    fingerprint=hashlib.sha256(json.dumps(
        fields,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'id':sid+':'+uid, 'release_uuid':uid,
            'fingerprint_sha256':fingerprint, **fields}

def snapshot(rows):
    return {
        'schema_version':1,
        'mode':'AUTOMATIC_PUBLIC_RSS_TRIAGE_NO_APPROVAL',
        'inventory':rows,
        'alerts':[],
        'counts':{'sources_expected':7,'sources_valid':7,'exceptions':0,
                  'machine_indexed':len(rows)},
        'release_channels_approved':0,'device_models_approved':0,
        'global_release_coverage_verified':False,
        'may_drive_device_upgrades':False,
    }

def provenance(data,run):
    return archive.verify(snapshot([pointer(0)]),data,run_id=run,commit_sha=SHA)[1]

class ArchiveSafety(unittest.TestCase):
    def test_first_scan_and_idempotent_replay(self):
        snap=snapshot([pointer(0),pointer(1)])
        incoming=h.build(snap)
        doc,prov=archive.verify(snap,incoming,run_id=101,commit_sha=SHA)
        self.assertEqual(prov['source_run_id'],101)
        self.assertEqual(prov['canonical_history_sha256'],archive.digest(doc))
        self.assertEqual(prov['release_channels_approved'],0)
        fresh=h.build(snap,previous_history=doc)
        later,p=archive.verify(snap,fresh,doc,prov,run_id=102,commit_sha=SHA)
        self.assertEqual(later['entries'],doc['entries'])
        self.assertEqual(later['counts']['newly_added_to_history'],0)
        self.assertEqual(p['source_run_id'],102)

    def test_archiving_lag_can_safely_catch_up(self):
        old_snap=snapshot([pointer(0)])
        old=h.build(old_snap)
        prov=archive.verify(old_snap,old,run_id=11,commit_sha=SHA)[1]
        # An intermediate scanner was successful, but its archive job
        # failed; incoming's delta is relative to that scanner, not old
        # archived history.
        intermediate=h.build(snapshot([pointer(0),pointer(1)]),previous_history=old)
        current=snapshot([pointer(0),pointer(1),pointer(2)])
        incoming=h.build(current,previous_history=intermediate)
        self.assertEqual(incoming['counts']['newly_added_to_history'],1)
        result,_=archive.verify(current,incoming,old,prov,run_id=13,commit_sha=SHA)
        self.assertEqual(len(result['entries']),3)

    def test_backwards_subset_rejected_without_mutation(self):
        old_snap=snapshot([pointer(0),pointer(1)])
        old=h.build(old_snap)
        prior=archive.verify(old_snap,old,run_id=21,commit_sha=SHA)[1]
        current=snapshot([pointer(0)])
        incoming=h.build(current)
        with self.assertRaisesRegex(ValueError,'archive_rollback_or_metadata_conflict'):
            archive.verify(current,incoming,old,prior,run_id=22,commit_sha=SHA)

    def test_same_id_changed_version_even_with_recomputed_fingerprint(self):
        snap=snapshot([pointer(0)])
        before=h.build(snap)
        prev=archive.verify(snap,before,run_id=30,commit_sha=SHA)[1]
        after=copy.deepcopy(before)
        entry=after['entries'][0]
        entry['version']='5.0.99'
        basis={k:entry[k] for k in h.FINGERPRINT_FIELDS}
        entry['fingerprint_sha256']=hashlib.sha256(json.dumps(
            basis,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError,'archive_current_snapshot_not_in_ledger'):
            archive.verify(snap,after,before,prev,run_id=31,commit_sha=SHA)

    def test_modified_archived_provenance_digest_blocks_new_run(self):
        snap=snapshot([pointer(0)])
        prior=h.build(snap)
        prov=archive.verify(snap,prior,run_id=41,commit_sha=SHA)[1]
        prov['canonical_history_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'archive_missing_or_invalid_prior_provenance'):
            archive.verify(snap,prior,prior,prov,run_id=42,commit_sha=SHA)

    def test_prior_run_id_must_be_lower(self):
        snap=snapshot([pointer(0)])
        prior=h.build(snap)
        prov=archive.verify(snap,prior,run_id=51,commit_sha=SHA)[1]
        with self.assertRaisesRegex(ValueError,'archive_missing_or_invalid_prior_provenance'):
            archive.verify(snap,prior,prior,prov,run_id=51,commit_sha=SHA)

    def test_reject_promoted_snapshot_or_history(self):
        snap=snapshot([pointer(0)])
        histdoc=h.build(snap)
        bad=copy.deepcopy(histdoc)
        bad['release_channels_approved']=1
        with self.assertRaisesRegex(ValueError,'archive_knowledge_promotion_forbidden'):
            archive.verify(snap,bad,run_id=65,commit_sha=SHA)
        snap['release_channels_approved']=1
        with self.assertRaisesRegex(ValueError,'snapshot_not_fully_validated_or_promoted'):
            archive.verify(snap,histdoc,run_id=65,commit_sha=SHA)

    def test_current_inventory_must_match_history(self):
        snap=snapshot([pointer(0),pointer(1)])
        missing=h.build(snapshot([pointer(0)]))
        with self.assertRaisesRegex(ValueError,'archive_snapshot_count_mismatch'):
            archive.verify(snap,missing,run_id=76,commit_sha=SHA)

    def test_unpaired_previous_archive_rejected(self):
        snap=snapshot([pointer(0)])
        incoming=h.build(snap)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'snapshot.json').write_text(json.dumps(snap))
            (root/'history.json').write_text(json.dumps(incoming))
            (root/'previous.json').write_text(json.dumps(incoming))
            code=archive.main(['--snapshot',str(root/'snapshot.json'),
                '--incoming',str(root/'history.json'),
                '--previous-history',str(root/'previous.json'),
                '--run-id','82','--commit-sha',SHA,
                '--output-history',str(root/'out.json'),
                '--output-provenance',str(root/'out-provenance.json')])
            self.assertEqual(code,2)
            self.assertFalse((root/'out.json').exists())

    def test_one_thousand_distinct_official_pointer_structures(self):
        history=None
        for i in range(0,1000,100):
            snap=snapshot([pointer(j) for j in range(i,i+100)])
            history=h.build(snap,previous_history=history)
        assert history is not None
        output,prov=archive.verify(snap,history,run_id=150,commit_sha=SHA)
        self.assertEqual(len(output['entries']),1000)
        self.assertEqual(output['counts']['historical_not_in_current_rss_window'],900)
        self.assertFalse(prov['all_product_coverage_verified'])

    def test_cli_writes_two_json_files(self):
        snap=snapshot([pointer(0)])
        incoming=h.build(snap)
        with tempfile.TemporaryDirectory() as d:
            r=Path(d)
            (r/'snapshot.json').write_text(json.dumps(snap))
            (r/'incoming.json').write_text(json.dumps(incoming))
            status=archive.main(['--snapshot',str(r/'snapshot.json'),
                '--incoming',str(r/'incoming.json'),
                '--run-id','209','--commit-sha',SHA,
                '--output-history',str(r/'archive-history.json'),
                '--output-provenance',str(r/'provenance.json')])
            self.assertEqual(status,0)
            info=json.loads((r/'provenance.json').read_text())
            self.assertEqual(info['source_run_id'],209)
            self.assertEqual(len(json.loads((r/'archive-history.json').read_text())['entries']),1)

if __name__ == '__main__':
    unittest.main()
