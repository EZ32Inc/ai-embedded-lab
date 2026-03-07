from __future__ import annotations

import json
import subprocess
from typing import Any


def _wifi_config(manifest: dict) -> dict:
    wifi = manifest.get("wifi")
    if not isinstance(wifi, dict):
        raise ValueError("instrument manifest missing wifi config")
    prefix = str(wifi.get("ap_ssid_prefix") or "").strip()
    password = str(wifi.get("ap_password") or "")
    ap_ip = str(wifi.get("ap_ip") or "").strip()
    tcp_port = wifi.get("tcp_port")
    if not prefix:
        raise ValueError("instrument manifest missing wifi.ap_ssid_prefix")
    return {
        "ap_ssid_prefix": prefix,
        "ap_password": password,
        "ap_ip": ap_ip,
        "tcp_port": tcp_port,
    }


def _run_nmcli(args: list[str]) -> str:
    proc = subprocess.run(
        ["nmcli", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(err or f"nmcli failed: {' '.join(args)}")
    return proc.stdout


def _parse_scan_output(raw: str, prefix: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for line in raw.splitlines():
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        in_use, ssid, signal_text = parts
        ssid = ssid.strip()
        if not ssid.startswith(prefix):
            continue
        try:
            signal = int(signal_text.strip())
        except ValueError:
            signal = None
        matches.append(
            {
                "ssid": ssid,
                "ssid_suffix": ssid[len(prefix):] if ssid.startswith(prefix) else "",
                "signal": signal,
                "in_use": in_use.strip() == "*",
            }
        )
    return sorted(matches, key=lambda item: ((item.get("signal") or -1), item.get("ssid") or ""), reverse=True)


def scan(ifname: str, manifest: dict) -> dict[str, Any]:
    wifi = _wifi_config(manifest)
    raw = _run_nmcli(["-t", "-f", "IN-USE,SSID,SIGNAL", "dev", "wifi", "list", "ifname", ifname])
    matches = _parse_scan_output(raw, wifi["ap_ssid_prefix"])
    return {
        "ok": True,
        "ifname": ifname,
        "instrument_id": manifest.get("id"),
        "ssid_prefix": wifi["ap_ssid_prefix"],
        "matches": matches,
        "wifi": wifi,
    }


def meter_list_report(ifname: str, manifest: dict) -> dict[str, Any]:
    scan_result = scan(ifname=ifname, manifest=manifest)
    matches = scan_result.get("matches", [])
    available = [
        {
            "ssid": item.get("ssid"),
            "suffix": item.get("ssid_suffix"),
            "signal": item.get("signal"),
            "in_use": bool(item.get("in_use")),
        }
        for item in matches
    ]
    return {
        "ok": True,
        "instrument_id": manifest.get("id"),
        "ifname": ifname,
        "ssid_prefix": scan_result.get("ssid_prefix"),
        "available_meters": available,
        "meter_count": len(available),
        "selection_required": len(available) != 1,
        "recommended_action": (
            "connect_directly" if len(available) == 1 else "choose_meter_by_ssid_or_suffix"
        ),
    }


def _select_match(matches: list[dict[str, Any]], ssid: str | None = None, ssid_suffix: str | None = None) -> dict[str, Any]:
    if ssid:
        for item in matches:
            if item.get("ssid") == ssid:
                return item
        raise ValueError(f"requested ssid not found: {ssid}")
    if ssid_suffix:
        normalized = ssid_suffix.upper()
        filtered = [item for item in matches if str(item.get("ssid", "")).upper().endswith(normalized)]
        if len(filtered) == 1:
            return filtered[0]
        if not filtered:
            raise ValueError(f"no matching ssid suffix found: {ssid_suffix}")
        raise ValueError(f"multiple ssids matched suffix {ssid_suffix}: {', '.join(item['ssid'] for item in filtered)}")
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError("no matching meter ssids found")
    raise ValueError("multiple matching meter ssids found; provide --ssid or --ssid-suffix")


def connect(ifname: str, manifest: dict, ssid: str | None = None, ssid_suffix: str | None = None) -> dict[str, Any]:
    scan_result = scan(ifname=ifname, manifest=manifest)
    target = _select_match(scan_result["matches"], ssid=ssid, ssid_suffix=ssid_suffix)
    password = scan_result["wifi"]["ap_password"]
    _run_nmcli(["dev", "wifi", "connect", target["ssid"], "password", password, "ifname", ifname])
    return {
        "ok": True,
        "ifname": ifname,
        "instrument_id": manifest.get("id"),
        "connected_ssid": target["ssid"],
        "signal": target.get("signal"),
        "ap_ip": scan_result["wifi"]["ap_ip"],
        "tcp_port": scan_result["wifi"]["tcp_port"],
    }


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))
