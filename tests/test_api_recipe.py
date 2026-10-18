import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("unifi_recipe",ROOT/"recipes/python/unifi_api_readonly.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class APIRecipeTests(unittest.TestCase):
 def test_safe_synthetic_pagination_and_redaction(self):
  a=m.collect_summary(m.mock_page,limit=2)
  self.assertEqual(a["total_devices"],3)
  self.assertEqual(a["states"],{"ONLINE":2,"OFFLINE":1})
  self.assertTrue(a["complete"])
  self.assertNotIn("mac",json.dumps(a).lower())
  self.assertNotIn("SYNTHETIC",json.dumps(a))

 def test_missing_or_changing_total_count_fails(self):
  with self.assertRaisesRegex(ValueError,"missing_pagination_metadata"):
   m.collect_summary(lambda o,l:{"data":[]})
  def changing(offset,limit):
   if offset==0:return {"data":[{"state":"ONLINE"}],"count":1,"offset":0,"limit":limit,"totalCount":3}
   return {"data":[{"state":"OFFLINE"}],"count":1,"offset":offset,"limit":limit,"totalCount":4}
  with self.assertRaisesRegex(ValueError,"changing_total_count"):
   m.collect_summary(changing,limit=1)

 def test_empty_incomplete_pages_rejected(self):
  with self.assertRaisesRegex(ValueError,"incomplete_page"):
   m.collect_summary(lambda o,l:{"data":[],"count":0,"offset":0,"limit":l,"totalCount":1})

 def test_page_cap_rejected(self):
  with self.assertRaisesRegex(ValueError,"max_pages_exceeded"):
   m.collect_summary(m.mock_page,limit=1,max_pages=1)

 def test_explicit_live_opt_in_and_offline_default(self):
  self.assertEqual(m.main([]),0)
  with self.assertRaises(SystemExit):
   m.main(["--live"])
  self.assertNotIn("getpass", (ROOT/"recipes/python/unifi_api_readonly.py").read_text())

 def test_api_matrix_is_official_docs_only(self):
  catalog=json.loads((ROOT/"docs/api-capabilities.json").read_text())
  self.assertTrue(catalog["requires_private_unifi_data"] is False)
  self.assertGreaterEqual(len(catalog["endpoints"]),5)
  for e in catalog["endpoints"]:
   self.assertEqual(e["method"],"GET")
   self.assertEqual(e["side_effects"],"none_expected")
   self.assertTrue(e["docs"].startswith("https://developer.ui.com/"))
   self.assertFalse(e["path"].startswith("http"))
   self.assertTrue(e["doc_version"])
  protect=[x for x in catalog["endpoints"] if x["api_family"]=="protect"]
  self.assertTrue(all(x["release_channel"]=="EA" for x in protect))
if __name__=="__main__":unittest.main()
