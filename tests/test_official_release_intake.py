import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("release_intake",ROOT/"scripts/import_official_release_evidence.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def fixture():
    return {
      "family":"Network","product":"UniFi Network Application",
      "version":"10.9.123","asserted_release_channel":"Release Candidate",
      "official_release_url":"https://community.ui.com/releases/00000000-0000-4000-8000-000000000000",
      "checked_on":"2026-10-18",
      "short_evidence_excerpt":"Synthetic only: Network application v10.9.123 Release Candidate is not a real release."
    }

class ReleaseIntakeTests(unittest.TestCase):
    def test_valid_synthetic_claim_is_not_verified_knowledge(self):
        out=mod.parse_batch([fixture()])
        self.assertFalse(out["independent_vendor_fetch"])
        self.assertEqual(len(out["candidates"]),1)
        row=out["candidates"][0]
        self.assertEqual(row["review_status"],"UNREVIEWED_EVIDENCE_NOT_KNOWLEDGE")
        self.assertEqual(row["channel_verified"],"HUMAN_REVIEW_REQUIRED")
        self.assertEqual(row["affected_module"],"M02")
        self.assertNotIn("short_evidence_excerpt",row)
        self.assertEqual(len(row["excerpt_sha256"]),64)

    def test_reject_bad_channels_and_version_labels(self):
        for field,value in [("asserted_release_channel","Stable"),
                            ("version","latest"),
                            ("version","10.5"),
                            ("checked_on","2200-01-01"),
                            ("family","Unknown")]:
            case=fixture();case[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                mod.parse_batch([case])

    def test_reject_moving_index_nonofficial_or_url_tricks(self):
        urls=["https://community.ui.com/releases?view=latest",
              "https://community.ui.com/questions/example",
              "https://community.ui.com.evil.example/releases/00000000-0000-4000-8000-000000000000",
              "http://community.ui.com/releases/00000000-0000-4000-8000-000000000000",
              "https://person:password@community.ui.com/releases/00000000-0000-4000-8000-000000000000",
              "https://community.ui.com:8443/releases/00000000-0000-4000-8000-000000000000"]
        for url in urls:
            case=fixture();case["official_release_url"]=url
            with self.subTest(url=url),self.assertRaises(ValueError):
                mod.parse_batch([case])

    def test_secret_and_duplicate_claims_rejected(self):
        case=fixture();case["short_evidence_excerpt"]="X-API-Key: TEST_SECRET_VALUE, not allowed in a public repo."
        with self.assertRaises(ValueError): mod.parse_batch([case])
        with self.assertRaisesRegex(ValueError,"duplicate"):
            mod.parse_batch([fixture(),fixture()])

    def test_offline_cli_roundtrip_only_synthetic(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            input_file=path/"synthetic.json";output_file=path/"candidate.json"
            input_file.write_text(json.dumps([fixture()]))
            self.assertEqual(mod.main(["--input",str(input_file),"--output",str(output_file)]),0)
            parsed=json.loads(output_file.read_text())
            self.assertEqual(parsed["candidates"][0]["version"],"10.9.123")
            self.assertNotIn("Synthetic only",output_file.read_text())
            self.assertEqual(parsed["source_mode"],"OFFLINE_MANUAL_PUBLIC_OFFICIAL_RELEASE_EVIDENCE")

if __name__=="__main__":unittest.main()
