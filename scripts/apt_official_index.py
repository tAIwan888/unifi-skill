#!/usr/bin/env python3
"""Verify official Ubiquiti *legacy Network APT* metadata, never device updates.

This is NOT a universal UniFi release feed. Signed metadata is a candidate
for human review, not automatic authorization to change public knowledge.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib import parse, request, robotparser

ROOT = Path(__file__).resolve().parents[1]
INDEX_URL = "https://www.ui.com/downloads/unifi/debian/dists/stable/InRelease"
KEY_URL = "https://dl.ui.com/unifi/unifi-repo.gpg"
BASE_URL = "https://www.ui.com/downloads/unifi/debian/dists/stable/"
KEY_FINGERPRINT = "FCF764DFE6488B0F899E91A17C84148C6904B09E"
OLD_KEY_ID = "06E85760C0A52C50"
APPROVED_HOSTS = {"www.ui.com", "ui.com", "dl.ui.com"}
UA = "UniFiSkillPublicKnowledgeMonitor/0.8"
MAX_BYTES = 2000000

def approved(url):
    p = parse.urlsplit(url)
    if p.scheme != "https" or p.hostname not in APPROVED_HOSTS or p.username or p.password or p.port is not None or p.fragment:
        raise ValueError("untrusted_vendor_url")
    return p

class Redirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        approved(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def fetch(opener, url, cap=MAX_BYTES):
    approved(url)
    with opener.open(request.Request(url, headers={"User-Agent":UA}), timeout=18) as response:
        raw = response.read(cap+1)
    if len(raw)>cap:
        raise ValueError("too_large")
    return raw

def check_robots(opener, url):
    p=approved(url)
    robot_url="https://"+p.hostname+"/robots.txt"
    lines=fetch(opener,robot_url,65536).decode("utf-8","replace").splitlines()
    robots=robotparser.RobotFileParser()
    robots.parse(lines)
    if not robots.can_fetch(UA,url):
        raise ValueError("robots_disallowed")

def key_fingerprint(key_path):
    proc = subprocess.run(["gpg","--batch","--with-colons","--show-keys",str(key_path)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=12, check=True)
    matches=[s.split(":")[9] for s in proc.stdout.splitlines() if s.startswith("fpr:")]
    if not matches or matches[0]!=KEY_FINGERPRINT:
        raise ValueError("vendor_signing_key_changed_requires_human_review")
    return matches[0]

def parse_verification_status(output):
    """Require current pinned good signature; tolerate only missing known old key."""
    status=[line[len("[GNUPG:] "):] for line in output.splitlines() if line.startswith("[GNUPG:] ")]
    if any(s.split()[0] in ("BADSIG","EXPSIG","EXPKEYSIG","REVKEYSIG","KEYREVOKED") for s in status):
        raise ValueError("invalid_or_revoked_signature")
    valid={s.split()[1] for s in status if s.startswith("VALIDSIG ") and len(s.split())>=2}
    if valid!={KEY_FINGERPRINT}:
        raise ValueError("missing_current_valid_signature")
    other_errors=[s for s in status if s.startswith(("NO_PUBKEY ","ERRSIG "))]
    for error in other_errors:
        tokens=error.split()
        if tokens[1]!=OLD_KEY_ID:
            raise ValueError("unexpected_missing_or_error_signer")
    return KEY_FINGERPRINT

def verify_signature(index_bytes, key_bytes):
    if not index_bytes.startswith(b"-----BEGIN PGP SIGNED MESSAGE-----"):
        raise ValueError("missing_clearsigned_index")
    if b"-----BEGIN PGP SIGNATURE-----" not in index_bytes:
        raise ValueError("missing_pgp_signature")
    with tempfile.TemporaryDirectory() as temp:
        d=Path(temp)
        key=d/"vendor-key.gpg"
        signed=d/"InRelease"
        key.write_bytes(key_bytes);signed.write_bytes(index_bytes)
        key_fingerprint(key)
        keybox=d/"vendor-import.kbx"
        subprocess.run(["gpg","--batch","--no-default-keyring","--keyring",str(keybox),
                        "--import",str(key)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12,check=True)
        # gpgv expects an exported keyring, not a modern GPG keybox.
        exported=subprocess.run(["gpg","--batch","--no-default-keyring","--keyring",str(keybox),
                                 "--export",KEY_FINGERPRINT],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12,check=True)
        if not exported.stdout:
            raise ValueError("empty_exported_keyring")
        keyring=d/"vendor-exported.gpg";keyring.write_bytes(exported.stdout)
        proc=subprocess.run(["gpgv","--status-fd=1","--keyring",str(keyring),str(signed)],
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=12)
        # gpgv may exit 2 when an additional historical signature's key is
        # unavailable. Accept ONLY an explicit VALID parsed pinned signature.
        return parse_verification_status(proc.stdout)

def signed_release_fields(raw):
    text=raw.decode("utf-8","strict")
    if not text.startswith("-----BEGIN PGP SIGNED MESSAGE-----"):
        raise ValueError("not_clearsigned")
    body=text.split("-----BEGIN PGP SIGNATURE-----",1)[0]
    if "Origin: Ubiquiti Networks, Inc." not in body or "Suite: stable" not in body:
        raise ValueError("unexpected_repository_identity")
    def field(name):
        m=re.search(r"(?m)^"+re.escape(name)+r":\s*(.+?)\s*$",body)
        if not m: raise ValueError("release_field_missing_"+name.lower())
        return m.group(1)
    checksum_block=re.search(r"(?ms)^SHA256:\s*\n(.*?)(?=^[A-Za-z0-9-]+:|\Z)",body)
    if not checksum_block:
        raise ValueError("missing_sha256_block")
    entries={}
    for line in checksum_block.group(1).splitlines():
        x=re.fullmatch(r"\s*([a-f0-9]{64})\s+(\d+)\s+(\S+)\s*",line)
        if x: entries[x.group(3)]=(x.group(1),int(x.group(2)))
    chosen="ubiquiti/binary-amd64/Packages"
    if chosen not in entries:raise ValueError("signed_packages_index_missing")
    return {"codename":field("Codename"),"date":field("Date"),"relative_path":chosen,
            "sha256":entries[chosen][0],"size":entries[chosen][1]}

def package_version(raw):
    # Debian "Packages" paragraphs, not a generic HTML or download page.
    text=raw.decode("utf-8","strict")
    for stanza in re.split(r"\n\s*\n",text):
        p=dict(re.findall(r"(?m)^([A-Za-z0-9-]+):\s*(.+)$",stanza))
        if p.get("Package")=="unifi":
            value=p.get("Version","")
            if not re.fullmatch(r"\d+(?:\.\d+){2,3}(?:[-+~][A-Za-z0-9.+~-]+)?",value):
                raise ValueError("invalid_debian_package_version")
            return value
    raise ValueError("unifi_package_not_found")

def run():
    opener=request.build_opener(Redirect())
    check_robots(opener,INDEX_URL)
    signed=fetch(opener,INDEX_URL,300000)
    pubkey=fetch(opener,KEY_URL,100000)
    signer=verify_signature(signed,pubkey)
    fields=signed_release_fields(signed)
    path=fields["relative_path"]
    if path!="ubiquiti/binary-amd64/Packages":
        raise ValueError("unapproved_package_path")
    if fields["size"] > MAX_BYTES:
        raise ValueError("package_list_too_large")
    if fields["size"] == 0:
        # Signed, cryptographically valid, but has NO package content.
        # Do not infer a UniFi release version from Codename alone.
        return {"schema_version":1,"source_scope":"legacy_self_hosted_network_only",
                "source_url":INDEX_URL,
                "observed_index_sha256":hashlib.sha256(signed).hexdigest(),
                "gpg_valid_signature_fingerprint":signer,
                "release_codename":fields["codename"],
                "signed_release_date":fields["date"],
                "signed_packages_sha256":fields["sha256"],
                "signed_packages_size":0,
                "verification":"PINNED_PGP_SIGNATURE_VALID",
                "content_status":"SIGNED_EMPTY_PACKAGES",
                "review_status":"NO_NEW_KNOWLEDGE",
                "not_global_latest":True}
    packages=fetch(opener,parse.urljoin(BASE_URL,path),MAX_BYTES)
    if len(packages)!=fields["size"] or hashlib.sha256(packages).hexdigest()!=fields["sha256"]:
        raise ValueError("signed_package_checksum_mismatch")
    version=package_version(packages)
    return {"schema_version":1,"source_scope":"legacy_self_hosted_network_only",
            "source_url":INDEX_URL,"package_source_url":parse.urljoin(BASE_URL,path),
            "observed_index_sha256":hashlib.sha256(signed).hexdigest(),
            "gpg_valid_signature_fingerprint":signer,
            "release_codename":fields["codename"],"signed_release_date":fields["date"],
            "package_name":"unifi","package_version":version,
            "verification":"PINNED_PGP_SIGNATURE_AND_SIGNED_PACKAGE_SHA256_VALID",
            "review_status":"UNREVIEWED_CANDIDATE","not_global_latest":True}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"sync/legacy-network-apt-status.json")
    args=parser.parse_args()
    try:
        result=run()
        status=0 if result.get("review_status")=="UNREVIEWED_CANDIDATE" else 2
    except (ValueError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        result={"schema_version":1,"source_scope":"legacy_self_hosted_network_only",
                "source_url":INDEX_URL,"verification":"FAILED_CLOSED",
                "review_status":"NO_NEW_KNOWLEDGE","failure_code":type(exc).__name__,
                "not_global_latest":True}
        status=2
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return status

if __name__=="__main__":
    sys.exit(main())
