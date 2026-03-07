from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from ael.pipeline import _simple_yaml_load


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_board_config_path(board: str) -> Path:
    if not board:
        raise ValueError("board is required")
    p = Path(board)
    if p.exists():
        return p
    candidate = _repo_root() / "configs" / "boards" / f"{board}.yaml"
    if candidate.exists():
        return candidate
    raise ValueError(f"board config not found: {board}")


def load_board_target(board: str) -> tuple[str, str]:
    path = resolve_board_config_path(board)
    cfg = _simple_yaml_load(str(path))
    board_cfg = cfg.get("board") if isinstance(cfg, dict) else {}
    target = str((board_cfg or {}).get("target") or "").strip()
    if not target:
        raise ValueError(f"board target missing in {path}")
    return str(path), target


def _port_present(port: str) -> bool:
    return bool(port) and os.path.exists(port)


def port_stability_check(port: str, samples: int = 5, interval_s: float = 1.0) -> dict[str, Any]:
    observed = []
    for _ in range(max(samples, 1)):
        observed.append(_port_present(port))
        if interval_s > 0:
            time.sleep(interval_s)
    return {
        "port": port,
        "samples": len(observed),
        "present_count": sum(1 for x in observed if x),
        "stable": all(observed),
        "observed": observed,
    }


def _run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, capture_output=True, text=True, **kwargs)


def probe_chip(port: str, target: str) -> dict[str, Any]:
    proc = _run(["python3", "-m", "esptool", "--chip", target, "-p", port, "chip_id"])
    combined = (proc.stdout or "") + (proc.stderr or "")
    chip_line = ""
    mac = ""
    for line in combined.splitlines():
        if line.startswith("Chip is "):
            chip_line = line.strip()
        if line.startswith("MAC: "):
            mac = line.split("MAC: ", 1)[1].strip()
    return {
        "ok": proc.returncode == 0,
        "command": " ".join(["python3", "-m", "esptool", "--chip", target, "-p", port, "chip_id"]),
        "chip_line": chip_line,
        "mac": mac,
        "raw": combined.strip(),
    }


def capture_boot_log(port: str, target: str, boot_timeout_s: float = 8.0) -> dict[str, Any]:
    timeout_s = max(1.0, boot_timeout_s)
    with tempfile.NamedTemporaryFile(prefix="ael_hwcheck_", suffix=".log", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        with open(tmp_path, "wb") as out_f:
            cat_proc = subprocess.Popen(["timeout", f"{timeout_s:.0f}s", "cat", port], stdout=out_f, stderr=subprocess.PIPE)
            time.sleep(1.0)
            reset_proc = _run(
                [
                    "python3",
                    "-m",
                    "esptool",
                    "--chip",
                    target,
                    "-p",
                    port,
                    "--before",
                    "default_reset",
                    "--after",
                    "hard_reset",
                    "chip_id",
                ]
            )
            try:
                cat_proc.wait(timeout=timeout_s + 2.0)
            except subprocess.TimeoutExpired:
                cat_proc.kill()
                cat_proc.wait(timeout=2.0)
        with open(tmp_path, "r", encoding="utf-8", errors="replace") as f:
            serial_text = f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return {
        "ok": bool(serial_text.strip()),
        "reset_ok": reset_proc.returncode == 0,
        "serial_nonempty": bool(serial_text.strip()),
        "serial_sample": "\n".join(serial_text.splitlines()[:20]),
        "reset_raw": ((reset_proc.stdout or "") + (reset_proc.stderr or "")).strip(),
    }


def run(board: str, port: str, expect_pattern: str | None = None, samples: int = 5, interval_s: float = 1.0, boot_timeout_s: float = 8.0) -> dict[str, Any]:
    board_config, target = load_board_target(board)
    port_info = port_stability_check(port=port, samples=samples, interval_s=interval_s)
    chip_info = probe_chip(port=port, target=target) if port_info["stable"] else {"ok": False, "error": "port_not_stable"}
    boot_info = capture_boot_log(port=port, target=target, boot_timeout_s=boot_timeout_s) if chip_info.get("ok") else {
        "ok": False,
        "reset_ok": False,
        "serial_nonempty": False,
        "serial_sample": "",
        "reset_raw": "",
    }
    expect_ok = None
    if expect_pattern:
        expect_ok = expect_pattern in str(boot_info.get("serial_sample") or "")
    overall_ok = bool(port_info["stable"] and chip_info.get("ok"))
    if expect_pattern and not boot_info.get("serial_nonempty"):
        overall_ok = False
    if expect_ok is False:
        overall_ok = False
    return {
        "ok": overall_ok,
        "board": board,
        "board_config": board_config,
        "target": target,
        "port": port,
        "port_check": port_info,
        "chip_check": chip_info,
        "boot_check": boot_info,
        "expect_pattern": expect_pattern,
        "expect_ok": expect_ok,
        "advisory": {
            "boot_log_detected": bool(boot_info.get("serial_nonempty")),
            "note": (
                "boot log capture is best-effort unless expect_pattern is required"
                if not expect_pattern
                else "expect_pattern requires boot log capture and token match"
            ),
        },
    }
