import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("apt_vendor",ROOT/"scripts/apt_official_index.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SignedAptTests(unittest.TestCase):
 def test_status_requires_pinned_cryptographic_validity(self):
  valid=f"[GNUPG:] VALIDSIG {module.KEY_FINGERPRINT} 2026 0 4 0 1 0 0 0\n"
  historical=(f"[GNUPG:] ERRSIG {module.OLD_KEY_ID} 1 8 01 0 0 0\n"
              f"[GNUPG:] NO_PUBKEY {module.OLD_KEY_ID}\n")
  self.assertEqual(module.parse_verification_status(historical+valid),module.KEY_FINGERPRINT)
  with self.assertRaisesRegex(ValueError,"missing_current_valid_signature"):
   module.parse_verification_status(historical)
  with self.assertRaisesRegex(ValueError,"invalid_or_revoked_signature"):
   module.parse_verification_status(valid+"[GNUPG:] BADSIG SOMEKEY bogus\n")
  with self.assertRaisesRegex(ValueError,"unexpected_missing_or_error_signer"):
   module.parse_verification_status(valid+"[GNUPG:] NO_PUBKEY 1234567890ABCDEF\n")

 def test_reject_unapproved_url_and_redirect(self):
  for url in ["http://dl.ui.com/key","https://not-ui.com/index",
              "https://evil.ui.com/key","https://login:token@dl.ui.com/key",
              "https://dl.ui.com:8443/key","https://dl.ui.com/key#fragment"]:
   with self.subTest(url=url), self.assertRaises(ValueError):
    module.approved(url)
  self.assertEqual(module.approved(module.INDEX_URL).hostname,"www.ui.com")

 def test_sha256_is_from_signed_metadata(self):
  p=b"Package: unifi\nVersion: 10.1.85-32713-1\nArchitecture: all\n\n"
  sha=hashlib.sha256(p).hexdigest()
  signed=("-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA512\n\n"
          "Origin: Ubiquiti Networks, Inc.\nSuite: stable\n"
          "Codename: unifi-10.1\nDate: Wed, 01 Apr 2026 11:14:06 UTC\n"
          "SHA256:\n"
          f" {sha} {len(p)} ubiquiti/binary-amd64/Packages\n"
          "-----BEGIN PGP SIGNATURE-----\n"
          "fake-crypto-fixture-not-for-signature-tests\n"
          "-----END PGP SIGNATURE-----\n").encode()
  fields=module.signed_release_fields(signed)
  self.assertEqual(fields["sha256"],sha)
  self.assertEqual(fields["size"],len(p))
  self.assertEqual(fields["codename"],"unifi-10.1")
  self.assertEqual(module.package_version(p),"10.1.85-32713-1")
  self.assertNotEqual(hashlib.sha256(p+b"tamper").hexdigest(),fields["sha256"])

 def test_no_packages_or_wrong_version_fail_closed(self):
  with self.assertRaisesRegex(ValueError,"unifi_package_not_found"):
   module.package_version(b"Package: other\nVersion: 1.2.3\n")
  with self.assertRaisesRegex(ValueError,"invalid_debian_package_version"):
   module.package_version(b"Package: unifi\nVersion: not-a-version\n")

 def test_signed_empty_index_does_not_create_release_candidate(self):
  with patch.object(module,'check_robots'), patch.object(module,'fetch',return_value=b'synthetic'), \
       patch.object(module,'verify_signature',return_value=module.KEY_FINGERPRINT), \
       patch.object(module,'signed_release_fields',return_value={
          "codename":"unifi-10.5","date":"Mon, 27 Jul 2026 14:19:52 UTC",
          "relative_path":"ubiquiti/binary-amd64/Packages",
          "sha256":hashlib.sha256(b"").hexdigest(),"size":0
       }):
   result=module.run()
   self.assertEqual(result["verification"],"PINNED_PGP_SIGNATURE_VALID")
   self.assertEqual(result["content_status"],"SIGNED_EMPTY_PACKAGES")
   self.assertEqual(result["review_status"],"NO_NEW_KNOWLEDGE")
   self.assertNotIn("package_version",result)
   self.assertTrue(result["not_global_latest"])

 def test_fingerprint_rotation_requires_review(self):
  self.assertEqual(len(module.KEY_FINGERPRINT),40)
  self.assertNotEqual(module.KEY_FINGERPRINT, "4A228B2D358A5094178285BE06E85760C0A52C50")

if __name__=="__main__": unittest.main()
