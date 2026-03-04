from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


DEFAULT_GATE_COMMANDS = [
    "python3 tools/ael_guard.py --fast",
    "python3 tools/runner_smoke.py",
    "python3 tools/agent_smoke.py",
    "python3 -m ael pack --pack packs/esp32meter1.json",
]


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


def run_gates(run_dir: str | Path, gates_path: str | None = None) -> Dict:
    commands = _load_gate_commands(gates_path)
    run_path = Path(run_dir)
    logs_dir = run_path / "logs" / "gates"
    logs_dir.mkdir(parents=True, exist_ok=True)

    gate_results: List[Dict] = []
    overall = "pass"

    for idx, cmd in enumerate(commands, start=1):
        log_path = logs_dir / f"gate_{idx:02d}.log"
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

        short_out = combined
        if len(short_out) > 1200:
            short_out = short_out[:1200] + "\n...<truncated>..."

        status = "pass" if int(proc.returncode) == 0 else "fail"
        summary = ""
        if status == "fail":
            summary = f"gate failed: {cmd}"
            if idx == 4 and _hardware_missing(combined):
                status = "human_action_required"
                summary = "hardware gate requires manual action"
                overall = "human_action_required"
            elif overall == "pass":
                overall = "fail"

        gate_results.append(
            {
                "index": idx,
                "command": cmd,
                "exit_code": int(proc.returncode),
                "status": status,
                "summary": summary,
                "stdout_stderr": short_out,
                "log_path": str(log_path),
            }
        )

    if overall == "pass":
        for item in gate_results:
            if item.get("status") == "human_action_required":
                overall = "human_action_required"
                break
            if item.get("status") == "fail":
                overall = "fail"
                break

    return {
        "overall": overall,
        "commands": commands,
        "results": gate_results,
        "logs_dir": str(logs_dir),
    }
