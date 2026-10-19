#!/usr/bin/env python3
"""Accept only machine-observed public source metadata; never release knowledge."""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
_SCOPE_SPEC=importlib.util.spec_from_file_location('machine_scope',Path(__file__).resolve().parent/'source_monitoring_scope.py')
scope=importlib.util.module_from_spec(_SCOPE_SPEC);_SCOPE_SPEC.loader.exec_module(scope)
KINDS={
 'help_article':('help.ui.com','PUBLIC_ANONYMOUS_HELP_CENTER_API'),
 'developer_markdown':('developer.ui.com','PUBLIC_OFFICIAL_VERSIONED_DEVELOPER_MARKDOWN'),
 'release_rss':('community.ui.com','OFFICIAL_COMMUNITY_SCOPED_RELEASE_RSS')}
TAG='MACHINE_SOURCE_OBSERVED_UNREVIEWED_NOT_DEVICE_APPROVED'
SHA=re.compile(r'[0-9a-f]{64}\Z')

def req(condition,message):
 if not condition: raise ValueError(message)

def load(root,name):
 return json.loads((root/'sync'/name).read_text(encoding='utf8'))

def safe_url(url,host):
 try:
  p=urlsplit(url)
  return (isinstance(url,str) and p.scheme=='https' and p.hostname==host
          and p.port is None and p.username is None and p.password is None
          and not p.fragment and not any(x in url for x in (' ',chr(10),chr(13),chr(96),'<','>','|')))
 except (ValueError,TypeError): return False

def verified(root):
 cat=load(root,'sources.json')['sources']
 scope.validate_catalog(cat)
 obs=load(root,'observed.json')['sources']
 pending=load(root,'pending.json')['changes']
 health=load(root,'health.json')
 release=load(root,'version-candidates.json')['sources']
 reviewed=load(root,'reviewed.json')
 req(reviewed=={'schema_version':1,'reviews':{}},'no_manual_review_records_permitted')
 by_id={s['id']:s for s in cat}
 hs={s['id']:s for s in health['results']}
 req(len(by_id)==len(cat)==len(hs)==health['monitored']
     and set(by_id)==set(hs) and len(cat)>=1,'source_or_health_coverage_mismatch')
 req(health['healthy']==sum(s['status']!='ERROR' for s in hs.values())
     and health['failed']==sum(s['status']=='ERROR' for s in hs.values())
     and health['freshness']==('DEGRADED' if health['failed'] else 'SOURCES_RETRIEVED_UNREVIEWED'),
     'source_health_counts_inconsistent')
 if any(key in health for key in scope.FIELDS):
  scope.validate_health(cat,health,full=True)
 req(set(obs)<=set(by_id) and set(pending)<=set(by_id),'unknown_source_in_evidence')
 good={}
 for sid,source in sorted(by_id.items()):
  h=hs[sid]
  req(h['url']==source['url'] and h['status'] in ('ERROR','UNCHANGED','CHANGED','FIRST_SEEN'),
      'source_health_identity_mismatch:'+sid)
  if h['status']=='ERROR':
   req(sid not in pending,'failed_source_cannot_be_accepted:'+sid)
   continue
  kind=source['kind']
  req(kind in KINDS,'unrecognised_successful_source_kind:'+sid)
  host,method=KINDS[kind]
  row=obs.get(sid,{})
  req(safe_url(source['url'],host)
      and h.get('detail')=='OK' and h.get('transport')==method
      and row.get('url')==source['url']
      and isinstance(row.get('sha256'),str) and SHA.fullmatch(row['sha256']),
      'source_fingerprint_not_verified:'+sid)
  metadata={k:v for k,v in row.items() if k not in ('url','sha256')}
  req(metadata.get('fetch_method')==method,'untrusted_parser:'+sid)
  modules=source['modules']
  req(isinstance(modules,list) and modules
      and all(isinstance(m,str) and re.fullmatch(r'M(?:0[1-9]|10)',m) for m in modules),
      'invalid_module_scope:'+sid)
  if kind=='help_article':
   m=re.fullmatch(r'/hc/en-us/articles/(\d+)(?:-[A-Za-z0-9-]+)?',urlsplit(source['url']).path)
   req(m and metadata.get('article_id')==int(m.group(1))
       and isinstance(metadata.get('title'),str) and len(metadata['title'])>=4
       and type(metadata.get('body_word_count')) is int
       and metadata['body_word_count']>=14,'unverified_official_article:'+sid)
  elif kind=='developer_markdown':
   m=re.fullmatch(r'/(network|protect|site-manager)/v(\d+(?:\.\d+){2,3})/ai-gettingstarted\.md',
                  urlsplit(source['url']).path)
   req(m and metadata.get('doc_version')==m.group(2)
       and source.get('doc_version')==m.group(2)
       and metadata.get('api_family')==m.group(1)
       and metadata.get('version_scope')=='PINNED_DOCUMENT_NOT_LATEST'
       and type(metadata.get('body_word_count')) is int
       and metadata['body_word_count']>=14,'unverified_pinned_document:'+sid)
  elif kind=='release_rss':
   c=release.get(sid,{})
   req(c.get('source_url')==source['url']
       and c.get('source_sha256')==row['sha256']
       and c.get('source_scope')==source.get('product_scope')
       and c.get('source_status')=='VALIDATED_THIS_RUN'
       and c.get('review_status')=='CANDIDATES_NOT_VERIFIED'
       and c.get('release_channel')=='UNKNOWN_NOT_VALIDATED_FROM_RSS'
       and metadata.get('product_scope')==source.get('product_scope')
       and metadata.get('channel_scope')=='CHANNEL_UNVERIFIED_MANUAL_REVIEW_REQUIRED'
       and isinstance(c.get('candidates'),list)
       and 1<=len(c['candidates'])<=50
       and metadata.get('candidate_count')==len(c['candidates']),
       'unverified_scoped_release_feed:'+sid)
   for item in c['candidates']:
    link=item.get('source_url')
    req(safe_url(link,'community.ui.com')
        and re.fullmatch(r'/releases/(?:[A-Za-z0-9-]+/)?[0-9a-fA-F-]{36}',urlsplit(link).path)
        and item.get('release_channel')=='UNKNOWN_NOT_VALIDATED_FROM_RSS'
        and item.get('verification')=='CANDIDATE_UNREVIEWED',
        'rss_release_channel_or_url_not_safe:'+sid)
  if sid in pending:
   change=pending[sid]
   req(change.get('status')=='REVIEW_REQUIRED'
       and change.get('current_sha256')==row['sha256']
       and change.get('url')==source['url']
       and change.get('modules')==modules
       and isinstance(change.get('public_source_evidence'),dict)
       and all(change['public_source_evidence'].get(k)==v
               for k,v in metadata.items() if k!='vendor_updated_at'),
       'pending_evidence_conflict:'+sid)
  good[sid]={'source_url':source['url'],'source_sha256':row['sha256'],
             'source_kind':kind,'modules':modules,'public_source_evidence':metadata,
             'classification':TAG,'knowledge_approved':False,
             'release_channel_approved':False,'device_upgrade_authorized':False}
 req(len(good)==health['healthy'] and good,'machine_observation_count_mismatch')
 return good,pending

def run(root,accept=False):
 good,pending=verified(root)
 result={'schema_version':1,'mode':'AUTOMATED_PUBLIC_SOURCE_METADATA_ONLY',
         'observations':good}
 target=root/'sync/machine-accepted.json'
 if accept:
  # Atomic validation before any write; source data, not knowledge or review records.
  # Preserve the original bytes when the newly verified evidence is
  # semantically identical. Avoid no-op Draft PRs caused only by JSON
  # key ordering or indentation differences on every scheduled run.
  if not target.exists() or load(root,'machine-accepted.json')!=result:
   target.write_text(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf8')
  pending_file=root/'sync/pending.json'
  if pending:
   pending_file.write_text('{\n  "changes": {},\n  "schema_version": 1\n}\n',encoding='utf8')
  # Keep the human-readable snapshot consistent after reconciliation.
  report=root/'sync/latest-observed.md'
  if report.exists():
   prior=report.read_text(encoding='utf8')
   updated=re.sub(r'等待來源與知識審核：\d+',
       '已機器核對來源觀測：'+str(len(good))+'；不需真人來源簽核；知識／發布渠道／設備升級核准：0',
       prior)
   report.write_text(updated,encoding='utf8')
 else:
  req(load(root,'machine-accepted.json')==result,'machine_ledger_not_equal_current_sources')
  req(not pending,'unreconciled_machine_observations')
 return len(good)

def main(argv=None):
 p=argparse.ArgumentParser()
 p.add_argument('--root',type=Path,default=ROOT)
 p.add_argument('--accept',action='store_true')
 args=p.parse_args(argv)
 try:
  n=run(args.root,args.accept)
  print('MACHINE_SOURCE_OBSERVATIONS_PASS:',n,'sources; zero knowledge/channel/upgrade approvals')
  return 0
 except (ValueError,KeyError,TypeError,OSError,AttributeError) as e:
  print('MACHINE_SOURCE_OBSERVATIONS_BLOCKED:',str(e),file=sys.stderr)
  return 2

if __name__=='__main__': sys.exit(main())
