"""
USB debug adapter enumeration for AEL instruments.

Handles detection and selection info for locally connected USB debug adapters
(currently ST-Link V2/V3). Called from the 'instruments usb-probe' CLI command.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _get_stlink_backend(repo_root: Path):
    """Import stlink_backend from the STLinkInstrument runtime directory."""
    backend_path = repo_root / "instruments" / "STLinkInstrument" / "runtime"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    import stlink_backend  # noqa: PLC0415
    return stlink_backend


def run_probe(repo_root: Path, fmt: str = "text") -> int:
    """Enumerate connected ST-Link USB devices and print results.

    Returns 0 if at least one device was found, 1 otherwise.
    """
    try:
        backend = _get_stlink_backend(repo_root)
    except ImportError as exc:
        print(json.dumps({"ok": False, "error": f"stlink_backend import failed: {exc}"}, indent=2))
        return 1

    devices = backend.list_devices()

    if fmt == "json":
        print(json.dumps({"ok": True, "count": len(devices), "devices": devices}, indent=2))
        return 0 if devices else 1

    # text format
    if not devices:
        print("No ST-Link devices found (VID:PID 0483:3748).")
        return 1

    print(f"Found {len(devices)} ST-Link device(s):\n")
    all_fw_serials = [d["serial"] for d in devices if d["serial"]]
    duplicate_serials = len(set(all_fw_serials)) < len(all_fw_serials)

    gdb_server_script = "instruments/STLinkInstrument/scripts/gdb_server.sh"

    for i, d in enumerate(devices):
        fw_serial = d["serial"] or "(none)"
        usb_id = d["sysfs_serial_hex"] or "(none)"
        dev_id = d["stlink_device"]
        version = d.get("version") or "?"

        if d["probe_ok"]:
            chipid = d.get("mcu_chipid") or "?"
            dev_type = d.get("mcu_dev_type") or "unknown"
            flash_kb = d.get("mcu_flash_kb")
            sram_kb = d.get("mcu_sram_kb")
            mem = ""
            if flash_kb is not None:
                mem += f"  Flash={flash_kb}KB"
            if sram_kb is not None:
                mem += f"  SRAM={sram_kb}KB"
            mcu_line = f"{dev_type}  (chipid {chipid}){mem}"
            status = "OK"
        else:
            mcu_line = "no target / not connected"
            status = "no MCU"

        print(f"  [{i}] USB path:    {d['usb_path']}  →  STLINK_DEVICE={dev_id}")
        print(f"       ST-Link:    {version}")
        print(f"       MCU:        {mcu_line}")
        print(f"       FW serial:  {fw_serial}")
        print(f"       USB serial: {usb_id}  (unique hardware ID)")
        print(f"       Status:     {status}")
        print()

    if duplicate_serials:
        print("NOTE: Multiple devices share the same firmware serial (common with ST-Link V2 clones).")
        print("      Use STLINK_DEVICE=BUS:ADDR to target a specific device — do NOT use --serial.\n")

    print("To start the GDB server for a specific device:")
    for d in devices:
        dev_id = d["stlink_device"]
        print(f"  {gdb_server_script} --stlink-device {dev_id}")

    return 0
