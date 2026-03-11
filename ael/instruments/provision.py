from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

from . import wifi
from ael.adapters import esp32s3_dev_c_meter_tcp

RUN_METER_GUARD_TIMEOUT_S = 3.0


class MeterReachabilityError(RuntimeError):
    def __init__(self, summary: str, details: dict[str, Any] | None = None):
        super().__init__(summary)
        self.details = details if isinstance(details, dict) else {}


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


def tcp_probe(host: str, port: int, timeout_s: float = 1.0) -> dict[str, Any]:
    target = str(host or "").strip()
    target_port = int(port)
    try:
        with socket.create_connection((target, target_port), timeout=max(timeout_s, 0.1)):
            return {
                "ok": True,
                "host": target,
                "port": target_port,
                "timeout_s": timeout_s,
            }
    except Exception as exc:
        return {
            "ok": False,
            "host": target,
            "port": target_port,
            "timeout_s": timeout_s,
            "error_summary": str(exc),
        }


def meter_api_probe(host: str, port: int) -> dict[str, Any]:
    try:
        payload = esp32s3_dev_c_meter_tcp.ping({"host": host, "port": port})
        return {
            "ok": bool(isinstance(payload, dict) and payload.get("ok", False)),
            "host": host,
            "port": int(port),
            "response": payload if isinstance(payload, dict) else {},
            "error_summary": "" if isinstance(payload, dict) and payload.get("ok", False) else "meter api ping failed",
        }
    except Exception as exc:
        return {
            "ok": False,
            "host": host,
            "port": int(port),
            "response": {},
            "error_summary": str(exc),
        }


def wifi_interface_state(manifest: dict) -> dict[str, Any]:
    wifi_cfg = manifest.get("wifi") if isinstance(manifest.get("wifi"), dict) else {}
    ifname = str(
        os.environ.get("AEL_WIFI_IFNAME")
        or wifi_cfg.get("ifname")
        or ""
    ).strip()
    if not ifname:
        return {"ok": False, "reason": "ifname_unknown"}
    cmd = ["nmcli", "-t", "-f", "DEVICE,STATE,CONNECTION", "dev", "status"]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    rows = []
    for line in (proc.stdout or "").splitlines():
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        rows.append({"device": parts[0], "state": parts[1], "connection": parts[2]})
    selected = next((row for row in rows if row.get("device") == ifname), None)
    return {
        "ok": proc.returncode == 0 and selected is not None,
        "ifname": ifname,
        "device": selected,
        "command": cmd,
        "returncode": proc.returncode,
        "stderr": proc.stderr,
    }


def route_summary(host: str) -> dict[str, Any]:
    target = str(host or "").strip()
    cmd = ["ip", "route", "get", target]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return {
        "ok": proc.returncode == 0,
        "host": target,
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
    }


def ensure_meter_reachable(
    manifest: dict,
    host: str | None = None,
    timeout_s: float = 1.0,
) -> dict[str, Any]:
    wifi_cfg = manifest.get("wifi") if isinstance(manifest.get("wifi"), dict) else {}
    target = str(host or wifi_cfg.get("ap_ip") or "192.168.4.1").strip()
    inst_id = str(manifest.get("id") or "meter").strip()
    tcp_port = int(wifi_cfg.get("tcp_port") or 9000)
    ping_result = ping_ip(target, timeout_s=timeout_s)
    route_result = route_summary(target)
    wifi_state = wifi_interface_state(manifest)
    tcp_result = tcp_probe(target, tcp_port, timeout_s=timeout_s)
    api_result = meter_api_probe(target, tcp_port) if tcp_result.get("ok") else {
        "ok": False,
        "host": target,
        "port": tcp_port,
        "response": {},
        "error_summary": "skipped because tcp probe failed",
    }
    details = {
        "failure_class": "",
        "instrument_condition": "",
        "condition_scope": "bench_instrument",
        "instrument_id": inst_id,
        "host": target,
        "port": tcp_port,
        "ping": ping_result,
        "tcp": tcp_result,
        "api": api_result,
        "wifi_state": wifi_state,
        "route_summary": route_result,
    }
    if not tcp_result.get("ok"):
        details["failure_class"] = (
            "network_meter_reachability"
            if not ping_result.get("ok")
            else "network_meter_tcp"
        )
        details["instrument_condition"] = (
            "instrument_unreachable"
            if not ping_result.get("ok")
            else "instrument_transport_unavailable"
        )
        raise MeterReachabilityError(
            (
                f"meter {inst_id} at {target} is unreachable and needs manual checking. "
                "Suggestion: add a meter reset feature."
            )
            if not ping_result.get("ok")
            else f"meter {inst_id} at {target}:{tcp_port} is reachable by ping but tcp connect failed.",
            details=details,
        )
    if not api_result.get("ok"):
        details["failure_class"] = "network_meter_api"
        details["instrument_condition"] = "instrument_api_unavailable"
        raise MeterReachabilityError(
            f"meter {inst_id} at {target}:{tcp_port} accepted tcp but api ping failed.",
            details=details,
        )
    warnings: list[str] = []
    if not ping_result.get("ok"):
        warnings.append("icmp_ping_failed_but_tcp_api_succeeded")
    return {
        "ok": True,
        "instrument_id": inst_id,
        "host": target,
        "port": tcp_port,
        "ping": ping_result,
        "tcp": tcp_result,
        "api": api_result,
        "wifi_state": wifi_state,
        "route_summary": route_result,
        "instrument_condition": ("instrument_ready_with_network_warning" if warnings else "instrument_ready"),
        "condition_scope": "bench_instrument",
        "warnings": warnings,
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
