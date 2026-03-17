"""
STLinkInstrument runtime glue — direct integration phase.

Thin wrapper around the st-flash / st-info / st-util binaries built from
instruments/STLinkInstrument/upstream/stlink (EZ32Inc fork).

This is NOT a full AEL instrument adapter. Full packaging comes later.
Current scope: probe, flash, gdb_server — callable from Python or scripts.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional

# Resolve paths relative to this file.
_INSTRUMENT_DIR = Path(__file__).resolve().parents[1]
_BUILD_BIN = _INSTRUMENT_DIR / "upstream" / "stlink" / "build" / "bin"


def _find_tool(name: str) -> Optional[Path]:
    """Return path to a stlink binary, preferring the local build."""
    local = _BUILD_BIN / name
    if local.is_file() and local.stat().st_mode & 0o111:
        return local
    system = shutil.which(name)
    return Path(system) if system else None


def _require_tool(name: str) -> Path:
    tool = _find_tool(name)
    if tool is None:
        raise RuntimeError(
            f"{name} not found. "
            "Run instruments/STLinkInstrument/scripts/build.sh to build from source."
        )
    return tool


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def probe() -> dict:
    """Run st-info --probe and return parsed output."""
    st_info = _require_tool("st-info")
    result = subprocess.run(
        [str(st_info), "--probe"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "ok": result.returncode == 0,
    }


def flash(firmware_path: str | Path, addr: str = "0x08000000", reset: bool = True) -> dict:
    """Flash a .bin file to the target via st-flash."""
    st_flash = _require_tool("st-flash")
    firmware = Path(firmware_path)
    if not firmware.is_file():
        raise FileNotFoundError(f"Firmware not found: {firmware}")

    cmd = [str(st_flash)]
    if reset:
        cmd += ["--reset"]
    cmd += ["write", str(firmware), addr]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "ok": result.returncode == 0,
        "cmd": cmd,
    }


def start_gdb_server(port: int = 4242, multi: bool = False) -> subprocess.Popen:
    """
    Launch st-util GDB server as a background process.
    Returns the Popen object — caller is responsible for .terminate().
    """
    st_util = _require_tool("st-util")
    cmd = [str(st_util), "--port", str(port)]
    if multi:
        cmd.append("--multi")
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def tool_versions() -> dict:
    """Return version strings for available stlink tools."""
    versions = {}
    for name in ("st-flash", "st-info", "st-util"):
        tool = _find_tool(name)
        if tool is None:
            versions[name] = None
            continue
        try:
            r = subprocess.run(
                [str(tool), "--version"],
                capture_output=True, text=True, timeout=5,
            )
            versions[name] = (r.stdout + r.stderr).strip().splitlines()[0]
        except Exception as exc:
            versions[name] = f"error: {exc}"
    return versions


def is_built() -> bool:
    """Return True if the local build artifacts exist."""
    return all(
        (_BUILD_BIN / name).is_file()
        for name in ("st-flash", "st-info", "st-util")
    )
