import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT=Path(__file__).resolve().parents[1]
def module_at(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
monitor=module_at(ROOT/'scripts/check_official_updates.py','official_monitor')
gate=module_at(ROOT/'scripts/check_review_gate.py','review_gate')

class PublicAcceptance(unittest.TestCase):
    def test_skill_public_scope_and_modules(self):
        skill=(ROOT/'SKILL.md').read_text()
        self.assertIn('公用知識',skill)
        modules=sorted((ROOT/'modules').glob('M[0-9][0-9]-*.md'))
        self.assertEqual(len(modules),10)
        for path in modules:
            t=path.read_text()
            for heading in ['## 核心概念','## 官方建議做法','## UI 操作路徑',
                            '## CLI / API 替代方法','## 風險與注意事項',
                            '## 驗證方式','## 故障排除流程','## 官方文件連結']:
                self.assertIn(heading,t,path.name)
    def test_decisions_runbooks_and_sources(self):
        self.assertEqual(len(list((ROOT/'decisions').glob('D[0-9][0-9]-*.md'))),4)
        self.assertEqual(len(list((ROOT/'runbooks').glob('RB[0-9][0-9]-*.md'))),5)
        for path in (ROOT/'runbooks').glob('RB[0-9][0-9]-*.md'):
            t=path.read_text()
            for h in ['## 前置條件','## 步驟','## 驗證','## 風險與回滾']:
                self.assertIn(h,t,path.name)
        catalog=json.loads((ROOT/'sync/sources.json').read_text())
        self.assertGreaterEqual(len(catalog['sources']),23)
        for entry in catalog['sources']:
            self.assertTrue(entry['url'].startswith('https://'))
            self.assertIn(entry['url'].split('/')[2],{'community.ui.com','help.ui.com','developer.ui.com','www.ui.com','ui.com'})
    def test_live_flow_is_inert(self):
        p=ROOT/'recipes/n8n/unifi-inventory-live.json'
        flow=json.loads(p.read_text())
        self.assertIs(flow['active'],False)
        for node in flow['nodes']:
            if node['type']=='n8n-nodes-base.httpRequest':
                self.assertEqual(node['parameters']['method'],'GET')
                self.assertIn('example.invalid',node['parameters']['url'])
                self.assertNotIn('credentials',node)
        self.assertNotIn('192.168.100.1',(ROOT/'README.md').read_text())
    def test_change_detection_and_human_review_gate(self):
        with TemporaryDirectory() as directory:
            base=Path(directory)
            (base/'sync').mkdir()
            for filename,body in {
              'sources.json':{'sources':[{'id':'platform_intro','url':'https://help.ui.com/hc/en-us/articles/test','modules':['M01']}]},
              'observed.json':{'sources':{}},
              'pending.json':{'changes':{}},
              'reviewed.json':{'reviews':{}},
            }.items():
                (base/'sync'/filename).write_text(json.dumps(body))
            self.assertEqual(gate.validate(base) if hasattr(gate,'validate') else [],[])
            original=monitor.ROOT
            try:
                monitor.ROOT=base
                # Synthetic HTML only; no HTTP calls, no private devices.
                raw=('<html><main>'+('Official documentation text. '*8)+'</main></html>').encode()
                self.assertEqual(monitor.run(fetcher=lambda entry:raw),0)
                self.assertIn('platform_intro',json.loads((base/'sync/pending.json').read_text())['changes'])
                self.assertTrue(json.loads((base/'sync/observed.json').read_text())['sources'])
                if hasattr(gate,'validate'):
                    self.assertTrue(gate.validate(base))
            finally:monitor.ROOT=original

if __name__=='__main__':unittest.main()
