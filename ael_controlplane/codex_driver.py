from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict


class CodexDriver:
    def __init__(self, cmd: str | None = None):
        self.cmd = str(cmd or os.environ.get("AEL_CODEX_CMD", "codex")).strip() or "codex"

    def available(self) -> bool:
        return shutil.which(self.cmd) is not None

    def run(self, *, repo_root: str, prompt: str, timeout_s: int, log_path: str) -> Dict:
        enabled = os.environ.get("AEL_CODEX_ENABLED", "0").strip() == "1"
        if not enabled:
            return {"ok": False, "error_summary": "codex disabled"}
        if not self.available():
            return {"ok": False, "error_summary": "codex cmd not found"}

        start = time.monotonic()
        lp = Path(log_path)
        lp.parent.mkdir(parents=True, exist_ok=True)
        with open(lp, "w", encoding="utf-8") as logf:
            logf.write("$ " + self.cmd + "\n")
            logf.flush()
            try:
                proc = subprocess.Popen(
                    [self.cmd],
                    cwd=str(Path(repo_root).resolve()),
                    stdin=subprocess.PIPE,
                    stdout=logf,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            except Exception as exc:
                return {"ok": False, "error_summary": f"codex launch failed: {exc}"}

            try:
                proc.communicate(prompt, timeout=max(1, int(timeout_s)))
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                except Exception:
                    pass
                return {"ok": False, "error_summary": "codex timeout", "exit_code": None}

        code = int(proc.returncode if proc.returncode is not None else 1)
        return {
            "ok": code == 0,
            "error_summary": "" if code == 0 else f"codex exited with code {code}",
            "exit_code": code,
            "duration_s": round(time.monotonic() - start, 3),
            "command": self.cmd,
        }
