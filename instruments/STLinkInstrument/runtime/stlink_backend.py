"""
STLinkInstrument runtime glue — direct integration phase.

Thin wrapper around the st-flash / st-info / st-util binaries built from
instruments/STLinkInstrument/upstream/stlink (EZ32Inc fork).

This is NOT a full AEL instrument adapter. Full packaging comes later.
Current scope: probe, flash, gdb_server — callable from Python or scripts.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

# Resolve paths relative to this file.
_INSTRUMENT_DIR = Path(__file__).resolve().parents[1]
_INSTALL_BIN = _INSTRUMENT_DIR / "install" / "bin"
_INSTALL_LIB = _INSTRUMENT_DIR / "install" / "lib"
_BUILD_BIN = _INSTRUMENT_DIR / "upstream" / "stlink" / "build" / "bin"  # fallback

_STLINK_VID = "0483"
_STLINK_PID = "3748"


def _find_tool(name: str) -> Optional[Path]:
    """Return path to a stlink binary.
    Priority: install/bin/ (cmake --install) > build/bin/ > system PATH.
    """
    for candidate in (_INSTALL_BIN / name, _BUILD_BIN / name):
        if candidate.is_file() and candidate.stat().st_mode & 0o111:
            return candidate
    system = shutil.which(name)
    return Path(system) if system else None


def _tool_env(stlink_device: Optional[str] = None) -> dict:
    """Return env with LD_LIBRARY_PATH set to find libstlink.so.

    If stlink_device is given (format "BUS:ADDR", e.g. "001:086"),
    sets STLINK_DEVICE so libstlink targets that specific device.
    """
    env = os.environ.copy()
    lib = str(_INSTALL_LIB)
    existing = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = f"{lib}:{existing}" if existing else lib
    if stlink_device:
        env["STLINK_DEVICE"] = stlink_device
    return env


def _require_tool(name: str) -> Path:
    tool = _find_tool(name)
    if tool is None:
        raise RuntimeError(
            f"{name} not found. "
            "Run instruments/STLinkInstrument/scripts/build.sh to build from source."
        )
    return tool


def _sysfs_usb_devices() -> Path:
    return Path("/sys/bus/usb/devices")


# ---------------------------------------------------------------------------
# Device enumeration (sysfs + st-info per device)
# ---------------------------------------------------------------------------

def list_devices() -> list[dict]:
    """Enumerate connected ST-Link devices via sysfs.

    Returns a list of dicts, each with:
      usb_path    — sysfs path key (e.g. "1-14.4")
      bus         — USB bus number string, zero-padded to 3 digits (e.g. "001")
      addr        — USB device address string, zero-padded to 3 digits (e.g. "086")
      stlink_device — "BUS:ADDR" string for STLINK_DEVICE env var
      sysfs_serial — raw serial from sysfs (may be binary/garbled for old V2)
      serial      — serial as reported by st-info for this device (hex string, or None)
      product     — USB product string
      probe_ok    — True if st-info --probe succeeded for this device
    """
    base = _sysfs_usb_devices()
    found = []

    for dev_path in sorted(base.iterdir()):
        vid_file = dev_path / "idVendor"
        pid_file = dev_path / "idProduct"
        if not vid_file.is_file() or not pid_file.is_file():
            continue
        if vid_file.read_text().strip() != _STLINK_VID:
            continue
        if pid_file.read_text().strip() != _STLINK_PID:
            continue

        usb_path_key = dev_path.name  # e.g. "1-14.4"

        busnum = (dev_path / "busnum").read_text().strip() if (dev_path / "busnum").is_file() else "?"
        devnum = (dev_path / "devnum").read_text().strip() if (dev_path / "devnum").is_file() else "?"
        try:
            bus = f"{int(busnum):03d}"
            addr = f"{int(devnum):03d}"
        except ValueError:
            bus, addr = busnum, devnum

        stlink_device = f"{bus}:{addr}"

        sysfs_serial_raw = b""
        serial_file = dev_path / "serial"
        if serial_file.is_file():
            try:
                sysfs_serial_raw = serial_file.read_bytes().rstrip(b"\n")
            except OSError:
                pass

        product = ""
        product_file = dev_path / "product"
        if product_file.is_file():
            try:
                product = product_file.read_text().strip()
            except OSError:
                pass

        # Probe this specific device with st-info to get its serial.
        serial, probe_ok = _probe_serial(stlink_device)

        found.append({
            "usb_path": usb_path_key,
            "bus": bus,
            "addr": addr,
            "stlink_device": stlink_device,
            "sysfs_serial_hex": sysfs_serial_raw.hex(),
            "serial": serial,
            "product": product,
            "probe_ok": probe_ok,
        })

    return found


def _probe_serial(stlink_device: str) -> tuple[Optional[str], bool]:
    """Run st-info --probe targeting a specific USB device.

    Returns (serial_string, ok). serial_string is None if not parsed.
    """
    try:
        st_info = _require_tool("st-info")
    except RuntimeError:
        return None, False

    env = _tool_env(stlink_device=stlink_device)
    result = subprocess.run(
        [str(st_info), "--probe"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    ok = result.returncode == 0
    serial = None
    for line in (result.stdout + result.stderr).splitlines():
        stripped = line.strip()
        if stripped.startswith("serial:"):
            serial = stripped.split(":", 1)[1].strip()
            break
    return serial, ok


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def probe() -> dict:
    """Run st-info --probe (first available device) and return parsed output."""
    st_info = _require_tool("st-info")
    result = subprocess.run(
        [str(st_info), "--probe"],
        capture_output=True,
        text=True,
        timeout=10,
        env=_tool_env(),
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "ok": result.returncode == 0,
    }


def flash(firmware_path: str | Path, addr: str = "0x08000000", reset: bool = True,
          stlink_device: Optional[str] = None) -> dict:
    """Flash a .bin file to the target via st-flash.

    stlink_device: "BUS:ADDR" string (e.g. "001:086") to target a specific ST-Link.
    """
    st_flash = _require_tool("st-flash")
    firmware = Path(firmware_path)
    if not firmware.is_file():
        raise FileNotFoundError(f"Firmware not found: {firmware}")

    cmd = [str(st_flash)]
    if reset:
        cmd += ["--reset"]
    cmd += ["write", str(firmware), addr]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                            env=_tool_env(stlink_device=stlink_device))
    return {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "ok": result.returncode == 0,
        "cmd": cmd,
    }


def start_gdb_server(port: int = 4242, multi: bool = False,
                     stlink_device: Optional[str] = None) -> subprocess.Popen:
    """
    Launch st-util GDB server as a background process.
    Returns the Popen object — caller is responsible for .terminate().

    stlink_device: "BUS:ADDR" string (e.g. "001:086") to target a specific ST-Link.
    """
    st_util = _require_tool("st-util")
    cmd = [str(st_util), "--port", str(port)]
    if multi:
        cmd.append("--multi")
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=_tool_env(stlink_device=stlink_device))


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
                capture_output=True, text=True, timeout=5, env=_tool_env(),
            )
            versions[name] = (r.stdout + r.stderr).strip().splitlines()[0]
        except Exception as exc:
            versions[name] = f"error: {exc}"
    return versions


def is_built() -> bool:
    """Return True if install/bin artifacts exist (or build/bin fallback)."""
    return all(_find_tool(name) is not None for name in ("st-flash", "st-info", "st-util"))
