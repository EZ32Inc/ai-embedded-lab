from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

import serial

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


def _read_serial_text(port: str, timeout_s: float, baud: int = 115200) -> str:
    deadline = time.time() + max(timeout_s, 0.5)
    chunks: list[bytes] = []
    with serial.Serial(port=port, baudrate=baud, timeout=0.2) as ser:
        ser.reset_input_buffer()
        while time.time() < deadline:
            waiting = ser.in_waiting
            if waiting:
                chunks.append(ser.read(waiting))
            else:
                chunk = ser.read(256)
                if chunk:
                    chunks.append(chunk)
            if chunks and sum(len(c) for c in chunks) >= 4096:
                break
    return b"".join(chunks).decode("utf-8", errors="replace")


def capture_boot_log(port: str, target: str, boot_timeout_s: float = 8.0) -> dict[str, Any]:
    timeout_s = max(1.0, boot_timeout_s)
    reset_proc: subprocess.CompletedProcess[str] | None = None
    serial_text = _read_serial_text(port=port, timeout_s=min(timeout_s, 3.0))
    if not serial_text.strip():
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
        time.sleep(0.5)
        serial_text = _read_serial_text(port=port, timeout_s=timeout_s)
    return {
        "ok": bool(serial_text.strip()),
        "reset_ok": (reset_proc.returncode == 0) if reset_proc is not None else True,
        "serial_nonempty": bool(serial_text.strip()),
        "serial_sample": "\n".join(serial_text.splitlines()[:20]),
        "serial_text": serial_text,
        "reset_raw": (((reset_proc.stdout or "") + (reset_proc.stderr or "")).strip() if reset_proc is not None else ""),
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
        expect_ok = expect_pattern in str(boot_info.get("serial_text") or "")
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
