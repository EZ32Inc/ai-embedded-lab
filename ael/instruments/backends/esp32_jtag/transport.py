from __future__ import annotations

import json
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Any

from .errors import DeviceBusy, InvalidRequest, RequestTimeout, TransportUnavailable


@dataclass
class TransportConfig:
    host: str
    port: int
    timeout_s: float = 10.0
    compat_mode: bool = False
    gdb_port: int | None = None
    web_port: int | None = None
    gdb_cmd: str = "arm-none-eabi-gdb"
    target_id: int = 1
    gdb_launch_cmds: list[str] | None = None
    speed_khz: int | None = None
    gpio_channels: dict[str, Any] | None = None
    web_user: str = "admin"
    web_pass: str = "admin"
    web_verify_ssl: bool = False


class Esp32JtagTransport:
    """Thin request/response transport for the ESP32-JTAG service."""

    def __init__(self, config: TransportConfig) -> None:
        self.config = config

    def request(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not command:
            raise InvalidRequest("command must not be empty")
        if self.config.compat_mode:
            return self._compat_request(command, payload)
        req = {"command": command, "payload": payload}
        raw_response = self._send_json(req)
        if not isinstance(raw_response, dict):
            raise TransportUnavailable("invalid non-dict response from device")
        if raw_response.get("busy") is True:
            raise DeviceBusy("device reported busy")
        return raw_response

    def _compat_request(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        if command == "flash":
            return self._compat_flash(payload)
        if command == "reset":
            return self._compat_reset(payload)
        if command == "gpio_measure":
            return self._compat_gpio_measure(payload)
        raise InvalidRequest(f"compat transport does not support command: {command}")

    def _send_json(self, message: dict[str, Any]) -> dict[str, Any]:
        data = (json.dumps(message) + "\n").encode("utf-8")
        try:
            with socket.create_connection(
                (self.config.host, self.config.port),
                timeout=self.config.timeout_s,
            ) as sock:
                sock.settimeout(self.config.timeout_s)
                sock.sendall(data)
                response = self._recv_line(sock)
        except socket.timeout as exc:
            raise RequestTimeout(
                f"timeout talking to {self.config.host}:{self.config.port}"
            ) from exc
        except OSError as exc:
            raise TransportUnavailable(
                f"cannot connect to {self.config.host}:{self.config.port}: {exc}"
            ) from exc
        try:
            decoded = json.loads(response)
        except json.JSONDecodeError as exc:
            raise TransportUnavailable("device returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise TransportUnavailable("device returned non-object JSON")
        return decoded

    def _recv_line(self, sock: socket.socket) -> str:
        chunks: list[bytes] = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            if b"\n" in chunk:
                break
        if not chunks:
            raise TransportUnavailable("empty response from device")
        line = b"".join(chunks).split(b"\n", 1)[0]
        return line.decode("utf-8")

    def _compat_flash(self, payload: dict[str, Any]) -> dict[str, Any]:
        from ael.adapters import flash_bmda_gdbmi

        firmware_path = str(payload.get("firmware_path") or "").strip()
        if not firmware_path:
            raise InvalidRequest("firmware_path is required")
        probe = {
            "ip": self.config.host,
            "gdb_port": int(self.config.gdb_port or self.config.port),
            "gdb_cmd": self.config.gdb_cmd,
        }
        flash_cfg = {
            "target_id": int(self.config.target_id),
            "timeout_s": int(self.config.timeout_s),
            "gdb_launch_cmds": self.config.gdb_launch_cmds,
            "speed_khz": self.config.speed_khz,
        }
        t0 = time.monotonic()
        ok = flash_bmda_gdbmi.run(probe, firmware_path, flash_cfg=flash_cfg)
        elapsed = round(time.monotonic() - t0, 2)
        if not ok:
            return {"ok": False, "message": "flash failed", "elapsed_s": elapsed, "logs": []}
        return {
            "ok": True,
            "bytes_written": None,
            "elapsed_s": elapsed,
            "verified": None,
            "logs": [],
        }

    def _compat_reset(self, payload: dict[str, Any]) -> dict[str, Any]:
        reset_kind = str(payload.get("reset_kind") or "hard")
        gdb_port = int(self.config.gdb_port or self.config.port)
        endpoint = f"{self.config.host}:{gdb_port}"
        args = [
            self.config.gdb_cmd,
            "-q",
            "--nx",
            "--batch",
            "-ex",
            "set pagination off",
            "-ex",
            "set confirm off",
            "-ex",
            f"target extended-remote {endpoint}",
            "-ex",
            "monitor swdp_scan",
            "-ex",
            f"attach {int(self.config.target_id)}",
            "-ex",
            "monitor reset run",
            "-ex",
            "disconnect",
        ]
        t0 = time.monotonic()
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=self.config.timeout_s)
        except subprocess.TimeoutExpired as exc:
            raise RequestTimeout(f"timeout talking to {endpoint}") from exc
        except OSError as exc:
            raise TransportUnavailable(f"cannot connect to {endpoint}: {exc}") from exc
        output = (result.stdout or "") + (result.stderr or "")
        lines = [line for line in output.splitlines() if line.strip()]
        if result.returncode != 0:
            return {"ok": False, "message": f"reset failed: {output[:200]}", "logs": lines}
        return {
            "ok": True,
            "elapsed_s": round(time.monotonic() - t0, 2),
            "method": reset_kind,
            "logs": lines,
        }

    def _compat_gpio_measure(self, payload: dict[str, Any]) -> dict[str, Any]:
        from ael.adapters import observe_gpio_pin

        gpio_channels = self.config.gpio_channels or {}
        channels = payload.get("channels") or []
        if not isinstance(channels, list) or not channels:
            raise InvalidRequest("channels is required")
        resolved = []
        for item in channels:
            key = str(item)
            resolved.append(str(gpio_channels.get(key, key)))
        probe_cfg = {
            "ip": self.config.host,
            "web_port": int(self.config.web_port or 443),
            "web_user": self.config.web_user,
            "web_pass": self.config.web_pass,
            "web_verify_ssl": bool(self.config.web_verify_ssl),
            "web_suppress_ssl_warnings": True,
        }
        capture_out: dict[str, Any] = {}
        ok = observe_gpio_pin.run(
            probe_cfg=probe_cfg,
            pin=resolved[0],
            pins=resolved[1:],
            duration_s=max(0.1, float(payload.get("duration_s") or 1.0)),
            expected_hz=0,
            min_edges=0,
            max_edges=10_000_000,
            capture_out=capture_out,
            verify_edges=False,
        )
        if not ok:
            return {"ok": False, "message": f"gpio_measure failed on {resolved}", "logs": []}
        values = {
            pin: {
                "edges": int(capture_out.get("edges") or 0),
                "window_s": float(capture_out.get("window_s") or 0.0),
                "freq_hz": float(capture_out.get("freq_hz") or 0.0) if capture_out.get("freq_hz") is not None else None,
            }
            for pin in resolved
        }
        return {
            "ok": True,
            "values": values,
            "summary": f"gpio_measure ok on {resolved}",
            "pass_hint": True,
            "elapsed_s": float(capture_out.get("window_s") or 0.0),
            "logs": [],
        }
