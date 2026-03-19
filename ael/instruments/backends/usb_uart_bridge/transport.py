from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TransportConfig:
    serial_port: str
    baud: int = 115200
    read_timeout_s: float = 1.0


class UsbUartBridgeTransport:
    def __init__(self, cfg: TransportConfig) -> None:
        self.cfg = cfg

    def open(self):
        try:
            import serial  # type: ignore
        except ImportError as exc:
            raise RuntimeError("pyserial not installed") from exc
        return serial.Serial(
            self.cfg.serial_port,
            baudrate=self.cfg.baud,
            timeout=self.cfg.read_timeout_s,
        )

    def read_lines(self, *, duration_s: float) -> dict[str, Any]:
        captured_lines: list[str] = []
        logs: list[str] = []
        ser = self.open()
        t0 = time.monotonic()
        try:
            while time.monotonic() - t0 < duration_s:
                try:
                    line = ser.readline().decode("utf-8", errors="replace")
                except Exception as exc:
                    logs.append(f"read error: {exc}")
                    break
                if line:
                    captured_lines.append(line.rstrip())
        finally:
            ser.close()
        return {
            "lines": captured_lines,
            "capture": "\n".join(captured_lines),
            "duration_s": duration_s,
            "logs": logs,
        }

    def wait_for(self, *, pattern: str, timeout_s: float) -> dict[str, Any]:
        try:
            compiled = re.compile(pattern)
        except re.error:
            compiled = re.compile(re.escape(str(pattern)))
        ser = self.open()
        logs: list[str] = [f"Waiting for pattern '{pattern}' (timeout={timeout_s}s)"]
        captured_lines: list[str] = []
        matched_line: str | None = None
        t0 = time.monotonic()
        try:
            while time.monotonic() - t0 < timeout_s:
                try:
                    raw = ser.readline()
                except Exception as exc:
                    logs.append(f"read error: {exc}")
                    break
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").rstrip()
                captured_lines.append(line)
                if compiled.search(line):
                    matched_line = line
                    logs.append(f"Pattern matched: {line}")
                    break
        finally:
            ser.close()
        return {
            "pattern": pattern,
            "matched": matched_line is not None,
            "elapsed_s": round(time.monotonic() - t0, 3),
            "matched_line": matched_line,
            "capture_excerpt": "\n".join(captured_lines[-10:]),
            "logs": logs,
        }
