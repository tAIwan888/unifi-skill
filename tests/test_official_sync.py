import importlib.util
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("monitor",ROOT/"scripts/check_official_updates.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class MonitorTests(unittest.TestCase):
 def test_digest_ignores_scripts(self):
  self.assertEqual(mod.normalize(b"<html><main><script>secret</script>"+b"x"*120+b"</main></html>"),"x"*120)
 def test_reject_nonhtml(self):
  with self.assertRaises(ValueError):mod.normalize(b"not an HTML page")
 def test_allowlist(self):
  self.assertEqual(mod.HOSTS, {'help.ui.com','developer.ui.com','community.ui.com','www.ui.com','ui.com'})
 def test_no_credentials(self):
  text=(ROOT/"scripts/check_official_updates.py").read_text()
  self.assertNotIn("X-API-Key",text)
