import os
import sys
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Optional
from ael import paths as ael_paths


@dataclass
class RunPaths:
    run_id: str
    root: Path
    meta: Path
    config_effective: Path
    preflight: Path
    preflight_log: Path
    build_log: Path
    flash_log: Path
    flash_json: Path
    observe_log: Path
    observe_uart_log: Path
    observe_uart_step_log: Path
    verify_log: Path
    measure: Path
    uart_observe: Path
    result: Path
    artifacts_dir: Path
    doctor_log: Path


class Tee:
    def __init__(self, file_obj, console, mode: str):
        self._file = file_obj
        self._console = console
        self._mode = mode
        self._buf = ""

    def write(self, s):
        if not s:
            return 0
        self._file.write(s)
        self._file.flush()
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            self._write_console_line(line + "\n")
        return len(s)

    def flush(self):
        if self._buf:
            self._write_console_line(self._buf)
            self._buf = ""
        self._file.flush()
        if hasattr(self._console, "flush"):
            self._console.flush()

    def _write_console_line(self, line):
        if self._mode == "verbose":
            self._console.write(line)
            return
        if self._mode == "quiet":
            prefixes = (
                "AI:",
                "Using ",
                "Wiring:",
                "Preflight:",
                "SWD ",
                "Build:",
                "Flash:",
                "Observe:",
                "Verify:",
                "PASS:",
                "FAIL:",
                "Summary:",
                "LKG:",
                "Run metadata saved:",
                "Run log saved:",
                "Hint:",
            )
            if line.startswith(prefixes):
                self._console.write(line)
            return
        # normal mode: drop very noisy build lines, keep status
        noisy = (
            "gmake",
            "/usr/bin/cmake",
            "Scanning dependencies",
            "Dependee ",
            "Dependencies file",
            "Consolidate compiler generated dependencies",
            "Built target",
            "Entering directory",
            "Leaving directory",
        )
        if line.startswith(noisy):
            return
        self._console.write(line)


_ORIGINAL_STDOUT = sys.stdout
_ORIGINAL_STDERR = sys.stderr
_THREAD_STREAMS = threading.local()


class ThreadLocalStreamProxy:
    def __init__(self, default_stream):
        self._default_stream = default_stream

    def _target(self):
        target = getattr(_THREAD_STREAMS, "target", None)
        if target is None:
            return self._default_stream
        return target

    def write(self, s):
        return self._target().write(s)

    def flush(self):
        target = self._target()
        if hasattr(target, "flush"):
            target.flush()

    def isatty(self):
        target = self._target()
        if hasattr(target, "isatty"):
            return target.isatty()
        return False

    @property
    def encoding(self):
        return getattr(self._target(), "encoding", None)


def ensure_thread_output_proxies():
    if not isinstance(sys.stdout, ThreadLocalStreamProxy):
        sys.stdout = ThreadLocalStreamProxy(_ORIGINAL_STDOUT)
    if not isinstance(sys.stderr, ThreadLocalStreamProxy):
        sys.stderr = ThreadLocalStreamProxy(_ORIGINAL_STDERR)


def base_stdout():
    return _ORIGINAL_STDOUT


@contextmanager
def route_thread_output(stream):
    ensure_thread_output_proxies()
    prev = getattr(_THREAD_STREAMS, "target", None)
    _THREAD_STREAMS.target = stream
    try:
        yield
    finally:
        if prev is None:
            try:
                delattr(_THREAD_STREAMS, "target")
            except AttributeError:
                pass
        else:
            _THREAD_STREAMS.target = prev


def create_run(board_id: str, test_path: str, repo_root: str) -> RunPaths:
    test_name = Path(test_path).stem
    run_id = f"{datetime.now():%Y-%m-%d_%H-%M-%S}_{board_id}_{test_name}"
    runs_root = ael_paths.runs_root()
    root = runs_root / run_id
    artifacts_dir = root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return RunPaths(
        run_id=run_id,
        root=root,
        meta=root / "meta.json",
        config_effective=root / "config_effective.json",
        preflight=root / "preflight.json",
        preflight_log=root / "preflight.log",
        build_log=root / "build.log",
        flash_log=root / "flash.log",
        flash_json=root / "flash.json",
        observe_log=root / "observe.log",
        observe_uart_log=root / "observe_uart.log",
        observe_uart_step_log=root / "observe_uart_step.log",
        verify_log=root / "verify.log",
        measure=root / "measure.json",
        uart_observe=root / "uart_observe.json",
        result=root / "result.json",
        artifacts_dir=artifacts_dir,
        doctor_log=root / "doctor.log",
    )


def open_tee(path: Path, mode: str, console: Optional[object] = None):
    if console is None:
        console = base_stdout()
    f = open(path, "w", encoding="utf-8")
    return Tee(f, console, mode), f


def ensure_parent(path: Path):
    os.makedirs(path.parent, exist_ok=True)
