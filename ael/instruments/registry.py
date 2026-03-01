from typing import List, Optional

from .manifest import load_manifests


class InstrumentRegistry:
    def __init__(self, manifests=None):
        self._manifests = manifests if manifests is not None else load_manifests()

    def list(self) -> List[dict]:
        return [self._manifests[k] for k in sorted(self._manifests.keys())]

    def get(self, instrument_id: str) -> Optional[dict]:
        return self._manifests.get(instrument_id)

    def find_by_capability(self, cap_name: str) -> List[dict]:
        matches = []
        for m in self._manifests.values():
            caps = m.get("capabilities", []) if isinstance(m, dict) else []
            for c in caps:
                if isinstance(c, dict) and c.get("name") == cap_name:
                    matches.append(m)
                    break
        return sorted(matches, key=lambda x: x.get("id", ""))

    def choose(self, cap_name: str) -> Optional[dict]:
        matches = self.find_by_capability(cap_name)
        if not matches:
            return None
        user = [m for m in matches if m.get("_origin") == "user"]
        pool = user if user else matches
        return sorted(pool, key=lambda x: x.get("id", ""))[0]


def resolve_instrument_for_cap(cap_name: str, explicit: Optional[dict] = None) -> Optional[dict]:
    if isinstance(explicit, dict):
        inst = explicit.get("instrument") if isinstance(explicit.get("instrument"), dict) else None
        if inst and inst.get("id"):
            return inst
    registry = InstrumentRegistry()
    return registry.choose(cap_name)
