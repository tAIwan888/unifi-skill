"""31-source offline parser/pipeline integration, never live Runner acceptance."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlsplit
import uuid

from scripts import auto_accept_source_observations as machine
from scripts import build_review_triage as triage
from scripts import render_source_monitoring_status as status_doc
from scripts import source_monitoring_scope as scope
from scripts import validate_release_candidate_evidence as evidence

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("required_scope_monitor",ROOT/"scripts/check_official_updates.py")
monitor=importlib.util.module_from_spec(spec);spec.loader.exec_module(monitor)
CATALOG=json.loads((ROOT/"sync/sources.json").read_text())["sources"]
TITLES={
    "network_application_release_rss":"UniFi Network Application 19.8.7",
    "protect_application_release_rss":"UniFi Protect Application 19.8.7",
    "os_server_release_rss":"UniFi OS Server 19.8.7",
    "dream_machines_release_rss":"UniFi OS - Dream Machines 19.8.7",
    "cloud_keys_release_rss":"UniFi OS - Cloud Keys 19.8.7",
    "wifi_firmware_release_rss":"UniFi Access Point & Wireless Bridge 19.8.7",
    "switch_firmware_release_rss":"UniFi Switch 19.8.7",
}
FILES=("machine-accepted.json","observed.json","pending.json","latest-observed.md",
       "health.json","version-candidates.json","legacy-network-apt-status.json","review-triage.md")

def read(root,name):return json.loads((root/"sync"/name).read_text())
def save(root,name,obj):(root/"sync"/name).write_text(json.dumps(obj))

def shell_step(name):
    workflow=(ROOT/".github/workflows/official-knowledge-sync.yml").read_text()
    block=workflow.split("      - name: "+name+"\n",1)[1].split("\n      - ",1)[0]
    return textwrap.dedent(block.split("        run: |\n",1)[1]).strip()+"\n"

class Response:
    status=200
    def __init__(self,raw,ctype):
        self.raw=raw
        self.headers=type("Headers",(),{"get_content_type":lambda self:ctype})()
    def read(self,n):return self.raw[:n]
    def __enter__(self):return self
    def __exit__(self,*args):return False

class OfficialFixtureOpener:
    """Independent published-article/Markdown/XML payloads at catalog URLs."""
    def __init__(self,failed=(),readable_optional=False):
        self.failed=set(failed);self.calls=[];self.readable_optional=readable_optional
        self.routes={}
        for entry in CATALOG:
            url=entry["url"]
            if entry["kind"]=="help_article":
                aid=re.search(r"/articles/(\d+)",url).group(1)
                url="https://help.ui.com/api/v2/help_center/en-us/articles/"+aid+".json"
            self.routes[url]=entry
    def open(self,req,timeout=0):
        url=req.full_url;self.calls.append(url)
        if urlsplit(url).path=="/robots.txt":return Response(b"User-agent: *\nDisallow:\n","text/plain")
        entry=self.routes[url];sid=entry["id"]
        if sid in self.failed:raise HTTPError(url,503,"Synthetic outage",{},None)
        kind=entry["kind"]
        if kind=="help_article":
            aid=int(re.search(r"/articles/(\d+)",entry["url"]).group(1))
            obj={"article":{"id":aid,"draft":False,"locale":"en-us",
                "title":"Synthetic UniFi public article for offline integration",
                "body":"<p>"+"Synthetic public documentation with no deployment authorization. "*30+"</p>",
                "updated_at":"2026-10-01T00:00:00Z"}}
            return Response(json.dumps(obj).encode(),"application/json")
        if kind=="developer_markdown":
            family={"network":"Network","site-manager":"Site Manager","protect":"Protect"}[urlsplit(url).path.split('/')[1]]
            body="# Synthetic UniFi "+family+" documentation\n"+"Offline integration document, not a real product capability. "*30
            return Response(body.encode(),"text/markdown")
        if kind=="release_rss":
            cat=monitor.RELEASE_RSS_SPECS[sid]["category"]
            link="https://community.ui.com/releases/"+str(uuid.uuid5(uuid.NAMESPACE_URL,sid))
            title=TITLES[sid].replace('&','&amp;')
            raw=("<rss><channel><item><title>"+title+"</title><category>"+cat+"</category><link>"+link+
                 "</link><pubDate>Thu, 01 Oct 2026 00:00:00 GMT</pubDate></item></channel></rss>")
            return Response(raw.encode(),"application/rss+xml")
        if self.readable_optional:
            raw="<html><main>"+"UniFi Network Application 19.8.7 Release Notes and Download. "*30+"</main></html>"
        elif sid=="official_releases":raw="<html><main>JavaScript navigation</main></html>"
        else:raw="<html><main>"+"Browse our navigation for products and support. "*30+"</main></html>"
        return Response(raw.encode(),"text/html")

class RequiredMonitoringScope(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/"sync").mkdir()
        save(self.root,"sources.json",{"sources":copy.deepcopy(CATALOG)})
        for name,obj in {
            "observed.json":{"schema_version":1,"sources":{}},
            "pending.json":{"schema_version":1,"changes":{}},
            "version-candidates.json":{"schema_version":1,"sources":{}},
            "reviewed.json":{"schema_version":1,"reviews":{}},
            "machine-accepted.json":{"schema_version":1,"mode":"AUTOMATED_PUBLIC_SOURCE_METADATA_ONLY","observations":{}},
            "legacy-network-apt-status.json":{"classification":"SYNTHETIC_NOT_PGP_VERIFIED"},
        }.items():save(self.root,name,obj)

    def scan(self,failed=(),readable_optional=False):
        op=OfficialFixtureOpener(failed,readable_optional)
        with patch.object(monitor,"ROOT",self.root),patch.object(monitor.request,"build_opener",return_value=op),patch.dict(monitor._ROBOTS_CACHE,{},clear=True):
            result=monitor.run()
        self.assertEqual(sum(urlsplit(u).path!="/robots.txt" for u in op.calls),31)
        return result

    def reconcile(self):
        count=machine.run(self.root,accept=True)
        (self.root/"sync/review-triage.md").write_text(triage.build(self.root))
        self.assertEqual(evidence.validate(self.root),[])
        return count

    def scan_guard(self,code):
        output=self.root/"github-output"
        output.write_text("")
        p=subprocess.run(["python3",str(ROOT/"scripts/source_monitoring_scope.py"),"--root",str(self.root),
                          "--github-output",str(output),"--expected-exit-code",str(code)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        return output.read_text()

    def final_workflow_step(self,degraded):
        if not degraded:return 0
        p=subprocess.run(["bash","-c",shell_step("Flag degraded source health")],capture_output=True,text=True)
        return p.returncode

    def test_optional_global_pages_fail_without_blocking_29_required(self):
        reviewed=(self.root/"sync/reviewed.json").read_bytes()
        self.assertEqual(self.scan(),0)
        h=read(self.root,"health.json")
        self.assertEqual((h['monitored'],h['healthy'],h['failed'],h['freshness']),(31,29,2,'DEGRADED'))
        self.assertEqual((h['required_total'],h['required_healthy'],h['required_failed']),(29,29,0))
        self.assertEqual((h['optional_total'],h['optional_healthy'],h['optional_failed']),(2,0,2))
        self.assertEqual(h['operational_status'],'REQUIRED_SOURCES_PASS_WITH_OPTIONAL_GAPS')
        self.assertEqual(self.reconcile(),29)
        self.assertEqual(self.scan_guard(0),'degraded=false\n')
        self.assertEqual(self.final_workflow_step(False),0)
        self.assertEqual((self.root/"sync/reviewed.json").read_bytes(),reviewed)
        for sid in scope.OPTIONAL_SOURCES:
            row=read(self.root,"version-candidates.json")['sources'][sid]
            self.assertEqual(row['source_status'],'UNAVAILABLE_THIS_RUN')
            self.assertEqual(row['candidates'],[])
            self.assertNotIn(sid,read(self.root,'machine-accepted.json')['observations'])

    def test_any_required_source_fails(self):
        self.assertEqual(self.scan(),0);self.reconcile()
        self.assertEqual(self.scan(['access']),4)
        h=read(self.root,'health.json');self.assertEqual(h['required_failed'],1)
        self.assertEqual(self.reconcile(),28)
        self.assertEqual(self.scan_guard(4),'degraded=true\n')
        self.assertEqual(self.final_workflow_step(True),2)
        # Even hypothetical successful optional pages cannot conceal the outage.
        rows=copy.deepcopy(h['results'])
        for row in rows:
            if row['id'] in scope.OPTIONAL_SOURCES:row['status']='UNCHANGED'
        derived=scope.summarize(CATALOG,rows)
        self.assertEqual(derived['optional_failed'],0)
        self.assertEqual(scope.exit_code(derived),4)

    def test_all_required_sources_fail(self):
        self.assertEqual(self.scan(),0);self.reconcile()
        failed=[e['id'] for e in CATALOG if scope.source_role(e)==scope.REQUIRED]
        self.assertEqual(self.scan(failed),2)
        self.assertEqual(read(self.root,'health.json')['required_failed'],29)
        with self.assertRaisesRegex(ValueError,'machine_observation_count_mismatch'):
            self.reconcile()
        self.assertEqual(self.scan_guard(2),'degraded=true\n')
        self.assertEqual(self.final_workflow_step(True),2)
        # The unchanged, trusted publisher must not run on a failed reader.
        workflow=(ROOT/'.github/workflows/official-knowledge-sync.yml').read_text()
        self.assertIn("needs.monitor.result == 'success'",workflow)
        env={**os.environ,'RUNNER_TEMP':str(self.root/'runner-temp')}
        (self.root/'runner-temp').mkdir()
        p=subprocess.run(['bash','-c',shell_step('Stage only eight public evidence files for independent writer job')],cwd=self.root,env=env,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(len(list((self.root/'runner-temp/public-evidence').iterdir())),8)
        self.assertEqual(json.loads((self.root/'runner-temp/public-evidence/health.json').read_text())['required_failed'],29)

    def test_cannot_mark_arbitrary_source_optional(self):
        cases=[]
        for sid in ('access','cloud_keys_release_rss','network_api'):
            c=copy.deepcopy(CATALOG);next(e for e in c if e['id']==sid)['monitoring_role']=scope.OPTIONAL;cases.append(c)
        for field,value in [('url','https://community.ui.com/releases'),('kind','help_article'),('enabled',False)]:
            c=copy.deepcopy(CATALOG);next(e for e in c if e['id']=='official_releases')[field]=value;cases.append(c)
        c=copy.deepcopy(CATALOG);c[1]['monitoring_role']='optional_reference_only';cases.append(c)
        c=copy.deepcopy(CATALOG);c[1]['enabled']=False;cases.append(c)
        for catalog in cases:
            with self.subTest(catalog=catalog[0]):
                save(self.root,'sources.json',{'sources':catalog})
                before=(self.root/'sync/observed.json').read_bytes()
                with patch.object(monitor,'ROOT',self.root),patch.object(monitor,'fetch') as fetcher:
                    with self.assertRaises(ValueError):monitor.run()
                fetcher.assert_not_called()
                self.assertEqual((self.root/'sync/observed.json').read_bytes(),before)

    def test_global_optional_metadata_never_becomes_approved_release(self):
        self.assertEqual(self.scan(readable_optional=True),0)
        h=read(self.root,'health.json')
        for row in h['results']:
            if row['id'] in scope.OPTIONAL_SOURCES:
                self.assertEqual(row['status'],'ERROR')
                self.assertEqual(row['detail'],'GLOBAL_RELEASE_MANIFEST_UNVERIFIED')
        self.reconcile()
        self.assertEqual(read(self.root,'reviewed.json')['reviews'],{})
        for rec in read(self.root,'machine-accepted.json')['observations'].values():
            self.assertFalse(rec['knowledge_approved'])
            self.assertFalse(rec['release_channel_approved'])
            self.assertFalse(rec['device_upgrade_authorized'])

    def test_historical_fail_closed_unchanged(self):
        historical=ROOT/'docs/evidence/official-sync-39228248994-health.json'
        original=historical.read_bytes()
        self.assertNotIn('operational_status',json.loads(original))
        self.assertEqual(json.loads(original)['freshness'],'DEGRADED')
        self.scan();self.reconcile()
        self.assertEqual(historical.read_bytes(),original)
        self.assertIn('39228248994',status_doc.render())
        self.assertIn('歷史結果沒有改成 PASS',status_doc.render())

    def test_noop_scan_no_extra_commit(self):
        self.scan();self.reconcile()  # FIRST_SEEN
        self.scan();self.reconcile()  # UNCHANGED, now steady
        receipt=read(self.root,'machine-accepted.json')
        (self.root/'sync/machine-accepted.json').write_text(json.dumps(receipt,indent=4))
        before={f:(self.root/'sync'/f).read_bytes() for f in FILES}
        for _ in range(2):
            self.assertEqual(self.scan(),0);self.assertEqual(self.reconcile(),29)
            self.assertEqual({f:(self.root/'sync'/f).read_bytes() for f in FILES},before)

    def test_publisher_rejects_forged_operational_success(self):
        self.scan(['access']);self.reconcile()
        h=read(self.root,'health.json');h.update(required_failed=0,required_healthy=29,operational_status='REQUIRED_SOURCES_PASS_WITH_OPTIONAL_GAPS')
        save(self.root,'health.json',h)
        with self.assertRaisesRegex(ValueError,'health_scope_mismatch'):
            evidence.validate(self.root)
        p=subprocess.run(['python3',str(ROOT/'scripts/source_monitoring_scope.py'),'--root',str(self.root)],capture_output=True,text=True)
        self.assertEqual(p.returncode,3)

    def test_full_workflow_rejects_missing_required_row(self):
        self.scan();self.reconcile();h=read(self.root,'health.json')
        h['results']=[r for r in h['results'] if r['id']!='access']
        h.update(monitored=30,healthy=28)
        h.update(scope.summarize(CATALOG,h['results']))
        save(self.root,'health.json',h)
        p=subprocess.run(['python3',str(ROOT/'scripts/source_monitoring_scope.py'),'--root',str(self.root)],capture_output=True,text=True)
        self.assertEqual(p.returncode,3)
        self.assertIn('incomplete_monitoring_coverage',p.stderr)

    def test_scope_exit_code_mismatch_rejected(self):
        self.scan(['access']);self.reconcile()
        p=subprocess.run(['python3',str(ROOT/'scripts/source_monitoring_scope.py'),'--root',str(self.root),'--expected-exit-code','0'],capture_output=True,text=True)
        self.assertEqual(p.returncode,3)

    def test_machine_gate_rejects_role_downgrade_without_rewriting_receipt(self):
        self.scan();self.reconcile()
        prior=(self.root/'sync/machine-accepted.json').read_bytes()
        catalog=read(self.root,'sources.json')
        next(e for e in catalog['sources'] if e['id']=='access')['monitoring_role']=scope.OPTIONAL
        save(self.root,'sources.json',catalog)
        with self.assertRaisesRegex(ValueError,'optional_reference_not_allowlisted'):
            machine.run(self.root,accept=True)
        self.assertEqual((self.root/'sync/machine-accepted.json').read_bytes(),prior)

    def test_real_reader_shell_uses_required_health_outputs(self):
        """Execute the Workflow Bash with parsed 31-source evidence, no network."""
        self.scan();self.reconcile()
        scripts=self.root/'scripts';scripts.mkdir()
        shutil.copyfile(ROOT/'scripts/source_monitoring_scope.py',scripts/'source_monitoring_scope.py')
        bin_dir=self.root/'bin';bin_dir.mkdir()
        # Only replace the already-executed network CLI with its actual result;
        # scope validation and inline summary run with the real Python process.
        wrapper=bin_dir/'python3'
        wrapper.write_text('#!'+sys.executable+'\nimport os,sys\n'
            'if sys.argv[1:]==["scripts/check_official_updates.py"]:\n'
            '    sys.exit(int(os.environ["FIXTURE_SCAN_EXIT"]))\n'
            'os.execv(sys.executable,[sys.executable]+sys.argv[1:])\n')
        wrapper.chmod(0o755)
        for failed,code in (([],0),(['access'],4)):
            with self.subTest(failed=failed):
                self.assertEqual(self.scan(failed),code);self.reconcile()
                env={**os.environ,'PATH':str(bin_dir)+os.pathsep+os.environ.get('PATH',''),
                     'FIXTURE_SCAN_EXIT':str(code)}
                for name in ('GITHUB_OUTPUT','GITHUB_ENV','GITHUB_STEP_SUMMARY'):
                    path=self.root/name;path.write_text('');env[name]=str(path)
                p=subprocess.run(['bash','-c',shell_step('Read public official sources and capture degraded result')],
                                 cwd=self.root,env=env,capture_output=True,text=True)
                self.assertEqual(p.returncode,0,p.stderr+p.stdout)
                self.assertEqual(Path(env['GITHUB_OUTPUT']).read_text(),
                                 'degraded='+('true' if failed else 'false')+'\n')
                summary=Path(env['GITHUB_STEP_SUMMARY']).read_text()
                self.assertIn('OPTIONAL REFERENCE: 0 / 2; failed 2',summary)
                self.assertIn('REQUIRED: '+('28' if failed else '29')+' / 29',summary)
                self.assertIn('DEGRADED',summary)
                self.assertIn('not a complete global release manifest',summary)
                self.assertEqual(self.final_workflow_step(bool(failed)),2 if failed else 0)

    def test_real_writer_shell_validates_all_eight_files_and_reader_flag(self):
        """Run trusted Writer validation, stubbing only macOS stat and final restore.

        No branch selection, network, commit or publication is executed here.
        """
        shutil.copytree(ROOT/'scripts',self.root/'scripts',ignore=shutil.ignore_patterns('__pycache__'))
        bin_dir=self.root/'writer-bin';bin_dir.mkdir()
        stat=bin_dir/'stat'
        stat.write_text('#!'+sys.executable+'\nimport os,sys\n'
                        'assert sys.argv[1]=="-c%s"\nprint(os.stat(sys.argv[2]).st_size)\n')
        git=bin_dir/'git'
        git.write_text('#!'+sys.executable+'\nimport os,sys\n'
                       'assert sys.argv[1:3]==["restore","--"]\n'
                       'open(os.environ["RESTORE_LOG"],"w").write("\\n".join(sys.argv[3:]))\n')
        for path in (stat,git):path.chmod(0o755)
        runner=self.root/'writer-runner';runner.mkdir()
        artifact=runner/'public-evidence'
        cases=('optional_only','required_failure','forged_reader_flag','missing','extra',
               'symlink','oversize','url','sha','product_scope','scope','triage')
        for case in cases:
            with self.subTest(case=case):
                failed=['access'] if case in ('required_failure','forged_reader_flag') else []
                self.assertEqual(self.scan(failed),4 if failed else 0);self.reconcile()
                if artifact.exists():shutil.rmtree(artifact)
                artifact.mkdir()
                for name in FILES:shutil.copyfile(self.root/'sync'/name,artifact/name)
                if case=='missing':(artifact/'pending.json').unlink()
                if case=='extra':(artifact/'extra.txt').write_text('unexpected')
                if case=='symlink':
                    (artifact/'pending.json').unlink()
                    (artifact/'pending.json').symlink_to(self.root/'sync/pending.json')
                if case=='oversize':(artifact/'latest-observed.md').write_bytes(b'x'*2097153)
                if case in ('url','scope'):
                    h=json.loads((artifact/'health.json').read_text())
                    if case=='url':h['results'][0]['url']='https://help.ui.com/forged'
                    else:h['required_failed']=1
                    (artifact/'health.json').write_text(json.dumps(h))
                if case in ('sha','product_scope'):
                    c=json.loads((artifact/'version-candidates.json').read_text())
                    rec=c['sources']['network_application_release_rss']
                    rec['source_sha256' if case=='sha' else 'source_scope']='0'*64 if case=='sha' else 'forged_product'
                    (artifact/'version-candidates.json').write_text(json.dumps(c))
                if case=='triage':(artifact/'review-triage.md').write_text('forged triage')
                restore=self.root/'restore.log';restore.unlink(missing_ok=True)
                env={**os.environ,'PATH':str(bin_dir)+os.pathsep+os.environ.get('PATH',''),
                     'RUNNER_TEMP':str(runner),'RESTORE_LOG':str(restore),
                     'EXPECTED_REQUIRED_DEGRADED':'true' if case=='required_failure' else 'false'}
                result=subprocess.run(['bash','-c',shell_step('Offline validate exact evidence files while executing only trusted main scripts')],
                                      cwd=self.root,env=env,capture_output=True,text=True)
                if case in ('optional_only','required_failure'):
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertEqual(set(restore.read_text().splitlines()),{'sync/'+f for f in FILES})
                    self.assertIn('RELEASE_EVIDENCE_PASS',result.stdout)
                    self.assertIn('MACHINE_SOURCE_OBSERVATIONS_PASS',result.stdout)
                else:
                    self.assertNotEqual(result.returncode,0,case)
                    self.assertFalse(restore.exists(),'Invalid evidence reached restore/publication boundary')
                    if case=='forged_reader_flag':
                        self.assertIn('reader_degraded_flag_does_not_match_required_health',result.stderr)

    def test_readme_snapshot_date_is_required_and_valid(self):
        for f in ('manifest.json','sync/sources.json','docs/evidence/official-sync-39228248994-health.json'):
            target=self.root/f;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/f,target)
        original=json.loads((self.root/'manifest.json').read_text())
        for value in (None,'2026-02-30','20261019'):
            config=copy.deepcopy(original);config['monitoring_contract']['status_snapshot_date']=value
            (self.root/'manifest.json').write_text(json.dumps(config))
            with self.subTest(value=value),self.assertRaises(ValueError):status_doc.render(self.root)

    def test_readme_generated_scope_is_current_not_deployed(self):
        doc=(ROOT/'README.md').read_text();block=status_doc.render()
        self.assertIn(block,doc)
        self.assertIn('29 個 REQUIRED',block)
        self.assertIn('2 個 OPTIONAL REFERENCE',block)
        self.assertIn('尚未部署',block)
        self.assertIn('狀態快照日期：2026-10-19（非即時部署狀態）',block)
        self.assertIn('截至此日',block)
        self.assertIn('/actions/workflows/official-knowledge-sync.yml',block)
        self.assertIn('/issues/7',block)
        self.assertNotIn('本分支是 **PR #47 的本地提案',doc)
        self.assertNotIn('## 正式監測範圍修正（尚待',doc)
        self.assertIn('不能', (ROOT/'docs/required-source-monitoring.md').read_text())

if __name__=='__main__':unittest.main()
