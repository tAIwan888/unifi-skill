"""Thousand DISTINCT release pointers, RSS rollover and fail-closed history tests."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from scripts import accumulate_release_pointer_history as h
from scripts import auto_release_triage as a

def pointer(i):
    sid=a.ALLOWED[i%len(a.ALLOWED)]
    uid=f'{i:08x}-0000-4000-8000-{i:012x}'
    title='UniFi Synthetic Product'
    version=f'5.{i//100}.{i%100}'
    url=f'https://community.ui.com/releases/UniFi-Synthetic-{version.replace(".","-")}/{uid}'
    pub='2026-10-19T09:00:00+00:00'
    base={'source_id':sid,'product_label':title,'version':version,
          'official_post_url':url,'publication_date':pub,
          'source_scope':'SYNTHETIC_UNIT_TEST_SCOPE'}
    sha=hashlib.sha256(json.dumps(base,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'id':sid+':'+uid,'release_uuid':uid,**base,'fingerprint_sha256':sha,
            'release_channel':'UNKNOWN_NOT_VERIFIED_BY_RSS',
            'device_upgrade_authorized':False}

def snapshot(rows):
    return {'schema_version':1,'mode':'AUTOMATIC_PUBLIC_RSS_TRIAGE_NO_APPROVAL',
            'inventory':rows,'alerts':[],
            'counts':{'sources_expected':7,'sources_valid':7,'exceptions':0,
                      'machine_indexed':len(rows)},
            'release_channels_approved':0,'device_models_approved':0,
            'may_drive_device_upgrades':False,'global_release_coverage_verified':False}

class HistoricalPointerLedger(unittest.TestCase):
    def test_thousand_unique_pointers_across_ten_small_rss_windows(self):
        history=None
        for j in range(10):
            window=snapshot([pointer(i) for i in range(j*100,(j+1)*100)])
            history=h.build(window,previous_history=history)
        self.assertEqual(history['counts']['historical_unique_pointers'],1000)
        self.assertEqual(history['counts']['observed_in_this_scan'],100)
        self.assertEqual(history['counts']['historical_not_in_current_rss_window'],900)
        self.assertEqual(history['counts']['newly_added_to_history'],100)
        self.assertTrue(history['historical_evidence_only'])
        self.assertFalse(history['all_versions_still_available'])
        self.assertFalse(history['may_drive_device_upgrades'])
        again=h.build(window,previous_history=history)
        self.assertEqual(again['counts']['newly_added_to_history'],0)
        self.assertEqual(again['counts']['historical_unique_pointers'],1000)

    def test_returning_old_pointer_does_not_repeat_first_seen(self):
        first=h.build(snapshot([pointer(0),pointer(1)]))
        second=h.build(snapshot([pointer(2)]),previous_history=first)
        third=h.build(snapshot([pointer(0),pointer(2)]),previous_history=second)
        self.assertEqual(third['counts']['newly_added_to_history'],0)
        self.assertEqual(third['counts']['historical_unique_pointers'],3)

    def test_first_rollout_recovers_previous_snapshot(self):
        old=snapshot([pointer(1),pointer(2)])
        current=snapshot([pointer(2),pointer(3)])
        ledger=h.build(current,previous_snapshot=old)
        self.assertEqual(ledger['counts']['historical_unique_pointers'],3)
        self.assertEqual(ledger['counts']['newly_added_to_history'],1)

    def test_metadata_tampering_fail_closed(self):
        current=snapshot([pointer(1)])
        history=h.build(current)
        bad=copy.deepcopy(history)
        bad['entries'][0]['version']='99.99.99'
        with self.assertRaisesRegex(ValueError,'history_fingerprint_mismatch'):
            h.build(current,previous_history=bad)
        altered=copy.deepcopy(current)
        altered['inventory'][0]['version']='99.99.99'
        with self.assertRaisesRegex(ValueError,'history_fingerprint_mismatch'):
            h.build(altered)

    def test_modified_official_pointer_requires_exception_review(self):
        prior=h.build(snapshot([pointer(1)]))
        current=snapshot([pointer(1)])
        current['inventory'][0]['product_label']='UniFi Changed Label'
        rec=current['inventory'][0]
        fp={k:rec[k] for k in h.FINGERPRINT_FIELDS}
        rec['fingerprint_sha256']=hashlib.sha256(json.dumps(
            fp,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError,'previously_observed_pointer_metadata_conflict'):
            h.build(current,previous_history=prior)

    def test_partial_unapproved_source_is_not_inserted_into_history(self):
        current=snapshot([pointer(1)])
        current['counts']['sources_valid']=6
        with self.assertRaisesRegex(ValueError,'snapshot_not_fully_validated_or_promoted'):
            h.build(current)
        current=snapshot([pointer(1)])
        current['release_channels_approved']=1
        with self.assertRaisesRegex(ValueError,'snapshot_not_fully_validated_or_promoted'):
            h.build(current)

    def test_duplicate_or_forged_historical_record_rejected(self):
        current=snapshot([pointer(1)])
        old=h.build(current)
        invalid=copy.deepcopy(old)
        invalid['entries'].append(invalid['entries'][0])
        with self.assertRaisesRegex(ValueError,'duplicate_prior_history_pointer'):
            h.build(current,previous_history=invalid)
        invalid=copy.deepcopy(old)
        invalid['entries'][0]['source_id']='unregistered'
        with self.assertRaisesRegex(ValueError,'history_unregistered_source'):
            h.build(current,previous_history=invalid)

    def test_cli_writes_unapproved_json_and_summary(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=root/'snapshot.json'
            source.write_text(json.dumps(snapshot([pointer(1)])))
            rc=h.main(['--snapshot',str(source),
                       '--output',str(root/'history.json'),
                       '--summary',str(root/'history.md')])
            self.assertEqual(rc,0)
            item=json.loads((root/'history.json').read_text())
            self.assertEqual(item['counts']['historical_unique_pointers'],1)
            self.assertIn('NOT a current release',(root/'history.md').read_text())

if __name__=='__main__':
    unittest.main()
