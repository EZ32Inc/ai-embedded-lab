from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any

from .errors import DeviceBusy, InvalidRequest, RequestTimeout, TransportUnavailable


@dataclass
class TransportConfig:
    host: str
    port: int
    timeout_s: float = 10.0


class Esp32JtagTransport:
    """Thin request/response transport for the ESP32-JTAG service."""

    def __init__(self, config: TransportConfig) -> None:
        self.config = config

    def request(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not command:
            raise InvalidRequest("command must not be empty")
        req = {"command": command, "payload": payload}
        raw_response = self._send_json(req)
        if not isinstance(raw_response, dict):
            raise TransportUnavailable("invalid non-dict response from device")
        if raw_response.get("busy") is True:
            raise DeviceBusy("device reported busy")
        return raw_response

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
