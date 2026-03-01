import json
import urllib.request

from .manifest import load_manifest_from_file, _validate_manifest


def fetch_network_manifest(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AEL/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = resp.read().decode("utf-8")
        doc = json.loads(data)
    except Exception:
        return None
    if not _validate_manifest(doc):
        return None
    return doc
