"""
ael.board.capability_registry
==============================
Board capability registry: maps named capabilities to invocable targets.

A capability registry YAML lives alongside the board config:
    configs/boards/<board_id>_capabilities.yaml

Invocation kinds:
  script  — run a Python script directly (passes --config <probe_config>)
  pack    — run via `ael pack --pack <target>`
  test    — run via `ael run --test <target>`
  api     — not directly runnable; prints endpoint info and usage example

Resolution is keyword-overlap based: the query is tokenised and scored
against each alias. Highest matching alias wins.  No fuzzy string distance.

Usage
-----
    from ael.board.capability_registry import load_registry

    reg = load_registry("esp32jtag_instrument_s3", repo_root=Path("."))
    print(reg.list_capabilities())          # show all capabilities
    exit_code = reg.invoke("port d loopback self-test", verbose=True)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


# ── Loader ────────────────────────────────────────────────────────────────────

def load_registry(
    board_id: str,
    repo_root: Optional[Path] = None,
    registry_path: Optional[Path] = None,
) -> "CapabilityRegistry":
    """
    Load the capability registry for *board_id*.

    Search order:
      1. Explicit *registry_path* (if provided)
      2. ``configs/boards/<board_id>_capabilities.yaml`` under *repo_root*

    Raises FileNotFoundError if neither is found.
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent.parent

    if registry_path is None:
        registry_path = repo_root / "configs" / "boards" / f"{board_id}_capabilities.yaml"

    if not registry_path.exists():
        raise FileNotFoundError(
            f"No capability registry for board {board_id!r}.\n"
            f"Expected: {registry_path}"
        )

    if yaml is None:
        raise ImportError("PyYAML is required: pip install pyyaml")

    with open(registry_path) as fh:
        raw = yaml.safe_load(fh) or {}

    return CapabilityRegistry(raw, repo_root=repo_root)


# ── Registry ──────────────────────────────────────────────────────────────────

class CapabilityRegistry:
    """
    Resolved capability registry for one board.

    Parameters
    ----------
    raw : dict
        Parsed YAML content of a ``*_capabilities.yaml`` file.
    repo_root : Path
        Repository root used to resolve relative target paths.
    """

    def __init__(self, raw: dict, repo_root: Path) -> None:
        self._raw = raw
        self.board: str = raw.get("board", "unknown")
        self.version: str = str(raw.get("version", "v1"))
        self._default_probe: Optional[str] = raw.get("default_probe_config")
        self._caps: dict[str, dict] = dict(raw.get("capabilities") or {})
        self.repo_root = Path(repo_root)

        # Build alias → canonical name index
        self._alias_map: dict[str, str] = {}
        for cap_name, cap in self._caps.items():
            # The canonical name itself is also an alias (underscores → spaces)
            self._alias_map[cap_name.lower().replace("_", " ")] = cap_name
            self._alias_map[cap_name.lower()] = cap_name
            for alias in cap.get("aliases") or []:
                self._alias_map[alias.lower().strip()] = cap_name

    # ── Resolution ───────────────────────────────────────────────────────────

    def resolve(self, query: str) -> Optional[dict]:
        """
        Resolve *query* to a capability dict, or None if no match.

        Exact match takes priority; falls back to highest word-overlap score.
        """
        q = query.lower().strip()

        # Exact match
        if q in self._alias_map:
            name = self._alias_map[q]
            return {"_name": name, **self._caps[name]}

        # Word-overlap scoring
        q_words = set(q.split())
        best_name: Optional[str] = None
        best_score = 0

        for alias, cap_name in self._alias_map.items():
            score = len(q_words & set(alias.split()))
            if score > best_score:
                best_score = score
                best_name = cap_name

        if best_name and best_score > 0:
            return {"_name": best_name, **self._caps[best_name]}

        return None

    # ── Invocation ───────────────────────────────────────────────────────────

    def invoke(self, query: str, verbose: bool = False) -> int:
        """
        Resolve *query* and run the matched capability.

        Returns the process exit code (0 = success, non-zero = failure).
        `kind: api` capabilities are not executable; prints guidance instead.
        """
        cap = self.resolve(query)
        if cap is None:
            print(f"[invoke] No capability matches: {query!r}")
            print(f"[invoke] Run with --list to see all capabilities.")
            return 2

        name = cap["_name"]
        kind = cap.get("kind", "")
        print(f"[invoke] ▶  {name}")
        print(f"[invoke]    {cap.get('description', '').strip()}")

        requires = cap.get("requires") or {}
        if requires:
            for key, val in requires.items():
                print(f"[invoke]    requires {key}: {val}")

        probe_cfg = cap.get("probe_config") or self._default_probe
        target_rel = cap.get("target", "")

        if kind == "script":
            return self._invoke_script(target_rel, probe_cfg, verbose)

        if kind == "pack":
            return self._invoke_pack(target_rel, verbose)

        if kind == "test":
            return self._invoke_test(target_rel, probe_cfg, verbose)

        if kind == "api":
            return self._show_api_info(cap)

        print(f"[invoke] Unknown kind: {kind!r}")
        return 1

    # ── Private invocation helpers ────────────────────────────────────────────

    def _invoke_script(self, target_rel: str, probe_cfg: Optional[str], verbose: bool) -> int:
        target = self.repo_root / target_rel
        if not target.exists():
            print(f"[invoke] Script not found: {target}")
            return 1
        cmd = [sys.executable, str(target)]
        if probe_cfg:
            cmd += ["--config", str(self.repo_root / probe_cfg)]
        if verbose:
            cmd.append("--verbose")
        print(f"[invoke] $ {' '.join(cmd)}")
        return subprocess.call(cmd, cwd=self.repo_root)

    def _invoke_pack(self, target_rel: str, verbose: bool) -> int:
        target = self.repo_root / target_rel
        if not target.exists():
            print(f"[invoke] Pack not found: {target}")
            return 1
        cmd = [sys.executable, "-m", "ael", "pack", "--pack", str(target)]
        if verbose:
            cmd.append("--verbose")
        print(f"[invoke] $ {' '.join(cmd)}")
        return subprocess.call(cmd, cwd=self.repo_root)

    def _invoke_test(self, target_rel: str, probe_cfg: Optional[str], verbose: bool) -> int:
        target = self.repo_root / target_rel
        if not target.exists():
            print(f"[invoke] Test not found: {target}")
            return 1
        cmd = [sys.executable, "-m", "ael", "run", "--test", str(target)]
        if probe_cfg:
            cmd += ["--probe", str(self.repo_root / probe_cfg)]
        if verbose:
            cmd.append("--verbose")
        print(f"[invoke] $ {' '.join(cmd)}")
        return subprocess.call(cmd, cwd=self.repo_root)

    def _show_api_info(self, cap: dict) -> int:
        endpoint = cap.get("api_endpoint", "")
        method   = cap.get("api_method", "")
        body     = cap.get("api_body", "")
        impl     = cap.get("implemented_in", "")
        # Avoid "POST POST ..." if endpoint already starts with method
        if method and not endpoint.upper().startswith(method.upper()):
            ep_line = f"{method} {endpoint}"
        else:
            ep_line = endpoint
        print(f"[invoke] kind=api — not directly runnable as a test")
        print(f"[invoke] endpoint : {ep_line}")
        if body:
            print(f"[invoke] body     : {body}")
        if impl:
            print(f"[invoke] impl in  : {impl}")
        print(f"[invoke] Tip: use port_d_loopback_self_test to exercise this capability end-to-end.")
        return 0

    # ── Display ───────────────────────────────────────────────────────────────

    def list_capabilities(self, verbose: bool = False) -> str:
        lines = [
            f"Board capability registry: {self.board}  ({self.version})",
            "",
        ]
        runnable = [(n, c) for n, c in self._caps.items() if c.get("kind") != "api"]
        api_caps = [(n, c) for n, c in self._caps.items() if c.get("kind") == "api"]

        if runnable:
            lines.append("  Runnable capabilities:")
            for name, cap in runnable:
                kind = cap.get("kind", "?")
                lines.append(f"    [{kind:6s}] {name}")
                lines.append(f"             {cap.get('description', '').split(chr(10))[0].strip()}")
                if verbose:
                    aliases = cap.get("aliases") or []
                    if aliases:
                        lines.append(f"             aliases: {', '.join(aliases[:4])}")
                    requires = cap.get("requires") or {}
                    for k, v in requires.items():
                        lines.append(f"             requires {k}: {v}")
            lines.append("")

        if api_caps:
            lines.append("  API surface capabilities (informational):")
            for name, cap in api_caps:
                lines.append(f"    [api   ] {name}")
                endpoint = cap.get("api_endpoint", "")
                method = cap.get("api_method", "")
                # Avoid "POST POST ..." if endpoint already starts with method
                if method and not endpoint.upper().startswith(method.upper()):
                    ep = f"{method} {endpoint}"
                else:
                    ep = endpoint
                lines.append(f"             {ep}")
            lines.append("")

        lines.append(
            "  Usage:  ael invoke --board esp32jtag_instrument_s3 \"<capability name or alias>\""
        )
        return "\n".join(lines)
