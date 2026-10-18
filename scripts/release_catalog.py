"""Extract UNREVIEWED release candidates from public official release-index text.

Extraction never establishes a stable/Official channel; verify target product,
release notes and applicability manually before knowledge promotion.
"""
import re

PATTERN = re.compile(
    r"\b(?P<label>UniFi\s+(?:Network(?:\s+Application)?"
    r"|OS\s+Server|OS(?:\s+-\s+[A-Za-z0-9 /()_-]{2,64})?"
    r"|Protect(?:\s+Application)?|Access(?:\s+Application)?"
    r"|Talk(?:\s+Application)?|Connect(?:\s+Application)?"
    r"|Identity(?:\s+Application)?))"
    r"\s+(?P<version>\d{1,3}(?:\.\d{1,4}){2,3})\b", re.I
)

def extract(text, url, max_records=60):
    """Return deterministic candidates, not the contents of official Release Notes."""
    results=[]
    seen=set()
    for match in PATTERN.finditer(text):
        label=" ".join(match.group("label").split())
        version=match.group("version")
        key=(label.casefold(),version)
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "product_label":label,"version":version,"source_url":url,
            "release_channel":"UNKNOWN_NOT_VALIDATED",
            "verification":"CANDIDATE_UNREVIEWED"
        })
        if len(results)>=max_records:
            break
    return results
