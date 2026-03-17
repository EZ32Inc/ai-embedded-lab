"""
STLinkInstrument runtime glue — direct integration phase.

Thin wrapper around the st-flash / st-info / st-util binaries built from
instruments/STLinkInstrument/upstream/stlink (EZ32Inc fork).

This is NOT a full AEL instrument adapter. Full packaging comes later.
Current scope: probe, flash, gdb_server — callable from Python or scripts.
"""

from __future__ import annotations

import os
import re
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
    Note: STLINK_DEVICE is honoured by st-util/st-flash but NOT by
    st-info --probe (which always lists all connected devices).
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


# ---------------------------------------------------------------------------
# Serial matching helpers
# ---------------------------------------------------------------------------

def _decode_sysfs_serial(raw_bytes: bytes) -> str:
    """Convert raw sysfs serial bytes to the hex string that st-info reports.

    The kernel reads USB serial descriptors (UTF-16LE) and converts them to
    UTF-8 before writing to sysfs. Bytes ≥ 0x80 become multi-byte UTF-8
    sequences (e.g. 0xFF → 0xC3 0xBF). Decoding the sysfs bytes as UTF-8
    recovers the original code points, which equal the firmware serial bytes.
    Returns uppercase hex string (e.g. "51FF6E06...").
    """
    stripped = raw_bytes.rstrip(b"\n")
    try:
        decoded = stripped.decode("utf-8", errors="replace")
        return "".join(f"{ord(c):02X}" for c in decoded)
    except Exception:
        return stripped.hex().upper()


def _match_probe_entry(sysfs_hex: str, probe_entries: list[dict]) -> Optional[dict]:
    """Find the probe entry whose serial starts with sysfs_hex.

    sysfs_hex is derived from the USB serial descriptor (may be a prefix of
    the full firmware serial because the USB descriptor can be shorter).
    Returns the best (longest prefix) match, or None.
    """
    if not sysfs_hex:
        return None
    best: Optional[dict] = None
    best_len = 0
    for entry in probe_entries:
        fw_serial = entry.get("serial", "").upper()
        if fw_serial.startswith(sysfs_hex.upper()):
            if len(sysfs_hex) > best_len:
                best = entry
                best_len = len(sysfs_hex)
    return best


# ---------------------------------------------------------------------------
# Probe all devices (single st-info call)
# ---------------------------------------------------------------------------

def probe_all() -> dict:
    """Run st-info --probe once and parse all detected devices.

    Returns:
      ok          — True if the command succeeded
      count       — number of entries parsed
      entries     — list of dicts per device:
                      serial, version, flash, sram, chipid, dev_type
      stdout/stderr — raw output
    """
    try:
        st_info = _require_tool("st-info")
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc), "count": 0, "entries": []}

    result = subprocess.run(
        [str(st_info), "--probe"],
        capture_output=True,
        text=True,
        timeout=15,
        env=_tool_env(),
    )

    entries = _parse_probe_output(result.stdout + result.stderr)
    return {
        "ok": result.returncode == 0,
        "count": len(entries),
        "entries": entries,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _parse_probe_output(text: str) -> list[dict]:
    """Parse st-info --probe text output into a list of device dicts."""
    entries: list[dict] = []
    current: dict = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()

        # "Found N stlink programmers" — ignore
        if line.lower().startswith("found"):
            continue

        # "N." starts a new device block
        if re.match(r"^\d+\.$", line):
            if current:
                entries.append(current)
            current = {}
            continue

        if ":" in line:
            key, _, val = line.partition(":")
            k = key.strip().lower().replace("-", "_").replace(" ", "_")
            v = val.strip()
            # Normalize key names
            key_map = {
                "version": "version",
                "serial": "serial",
                "flash": "flash",
                "sram": "sram",
                "chipid": "chipid",
                "dev_type": "dev_type",
            }
            k = key_map.get(k, k)
            current[k] = v

    if current:
        entries.append(current)

    return entries


# ---------------------------------------------------------------------------
# Device enumeration (sysfs + single probe_all call)
# ---------------------------------------------------------------------------

def list_devices() -> list[dict]:
    """Enumerate connected ST-Link devices and match each to its MCU.

    Strategy:
      1. Scan sysfs for USB devices with VID:PID 0483:3748.
      2. Run st-info --probe ONCE to get all connected targets (serial, chipid,
         flash, sram, dev-type).
      3. Match each sysfs device to a probe entry by decoding the USB serial
         descriptor bytes (UTF-8) → uppercase hex → prefix match against
         firmware serial.

    Returns a list of dicts per USB device:
      usb_path       — sysfs path key (e.g. "1-14.4")
      bus / addr     — zero-padded USB bus/address strings
      stlink_device  — "BUS:ADDR" for STLINK_DEVICE env var / --stlink-device
      sysfs_serial_hex — raw sysfs serial decoded to hex
      serial         — firmware serial from st-info (or None)
      version        — ST-Link firmware version string (or None)
      product        — USB product string
      mcu_chipid     — chip ID hex string (or None)
      mcu_dev_type   — human-readable MCU family string (or None)
      mcu_flash_kb   — flash size in KB (or None)
      mcu_sram_kb    — SRAM size in KB (or None)
      probe_ok       — True if a matching probe entry was found
    """
    base = Path("/sys/bus/usb/devices")
    sysfs_devices = []

    for dev_path in sorted(base.iterdir()):
        vid_file = dev_path / "idVendor"
        pid_file = dev_path / "idProduct"
        if not vid_file.is_file() or not pid_file.is_file():
            continue
        if vid_file.read_text().strip() != _STLINK_VID:
            continue
        if pid_file.read_text().strip() != _STLINK_PID:
            continue

        busnum = (dev_path / "busnum").read_text().strip() if (dev_path / "busnum").is_file() else "?"
        devnum = (dev_path / "devnum").read_text().strip() if (dev_path / "devnum").is_file() else "?"
        try:
            bus = f"{int(busnum):03d}"
            addr = f"{int(devnum):03d}"
        except ValueError:
            bus, addr = busnum, devnum

        sysfs_serial_raw = b""
        serial_file = dev_path / "serial"
        if serial_file.is_file():
            try:
                sysfs_serial_raw = serial_file.read_bytes()
            except OSError:
                pass

        product = ""
        product_file = dev_path / "product"
        if product_file.is_file():
            try:
                product = product_file.read_text().strip()
            except OSError:
                pass

        sysfs_devices.append({
            "usb_path": dev_path.name,
            "bus": bus,
            "addr": addr,
            "stlink_device": f"{bus}:{addr}",
            "sysfs_serial_hex": _decode_sysfs_serial(sysfs_serial_raw),
            "product": product,
        })

    # Run probe_all once to get all MCU info.
    probe_result = probe_all()
    probe_entries = probe_result.get("entries", [])

    # Match each sysfs device to a probe entry.
    used_indices: set[int] = set()
    result = []

    for dev in sysfs_devices:
        sysfs_hex = dev["sysfs_serial_hex"]
        matched: Optional[dict] = None
        best_len = 0

        for i, entry in enumerate(probe_entries):
            if i in used_indices:
                continue
            fw_serial = entry.get("serial", "").upper()
            if sysfs_hex and fw_serial.startswith(sysfs_hex.upper()):
                if len(sysfs_hex) > best_len:
                    matched = entry
                    best_len = len(sysfs_hex)
                    best_idx = i

        if matched is not None:
            used_indices.add(best_idx)

        def _kb(raw: str) -> Optional[int]:
            m = re.match(r"(\d+)", raw or "")
            return int(m.group(1)) // 1024 if m else None

        result.append({
            "usb_path": dev["usb_path"],
            "bus": dev["bus"],
            "addr": dev["addr"],
            "stlink_device": dev["stlink_device"],
            "sysfs_serial_hex": sysfs_hex,
            "serial": matched.get("serial") if matched else None,
            "version": matched.get("version") if matched else None,
            "product": dev["product"],
            "mcu_chipid": matched.get("chipid") if matched else None,
            "mcu_dev_type": matched.get("dev_type") if matched else None,
            "mcu_flash_kb": _kb(matched.get("flash", "")) if matched else None,
            "mcu_sram_kb": _kb(matched.get("sram", "")) if matched else None,
            "probe_ok": matched is not None,
        })

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def probe() -> dict:
    """Run st-info --probe (all devices) and return parsed output."""
    return probe_all()


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
    """Launch st-util GDB server as a background process.

    stlink_device: "BUS:ADDR" string (e.g. "001:086") to target a specific ST-Link.
    Returns the Popen object — caller is responsible for .terminate().
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
