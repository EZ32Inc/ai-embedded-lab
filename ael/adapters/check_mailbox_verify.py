"""
check.mailbox_verify — AEL pipeline adapter

Reads the AEL debug mailbox from a target over the existing GDB/BMP endpoint
and verifies magic + status fields.  Produces a structured JSON artifact and
returns a standard AEL adapter result dict.

Expected inputs (from step["inputs"]):
    probe_ip     str   IP address of the BMP/GDB server
    probe_port   int   GDB server port (default 4242)
    target_id    int   GDB attach target ID (default 1)
    addr         str   Mailbox address, hex string (default "0x20007F00")
    settle_s     float seconds to wait after flash before reading (default 0)
    out_json     str   path where the result artifact will be written

Pass criteria:
    magic  == 0xAE100001
    status == 2  (STATUS_PASS)
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict


MAILBOX_MAGIC  = 0xAE100001
STATUS_NAMES   = {0: "EMPTY", 1: "RUNNING", 2: "PASS", 3: "FAIL"}


def _write_json(path: str | Path, payload: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _gdb_read_mailbox(endpoint: str, target_id: int, addr: int) -> Dict[str, Any]:
    """Run arm-none-eabi-gdb in batch mode and parse x/4xw output."""
    cmds = [
        "set pagination off",
        "set confirm off",
        f"target extended-remote {endpoint}",
        "monitor a",
        f"attach {target_id}",
        f"x/4xw {addr:#010x}",
        "detach",
        "quit",
    ]
    args = ["arm-none-eabi-gdb", "--batch"] + [
        item for cmd in cmds for item in ("-ex", cmd)
    ]

    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "gdb_timeout", "stdout": "", "stderr": ""}
    except FileNotFoundError:
        return {"ok": False, "error": "gdb_not_found", "stdout": "", "stderr": ""}

    stdout = proc.stdout
    stderr = proc.stderr

    # Parse: "0x20007f00:\t0xae100001\t0x00000002\t0x00000000\t0x00000000"
    words: list[int] = []
    for line in stdout.splitlines():
        if f"{addr:#010x}" in line.lower():
            found = re.findall(r"0x[0-9a-fA-F]+", line)
            words = [int(x, 16) for x in found[1:]]  # skip the address word
            break

    if len(words) < 4:
        return {
            "ok": False,
            "error": "parse_failed",
            "stdout": stdout,
            "stderr": stderr,
        }

    return {
        "ok": True,
        "magic":      words[0],
        "status":     words[1],
        "error_code": words[2],
        "detail0":    words[3],
        "stdout":     stdout,
        "stderr":     stderr,
    }


def execute(step: dict, plan: dict, ctx: Any) -> Dict[str, Any]:  # noqa: ARG001
    inputs    = step.get("inputs", {}) if isinstance(step, dict) else {}
    probe_ip  = inputs.get("probe_ip", "")
    probe_port = int(inputs.get("probe_port", 4242))
    target_id = int(inputs.get("target_id", 1))
    addr_str  = inputs.get("addr", "0x20007F00")
    settle_s  = float(inputs.get("settle_s", 0.0))
    out_json  = inputs.get("out_json")

    if not probe_ip:
        return {"ok": False, "error_summary": "check.mailbox_verify: probe_ip not set"}

    if settle_s > 0.0:
        time.sleep(settle_s)

    addr     = int(addr_str, 16)
    endpoint = f"{probe_ip}:{probe_port}"
    raw      = _gdb_read_mailbox(endpoint, target_id, addr)

    if not raw.get("ok"):
        result = {
            "ok":           False,
            "addr":         addr_str,
            "endpoint":     endpoint,
            "error":        raw.get("error", "unknown"),
            "gdb_stdout":   raw.get("stdout", ""),
            "gdb_stderr":   raw.get("stderr", ""),
        }
        if out_json:
            _write_json(out_json, result)
        return {
            "ok": False,
            "error_summary": f"mailbox read failed: {raw.get('error')}",
            "failure_kind": "mailbox_read_error",
            "result": result,
        }

    magic_ok  = raw["magic"] == MAILBOX_MAGIC
    status    = raw["status"]
    pass_ok   = magic_ok and status == 2  # STATUS_PASS

    result = {
        "ok":           pass_ok,
        "addr":         addr_str,
        "endpoint":     endpoint,
        "magic":        f"{raw['magic']:#010x}",
        "magic_ok":     magic_ok,
        "status":       status,
        "status_name":  STATUS_NAMES.get(status, f"UNKNOWN({status})"),
        "error_code":   f"{raw['error_code']:#010x}",
        "detail0":      raw["detail0"],
    }
    if out_json:
        _write_json(out_json, result)

    if not pass_ok:
        if not magic_ok:
            reason = f"magic mismatch: got {raw['magic']:#010x}, expected {MAILBOX_MAGIC:#010x}"
        else:
            reason = f"status={STATUS_NAMES.get(status, status)} (expected PASS)"
        return {
            "ok": False,
            "error_summary": f"mailbox verify failed: {reason}",
            "failure_kind": "mailbox_verify_mismatch",
            "result": result,
        }

    return {"ok": True, "result": result}
