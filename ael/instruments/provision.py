from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from . import wifi
from ael.adapters import esp32s3_dev_c_meter_tcp


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def firmware_dir(manifest: dict) -> Path:
    inst_id = str(manifest.get("id") or "").strip()
    if not inst_id:
        raise ValueError("instrument manifest missing id")
    path = _repo_root() / "firmware" / "instruments" / inst_id
    if not path.exists():
        raise ValueError(f"firmware directory not found for instrument: {inst_id}")
    return path


def flash_meter(port: str, manifest: dict) -> dict[str, Any]:
    fw_dir = firmware_dir(manifest)
    proc = subprocess.run(
        ["idf.py", "-p", port, "flash"],
        cwd=str(fw_dir),
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(err or f"idf.py flash failed on {port}")
    return {
        "ok": True,
        "instrument_id": manifest.get("id"),
        "port": port,
        "firmware_dir": str(fw_dir),
        "flash": "completed",
    }


def wait_for_meter(
    ifname: str,
    manifest: dict,
    timeout_s: float = 30.0,
    interval_s: float = 2.0,
) -> dict[str, Any]:
    deadline = time.time() + max(timeout_s, 1.0)
    last_matches: list[dict[str, Any]] = []
    while time.time() < deadline:
        result = wifi.scan(ifname=ifname, manifest=manifest)
        last_matches = result.get("matches", [])
        if last_matches:
            return result
        time.sleep(max(interval_s, 0.1))
    raise RuntimeError(f"meter AP not found within {timeout_s:.1f}s on {ifname}")


def flash_wait_connect(
    port: str,
    ifname: str,
    manifest: dict,
    ssid: str | None = None,
    ssid_suffix: str | None = None,
    timeout_s: float = 30.0,
    interval_s: float = 2.0,
) -> dict[str, Any]:
    flash_result = flash_meter(port=port, manifest=manifest)
    scan_result = wait_for_meter(ifname=ifname, manifest=manifest, timeout_s=timeout_s, interval_s=interval_s)
    connect_result = wifi.connect(
        ifname=ifname,
        manifest=manifest,
        ssid=ssid,
        ssid_suffix=ssid_suffix,
    )
    return {
        "ok": True,
        "instrument_id": manifest.get("id"),
        "port": port,
        "ifname": ifname,
        "flash_result": flash_result,
        "scan_matches": scan_result.get("matches", []),
        "connected_ssid": connect_result.get("connected_ssid"),
        "ap_ip": connect_result.get("ap_ip"),
        "tcp_port": connect_result.get("tcp_port"),
    }


def ping_ip(host: str, timeout_s: float = 1.0, count: int = 1) -> dict[str, Any]:
    target = str(host or "").strip()
    if not target:
        raise ValueError("ping target host is required")
    packets = max(1, int(count))
    wait_s = max(1, int(timeout_s))
    cmd = ["ping", "-c", str(packets), "-W", str(wait_s), target]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return {
        "ok": proc.returncode == 0,
        "host": target,
        "timeout_s": timeout_s,
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def ensure_meter_reachable(
    manifest: dict,
    host: str | None = None,
    timeout_s: float = 1.0,
) -> dict[str, Any]:
    wifi_cfg = manifest.get("wifi") if isinstance(manifest.get("wifi"), dict) else {}
    target = str(host or wifi_cfg.get("ap_ip") or "192.168.4.1").strip()
    inst_id = str(manifest.get("id") or "meter").strip()
    result = ping_ip(target, timeout_s=timeout_s)
    if not result.get("ok"):
        raise RuntimeError(
            f"meter {inst_id} at {target} is unreachable and needs manual checking. "
            "Suggestion: add a meter reset feature."
        )
    return {
        "ok": True,
        "instrument_id": inst_id,
        "host": target,
        "ping": result,
    }


def ready_meter(
    ifname: str,
    manifest: dict,
    ssid: str | None = None,
    ssid_suffix: str | None = None,
    host: str | None = None,
    port: int | None = None,
) -> dict[str, Any]:
    scan_result = wifi.scan(ifname=ifname, manifest=manifest)
    connect_result = wifi.connect(
        ifname=ifname,
        manifest=manifest,
        ssid=ssid,
        ssid_suffix=ssid_suffix,
    )
    cfg = {
        "host": host or connect_result.get("ap_ip") or "192.168.4.1",
        "port": port or connect_result.get("tcp_port") or 9000,
    }
    ping_result = esp32s3_dev_c_meter_tcp.ping(cfg)
    return {
        "ok": True,
        "instrument_id": manifest.get("id"),
        "ifname": ifname,
        "scan_matches": scan_result.get("matches", []),
        "connected_ssid": connect_result.get("connected_ssid"),
        "ap_ip": cfg["host"],
        "tcp_port": cfg["port"],
        "ping": ping_result,
    }
