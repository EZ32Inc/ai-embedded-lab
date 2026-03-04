from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


DEFAULT_GATE_COMMANDS = [
    "python3 tools/ael_guard.py --fast",
    "python3 tools/runner_smoke.py",
    "python3 tools/agent_smoke.py",
    "python3 -m ael pack --pack packs/esp32meter1.json",
]

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_SKIP = "SKIP"
STATUS_HAR = "HUMAN_ACTION_REQUIRED"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _hardware_missing(text: str) -> bool:
    low = str(text or "").lower()
    patterns = [
        "permission denied",
        "permission",
        "sudo",
        "device not found",
        "no such file or directory",
        "cannot open",
        "/dev/tty",
        "network is unreachable",
        "name or service not known",
        "connection refused",
        "download mode",
    ]
    return any(p in low for p in patterns)


def _find_device(text: str) -> str:
    m = re.search(r"(/dev/tty[A-Za-z0-9]+)", text or "")
    return m.group(1) if m else ""


def _classify_hardware_gate(command: str, exit_code: int, output: str) -> Dict:
    low = (output or "").lower()
    device = _find_device(output or "")
    hints: List[str] = []
    matched = ""
    status = STATUS_PASS if int(exit_code) == 0 else STATUS_FAIL
    summary = "hardware gate passed" if status == STATUS_PASS else f"hardware gate failed: {command}"

    def _mark_har(reason: str, detail_hints: List[str]) -> None:
        nonlocal status, summary, matched, hints
        status = STATUS_HAR
        matched = reason
        summary = f"hardware gate needs manual action ({reason})"
        hints = detail_hints

    permission_patterns = ["permission denied", "could not open port", "cannot open"]
    missing_patterns = ["no such file or directory", "port is busy or doesn't exist", "device not found"]
    busy_patterns = ["resource busy", "port is busy"]
    download_patterns = ["waiting for download", "download mode", "boot:0x0 (download"]
    notifier_patterns = ["could not resolve host: discord.com", "discord webhook failed", "name or service not known"]

    if status == STATUS_FAIL:
        if any(p in low for p in download_patterns):
            _mark_har(
                "download_mode",
                [
                    "DUT appears in bootloader/download mode.",
                    "Reset target and rerun gate.",
                    "Rerun command: python3 -m ael pack --pack packs/esp32meter1.json",
                ],
            )
        elif any(p in low for p in permission_patterns):
            _mark_har(
                "serial_permission_denied",
                [
                    f"Fix serial permissions for {device or '/dev/tty*'} (dialout/uucp group).",
                    "Rerun command: python3 -m ael pack --pack packs/esp32meter1.json",
                ],
            )
        elif any(p in low for p in missing_patterns):
            _mark_har(
                "serial_device_missing",
                [
                    f"Ensure device is connected ({device or '/dev/ttyACM*'}).",
                    "Rerun command: python3 -m ael pack --pack packs/esp32meter1.json",
                ],
            )
        elif any(p in low for p in busy_patterns):
            _mark_har(
                "serial_port_busy",
                [
                    f"Release the serial port ({device or '/dev/ttyACM*'}) from other process.",
                    "Rerun command: python3 -m ael pack --pack packs/esp32meter1.json",
                ],
            )
        elif any(p in low for p in notifier_patterns):
            status = STATUS_SKIP
            matched = "notifier_dns_warning"
            summary = "hardware gate notifier warning only"
            hints = ["Network/DNS issue for notifier; treat as non-fatal warning."]

    return {
        "status": status,
        "summary": summary,
        "hints": hints,
        "matched_error": matched,
        "device": device,
    }


def _load_gate_commands(path: str | None) -> List[str]:
    if not path:
        return list(DEFAULT_GATE_COMMANDS)
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("gates file must be a JSON object")
    commands = payload.get("commands")
    if not isinstance(commands, list) or not commands:
        raise ValueError("gates file must contain non-empty commands list")
    return [str(x) for x in commands]


def _tail_lines(text: str, count: int = 40) -> str:
    lines = (text or "").splitlines()
    if len(lines) <= count:
        return "\n".join(lines)
    return "\n".join(lines[-count:])


def _mk_gate_result(
    name: str,
    command: str,
    exit_code: int,
    status: str,
    summary: str,
    hints: Optional[List[str]],
    log_path: str,
    output_text: str,
) -> Dict:
    return {
        "name": name,
        "command": command,
        "ok": status in (STATUS_PASS, STATUS_SKIP, STATUS_HAR),
        "status": status,
        "summary": summary,
        "hints": list(hints or []),
        "evidence": {
            "exit_code": int(exit_code),
            "log_path": log_path,
            "last_lines": _tail_lines(output_text, 40),
        },
    }


def run_gates(run_dir: str | Path, gates_path: str | None = None) -> Dict:
    commands = _load_gate_commands(gates_path)
    run_path = Path(run_dir)
    logs_dir = run_path / "logs" / "gates"
    logs_dir.mkdir(parents=True, exist_ok=True)

    gate_results: List[Dict] = []
    overall_status = STATUS_PASS

    for idx, cmd in enumerate(commands, start=1):
        log_path = logs_dir / f"gate_{idx:02d}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        is_hardware_gate = "python3 -m ael pack --pack packs/esp32meter1.json" in cmd
        if is_hardware_gate and os.environ.get("AEL_SKIP_HARDWARE_GATES", "").strip() == "1":
            skip_text = "Hardware gate skipped by AEL_SKIP_HARDWARE_GATES=1"
            log_path.write_text(f"$ {cmd}\n[skip]\n{skip_text}\n", encoding="utf-8")
            gate_results.append(
                _mk_gate_result(
                    name=f"gate_{idx:02d}",
                    command=cmd,
                    exit_code=0,
                    status=STATUS_SKIP,
                    summary="hardware gate skipped by policy",
                    hints=[
                        "Set AEL_SKIP_HARDWARE_GATES=0 to run the hardware gate.",
                        "Rerun command: python3 -m ael pack --pack packs/esp32meter1.json",
                    ],
                    log_path=str(log_path),
                    output_text=skip_text,
                )
            )
            continue
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(_repo_root()),
            capture_output=True,
            text=True,
            env=dict(os.environ),
        )
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        log_path.write_text(
            f"$ {cmd}\n[exit_code] {proc.returncode}\n\n{combined}",
            encoding="utf-8",
        )

        status = STATUS_PASS if int(proc.returncode) == 0 else STATUS_FAIL
        summary = "gate passed" if status == STATUS_PASS else f"gate failed: {cmd}"
        hints: List[str] = []
        extra_evidence: Dict[str, str] = {}
        if is_hardware_gate:
            hw = _classify_hardware_gate(cmd, int(proc.returncode), combined)
            status = str(hw.get("status", status))
            summary = str(hw.get("summary", summary))
            hints = [str(x) for x in hw.get("hints", []) if str(x).strip()]
            extra_evidence = {
                "matched_error": str(hw.get("matched_error", "")),
                "device": str(hw.get("device", "")),
            }
        elif status == STATUS_FAIL:
            if _hardware_missing(combined):
                status = STATUS_HAR
                summary = "gate requires manual action"
                hints.append("External environment unavailable; rerun once fixed.")
        if status == STATUS_FAIL:
            overall_status = STATUS_FAIL
        gate_results.append(
            _mk_gate_result(
                name=f"gate_{idx:02d}",
                command=cmd,
                exit_code=int(proc.returncode),
                status=status,
                summary=summary,
                hints=hints,
                log_path=str(log_path),
                output_text=combined,
            )
        )
        if extra_evidence:
            gate_results[-1]["evidence"].update(extra_evidence)

    if overall_status != STATUS_FAIL:
        har = [x for x in gate_results if x.get("status") == STATUS_HAR]
        skip = [x for x in gate_results if x.get("status") == STATUS_SKIP]
        if har:
            overall_status = STATUS_HAR
        elif skip:
            overall_status = STATUS_SKIP
        else:
            overall_status = STATUS_PASS

    return {
        "overall": overall_status,
        "ok": overall_status in (STATUS_PASS, STATUS_SKIP, STATUS_HAR),
        "commands": commands,
        "results": gate_results,
        "logs_dir": str(logs_dir),
    }
