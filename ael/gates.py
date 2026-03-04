from __future__ import annotations

import json
import os
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
        if status == STATUS_FAIL:
            if idx == 4 and _hardware_missing(combined):
                status = STATUS_HAR
                summary = "hardware gate requires manual action"
                hints.append("Verify hardware connection and permissions before retrying.")
                hints.append("Rerun command: python3 -m ael pack --pack packs/esp32meter1.json")
            else:
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
