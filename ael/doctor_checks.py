"""Doctor command checks extracted from CLI entrypoint."""

from __future__ import annotations

import base64
import json
from pathlib import Path
import ssl
import subprocess
import urllib.request


def get_required_tools():
    repo_root = Path(__file__).resolve().parents[1]
    cfg_path = repo_root / "configs" / "doctor_tools.json"
    try:
        payload = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return ()
    tools = payload.get("required_tools", []) if isinstance(payload, dict) else []
    if not isinstance(tools, list):
        return ()
    return tuple(str(x) for x in tools if isinstance(x, str) and x.strip())


def monitor_version(probe_cfg):
    monitor_cmd = probe_cfg.get("gdb_cmd")
    ip = probe_cfg.get("ip")
    port = probe_cfg.get("gdb_port")
    if not monitor_cmd or not ip or not port:
        return False, "missing gdb_cmd/ip/port"
    try:
        res = subprocess.run(
            [
                monitor_cmd,
                "-q",
                "--nx",
                "--batch",
                "-ex",
                f"target extended-remote {ip}:{port}",
                "-ex",
                "monitor version",
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )
        ok = res.returncode == 0
        out = (res.stdout or "") + (res.stderr or "")
        return ok, out.strip()
    except Exception as exc:
        return False, str(exc)


def la_capture_ok(probe_cfg):
    try:
        ip = probe_cfg.get("ip")
        scheme = probe_cfg.get("web_scheme", "https")
        port = int(probe_cfg.get("web_port", 443))
        user = probe_cfg.get("web_user", "admin")
        password = probe_cfg.get("web_pass", "admin")
        verify_ssl = bool(probe_cfg.get("web_verify_ssl", False))

        base_url = f"{scheme}://{ip}:{port}"
        cfg = {
            "sampleRate": 1_000_000,
            "triggerPosition": 50,
            "triggerEnabled": False,
            "triggerModeOR": True,
            "captureInternalTestSignal": True,
            "channels": ["disabled"] * 16,
        }
        auth = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        headers = {"Content-Type": "application/json", "Authorization": f"Basic {auth}"}
        ctx = ssl.create_default_context()
        if not verify_ssl:
            ctx = ssl._create_unverified_context()  # nosec - local device API

        req = urllib.request.Request(
            f"{base_url}/la_configure",
            data=json.dumps(cfg).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            resp.read()

        req = urllib.request.Request(
            f"{base_url}/instant_capture",
            headers={"Authorization": f"Basic {auth}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            blob = resp.read()
        ok = len(blob or b"") > 10
        return ok, f"len={len(blob or b'')}"
    except Exception as exc:
        return False, str(exc)


def validate_config(probe_raw, board_raw, test_raw):
    issues = []
    probe = probe_raw.get("probe", {}) if isinstance(probe_raw, dict) else {}
    if not probe.get("name"):
        issues.append("probe.name missing")
    conn = probe_raw.get("connection", {}) if isinstance(probe_raw, dict) else {}
    if not (probe.get("ip") or conn.get("ip")):
        issues.append("probe ip missing")
    if not (probe.get("gdb_port") or conn.get("gdb_port")):
        issues.append("probe gdb_port missing")

    board = board_raw.get("board", {}) if isinstance(board_raw, dict) else {}
    if not board.get("name"):
        issues.append("board.name missing")
    if not board.get("target"):
        issues.append("board.target missing")
    if not board.get("default_wiring"):
        issues.append("board.default_wiring missing")
    if not board.get("safe_pins"):
        issues.append("board.safe_pins missing")
    if not board.get("observe_map"):
        issues.append("board.observe_map missing")
    if not board.get("flash"):
        issues.append("board.flash missing")

    if isinstance(test_raw, dict):
        if not test_raw.get("name"):
            issues.append("test.name missing")
        if not test_raw.get("pin"):
            issues.append("test.pin missing")
        if test_raw.get("min_freq_hz") is None:
            issues.append("test.min_freq_hz missing")
        if test_raw.get("max_freq_hz") is None:
            issues.append("test.max_freq_hz missing")
        if test_raw.get("duty_min") is None:
            issues.append("test.duty_min missing")
        if test_raw.get("duty_max") is None:
            issues.append("test.duty_max missing")
    return issues
