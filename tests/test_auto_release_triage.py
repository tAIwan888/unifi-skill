"""1000-pointer scale and fail-closed source/metadata behavior, entirely offline."""
import copy
from datetime import datetime, timezone, timedelta
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import auto_release_triage as a


def fixture(per_feed=1):
    catalog={'sources':[]}; obs={'sources':{}};health={'results':[]};report={'sources':{}}
    for sid in a.ALLOWED:
        url='https://community.ui.com/rss/releases/UniFi-Test-'+sid+'/00000000-0000-4000-8000-000000000000'
        scope='SCOPE_'+sid.upper()
        catalog['sources'].append({'id':sid,'kind':'release_rss','enabled':True,'url':url,'product_scope':scope})
        sha=hashlib.sha256(sid.encode()).hexdigest()
        obs['sources'][sid]={'url':url,'sha256':sha,'fetch_method':'OFFICIAL_COMMUNITY_SCOPED_RELEASE_RSS','product_scope':scope,'candidate_count':per_feed}
        health['results'].append({'id':sid,'url':url,'status':'UNCHANGED','detail':'OK','transport':'OFFICIAL_COMMUNITY_SCOPED_RELEASE_RSS'})
        candidates=[]
        for i in range(per_feed):
            unique = (a.ALLOWED.index(sid)*per_feed+i)
            uid=f'{unique:08x}-0000-4000-8000-{unique:012x}'
            version='5.1.'+str(i%90)
            candidates.append({'product_label':'UniFi Test '+sid, 'version':version,
               'source_url':'https://community.ui.com/releases/UniFi-Test-'+sid.replace('_','-')+'-'+version.replace('.','-')+'/'+uid,
               'publication_date':'2026-10-18T10:00:00+00:00',
               'release_channel':'UNKNOWN_NOT_VALIDATED_FROM_RSS',
               'verification':'CANDIDATE_UNREVIEWED'})
        report['sources'][sid]={'source_url':url,'source_sha256':sha,'source_scope':scope,
         'source_status':'VALIDATED_THIS_RUN','review_status':'CANDIDATES_NOT_VERIFIED','candidates':candidates}
    return catalog,obs,health,report

class AutoTriage(unittest.TestCase):
    def test_all_sources_auto_index_no_manual_queue(self):
        b=fixture(20)
        d=a.triage(*b)
        self.assertEqual(d['counts']['machine_indexed'],140)
        self.assertEqual(d['counts']['exceptions'],0)
        self.assertEqual(d['counts']['sources_valid'],7)
        self.assertFalse(d['may_drive_device_upgrades'])
        self.assertTrue(all(x['release_channel']=='UNKNOWN_NOT_VERIFIED_BY_RSS'
                            and x['hardware_compatibility']=='NOT_VERIFIED_FROM_RELEASE_NOTES'
                            and x['device_upgrade_authorized'] is False for x in d['inventory']))
    def test_repeat_1000_changes_without_any_per_item_human_steps(self):
        b=fixture(20); prior=a.triage(*b)
        for i in range(1000):
            data=a.triage(*b,previous=prior)
            self.assertEqual(data['counts']['new_or_changed_events'],0)
            self.assertEqual(data['counts']['exceptions'],0)
        self.assertEqual(data['counts']['machine_indexed'],140)
    def test_incremental_new_and_dropped_are_not_official_withdrawal(self):
        b=fixture(2); prior=a.triage(*b)
        sid=a.ALLOWED[0]
        c=b[3]['sources'][sid]['candidates']
        c.pop(0)
        c.append({**c[0], 'source_url':c[0]['source_url'].replace('00000001-','00000101-').replace('-5-1-1/','-5-1-98/'), 'version':'5.1.98'})
        out=a.triage(*b,previous=prior)
        self.assertIn('OUT_OF_RSS_WINDOW_NOT_WITHDRAWAL',{x['event'] for x in out['events']})
        self.assertIn('NEW_OFFICIAL_RSS_POINTER',{x['event'] for x in out['events']})
        self.assertEqual(out['counts']['exceptions'],0)
    def test_source_failure_does_not_publish_stale_versions(self):
        b=fixture(2);prev=a.triage(*b)
        sid=a.ALLOWED[0]
        b[2]['results'][0]['status']='ERROR'
        b[3]['sources'][sid].update(source_status='UNAVAILABLE_THIS_RUN',candidates=[])
        out=a.triage(*b,previous=prev)
        self.assertEqual(out['counts']['machine_indexed'],12)
        self.assertEqual(out['counts']['exceptions'],1)
        self.assertFalse(any(x['source_id']==sid for x in out['inventory']))
        self.assertFalse(any(x['event']=='OUT_OF_RSS_WINDOW_NOT_WITHDRAWAL'
                             for x in out['events'] if x['id'].startswith(sid+':')))
    def test_provenance_drift_discards_whole_source(self):
        b=fixture(2);b[3]['sources'][a.ALLOWED[0]]['source_sha256']='0'*64
        d=a.triage(*b)
        self.assertEqual(d['counts']['machine_indexed'],12)
        self.assertEqual(d['counts']['exceptions'],1)
        self.assertIn('SOURCE_PROVENANCE_OR_SCOPE_DRIFT',d['alerts'][0]['reason'])
    def test_untrusted_candidate_invalidates_whole_source(self):
        for key,value in [('release_channel','Official'),('verification','APPROVED'),
                          ('source_url','https://evil.test/releases/a'),('version','latest')]:
            b=fixture(2);b[3]['sources'][a.ALLOWED[0]]['candidates'][0][key]=value
            with self.subTest(key=key):
                out=a.triage(*b)
                self.assertEqual(out['counts']['machine_indexed'],12)
                self.assertEqual(out['counts']['exceptions'],1)
    def test_metadata_change_is_exception_not_auto_approval(self):
        b=fixture(1);prior=a.triage(*b)
        b[3]['sources'][a.ALLOWED[0]]['candidates'][0]['product_label']='UniFi Test New Label'
        d=a.triage(*b,previous=prior)
        self.assertIn('POINTER_METADATA_CHANGED_RECHECK_REQUIRED',{x['event'] for x in d['events']})
        self.assertEqual(d['counts']['exceptions'],1)
        self.assertFalse(d['may_drive_device_upgrades'])
    def test_invalid_previous_and_duplicate_catalog_fail_closed(self):
        b=fixture(1)
        with self.assertRaisesRegex(ValueError,'invalid_prior_snapshot'):
            a.triage(*b,previous={'inventory':[]})
        b[0]['sources'].append(b[0]['sources'][0])
        with self.assertRaisesRegex(ValueError,'duplicate_catalog_source_id'):
            a.triage(*b)
    def test_cli_synthetic_files_creates_machine_inventory(self):
        b=fixture(2)
        with tempfile.TemporaryDirectory() as root:
            d=pathlib.Path(root)
            paths=[]
            for i,x in enumerate(b):
                p=d/(str(i)+'.json');p.write_text(json.dumps(x));paths.append(p)
            code=a.main(['--catalog',str(paths[0]),'--observed',str(paths[1]),
                         '--health',str(paths[2]),'--source-report',str(paths[3]),
                         '--output',str(d/'inventory.json'),'--summary',str(d/'summary.md')])
            self.assertEqual(code,0)
            self.assertEqual(json.loads((d/'inventory.json').read_text())['counts']['machine_indexed'],14)
            self.assertIn('zero manual review', (d/'summary.md').read_text())

if __name__=='__main__':unittest.main()
