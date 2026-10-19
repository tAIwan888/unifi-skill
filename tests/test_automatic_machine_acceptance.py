"""Fail-closed, offline machine acceptance of public source METADATA only."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts import auto_accept_source_observations as m

ROOT=Path(__file__).resolve().parents[1]
SOURCES=('sources.json','observed.json','pending.json','health.json',
         'version-candidates.json','reviewed.json','machine-accepted.json')

class PublicSourceMachineGate(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)
  (self.root/'sync').mkdir()
  for name in SOURCES:
   shutil.copyfile(ROOT/'sync'/name,self.root/'sync'/name)

 def load(self,name):
  return json.loads((self.root/'sync'/name).read_text(encoding='utf8'))

 def save(self,name,value):
  (self.root/'sync'/name).write_text(json.dumps(value),encoding='utf8')

 def test_29_scoped_machine_sources_pass_without_human_reviewer(self):
  before=(self.root/'sync/reviewed.json').read_bytes()
  self.assertEqual(m.run(self.root,accept=False),29)
  self.assertEqual((self.root/'sync/reviewed.json').read_bytes(),before)
  doc=self.load('machine-accepted.json')
  self.assertEqual(len(doc['observations']),29)
  self.assertTrue(all(not r['knowledge_approved'] and
                      not r['device_upgrade_authorized']
                      for r in doc['observations'].values()))
  self.assertNotIn('official_releases',doc['observations'])
  self.assertNotIn('software_downloads',doc['observations'])

 def test_reconcile_pending_automatically_without_mutating_reviews(self):
  source='unifi_updates'
  pending=self.load('pending.json')
  observed=self.load('observed.json')['sources'][source]
  src=next(x for x in self.load('sources.json')['sources'] if x['id']==source)
  pending['changes'][source]={'status':'REVIEW_REQUIRED',
    'current_sha256':observed['sha256'],'url':observed['url'],
    'modules':src['modules'],
    'public_source_evidence':{k:v for k,v in observed.items() if k not in ('sha256','url')}}
  self.save('pending.json',pending)
  old=(self.root/'sync/reviewed.json').read_bytes()
  self.assertEqual(m.run(self.root,accept=True),29)
  self.assertEqual(self.load('pending.json')['changes'],{})
  self.assertEqual((self.root/'sync/reviewed.json').read_bytes(),old)
  self.assertEqual(m.run(self.root,accept=False),29)

 def test_metadata_forgery_rejected(self):
  obs=self.load('observed.json')
  obs['sources']['unifi_updates']['article_id']=1234
  self.save('observed.json',obs)
  with self.assertRaisesRegex(ValueError,'unverified_official_article'):
   m.run(self.root,accept=True)

 def test_digest_changed_without_receipt_rejected(self):
  obs=self.load('observed.json')
  obs['sources']['access']['sha256']='a'*64
  self.save('observed.json',obs)
  with self.assertRaisesRegex(ValueError,'machine_ledger_not_equal_current_sources'):
   m.run(self.root,accept=False)

 def test_release_channel_must_remain_unknown(self):
  release=self.load('version-candidates.json')
  release['sources']['cloud_keys_release_rss']['candidates'][0]['release_channel']='Official'
  self.save('version-candidates.json',release)
  with self.assertRaisesRegex(ValueError,'rss_release_channel_or_url_not_safe'):
   m.run(self.root,accept=True)

 def test_failed_global_source_cannot_be_promoted(self):
  health=self.load('health.json')
  target=next(x for x in health['results'] if x['id']=='official_releases')
  target['status']='UNCHANGED'
  target['detail']='OK'
  self.save('health.json',health)
  with self.assertRaisesRegex(ValueError,'source_health_counts_inconsistent'):
   m.run(self.root,accept=True)

 def test_unauthorized_vendor_release_cannot_be_accepted(self):
  release=self.load('version-candidates.json')
  release['sources']['cloud_keys_release_rss']['source_status']='UNAVAILABLE_THIS_RUN'
  self.save('version-candidates.json',release)
  with self.assertRaisesRegex(ValueError,'unverified_scoped_release_feed'):
   m.run(self.root,accept=True)

 def test_no_fake_human_review_record(self):
  reviewed=self.load('reviewed.json')
  reviewed['reviews']['access']={'reviewer':'bot'}
  self.save('reviewed.json',reviewed)
  with self.assertRaisesRegex(ValueError,'no_manual_review_records_permitted'):
   m.run(self.root,accept=True)

 def test_inconsistent_pending_cannot_be_silently_removed(self):
  pending=self.load('pending.json')
  pending['changes']['access']={
   'status':'REVIEW_REQUIRED','current_sha256':'f'*64,
   'url':'https://help.ui.com/bogus','modules':['M07']}
  self.save('pending.json',pending)
  with self.assertRaisesRegex(ValueError,'pending_evidence_conflict'):
   m.run(self.root,accept=True)
  self.assertIn('access',self.load('pending.json')['changes'])

 def test_scanner_metadata_mutation_writes_no_knowledge_files(self):
  prior=(self.root/'sync/reviewed.json').read_bytes()
  self.assertEqual(m.run(self.root,accept=True),29)
  self.assertEqual((self.root/'sync/reviewed.json').read_bytes(),prior)
  self.assertFalse((self.root/'modules').exists())
  self.assertFalse((self.root/'scripts').exists())

if __name__=='__main__':unittest.main()
