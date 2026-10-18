import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(script,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/script)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
review=load('approve_official_update.py','approve_official')
gate=load('check_review_gate.py','review_gate')

class HumanApproval(unittest.TestCase):
    def test_requires_exact_digest_and_cited_markdown(self):
        with TemporaryDirectory() as d:
            root=Path(d);(root/'sync').mkdir();(root/'modules').mkdir()
            url='https://help.ui.com/hc/en-us/articles/360012192813-Introduction-to-UniFi'
            good='a'*64
            for file,payload in {
              'pending.json':{'changes':{'platform_intro':{'url':url,'current_sha256':good}}},
              'observed.json':{'sources':{'platform_intro':{'sha256':good}}},
              'reviewed.json':{'reviews':{}}
            }.items():
                (root/'sync'/file).write_text(json.dumps(payload))
            evidence=root/'modules/M01-platform.md'
            evidence.write_text('# Platform\n\nSource: '+url)
            self.assertTrue(gate.validate(root))
            with self.assertRaises(ValueError):
                review.approve(root,'platform_intro','b'*64,'reviewer-id','Reviewed latest source changes',['modules/M01-platform.md'])
            with self.assertRaises(ValueError):
                review.approve(root,'platform_intro',good,'reviewer-id','Reviewed latest source changes',['modules/missing.md'])
            self.assertEqual(review.approve(root,'platform_intro',good,'reviewer-id','Reviewed latest source changes',['modules/M01-platform.md']),['modules/M01-platform.md'])
            self.assertEqual(gate.validate(root),[])
            recorded=json.loads((root/'sync/reviewed.json').read_text())['reviews']['platform_intro']
            self.assertEqual(recorded['sha256'],good)
            self.assertEqual(recorded['source_url'],url)
if __name__=='__main__':unittest.main()
