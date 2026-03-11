from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from ael.pipeline import _simple_yaml_load


DEFAULT_LISTEN_HOST = "127.0.0.1"
DEFAULT_LISTEN_PORT = 8767
DEFAULT_TIMEOUT = 1.0


def _import_serial():
    try:
        import serial  # type: ignore
        import serial.tools.list_ports  # type: ignore

        return serial
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("pyserial is required for usb_uart_bridge_daemon") from exc


@dataclass(frozen=True)
class USBUARTDevice:
    device_path: str
    serial_number: str
    vid: Optional[int]
    pid: Optional[int]
    manufacturer: Optional[str]
    product: Optional[str]
    by_id_path: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_path": self.device_path,
            "serial_number": self.serial_number,
            "vid": self.vid,
            "pid": self.pid,
            "manufacturer": self.manufacturer,
            "product": self.product,
            "by_id_path": self.by_id_path,
        }


def _resolve_by_id_links(by_id_dir: Path) -> Dict[str, str]:
    links: Dict[str, str] = {}
    if not by_id_dir.exists():
        return links
    for entry in sorted(by_id_dir.iterdir()):
        try:
            resolved = str(entry.resolve())
        except Exception:
            continue
        links[resolved] = str(entry)
    return links


def discover_usb_uart_devices(
    *,
    list_ports_fn: Optional[Callable[[], Iterable[Any]]] = None,
    by_id_dir: str | Path = "/dev/serial/by-id",
) -> Dict[str, Any]:
    serial_mod = _import_serial()
    ports = list_ports_fn or serial_mod.tools.list_ports.comports
    by_id_links = _resolve_by_id_links(Path(by_id_dir))

    candidates: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    serial_counts: Dict[str, int] = {}

    for port in ports():
        serial_number = str(getattr(port, "serial_number", "") or "").strip()
        device_path = str(getattr(port, "device", "") or "").strip()
        item = {
            "device_path": device_path,
            "serial_number": serial_number or None,
            "vid": getattr(port, "vid", None),
            "pid": getattr(port, "pid", None),
            "manufacturer": getattr(port, "manufacturer", None),
            "product": getattr(port, "product", None),
            "by_id_path": by_id_links.get(device_path),
        }
        if not serial_number:
            item["reason"] = "missing_serial_number"
            rejected.append(item)
            continue
        serial_counts[serial_number] = serial_counts.get(serial_number, 0) + 1
        candidates.append(item)

    devices: List[Dict[str, Any]] = []
    duplicate_serials = sorted(serial for serial, count in serial_counts.items() if count > 1)
    duplicate_set = set(duplicate_serials)

    for item in candidates:
        serial_number = str(item.get("serial_number") or "")
        if serial_number in duplicate_set:
            dup = dict(item)
            dup["reason"] = "duplicate_serial_number"
            rejected.append(dup)
            continue
        devices.append(item)

    return {
        "ok": True,
        "devices": devices,
        "rejected": rejected,
        "duplicate_serial_numbers": duplicate_serials,
    }


def _default_config() -> Dict[str, Any]:
    return {
        "usb_uart_bridge": {
            "selected_serial_number": None,
            "listen": {
                "host": DEFAULT_LISTEN_HOST,
                "port": DEFAULT_LISTEN_PORT,
            },
            "serial": {
                "baudrate": 115200,
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
                "timeout": DEFAULT_TIMEOUT,
            },
        }
    }


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(out.get(key), dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_bridge_config(path: str | Path) -> Dict[str, Any]:
    cfg = _default_config()
    cfg_path = Path(path)
    if not cfg_path.exists():
        return cfg
    raw = _simple_yaml_load(str(cfg_path))
    if not isinstance(raw, dict):
        return cfg
    return _deep_merge(cfg, raw)


def _yaml_dump(data: Dict[str, Any]) -> str:
    try:
        import yaml  # type: ignore

        return yaml.safe_dump(data, sort_keys=False)
    except Exception:
        lines: List[str] = []

        def _emit(obj: Dict[str, Any], indent: int) -> None:
            prefix = " " * indent
            for key, value in obj.items():
                if isinstance(value, dict):
                    lines.append(f"{prefix}{key}:")
                    _emit(value, indent + 2)
                else:
                    dumped = "null" if value is None else json.dumps(value)
                    lines.append(f"{prefix}{key}: {dumped}")

        _emit(data, 0)
        return "\n".join(lines) + "\n"


def save_bridge_config(path: str | Path, payload: Dict[str, Any]) -> None:
    cfg_path = Path(path)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(_yaml_dump(payload), encoding="utf-8")


def select_bridge_device(config_path: str | Path, serial_number: str) -> Dict[str, Any]:
    serial_text = str(serial_number or "").strip()
    if not serial_text:
        raise ValueError("serial number is required")
    discovery = discover_usb_uart_devices()
    valid_serials = {entry["serial_number"] for entry in discovery["devices"]}
    if serial_text not in valid_serials:
        raise ValueError(f"device serial not found in current scan: {serial_text}")
    payload = load_bridge_config(config_path)
    bridge_cfg = payload.setdefault("usb_uart_bridge", {})
    bridge_cfg["selected_serial_number"] = serial_text
    save_bridge_config(config_path, payload)
    return payload


def resolve_selected_device(
    config_path: str | Path,
    *,
    discovery: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = load_bridge_config(config_path)
    bridge_cfg = payload.get("usb_uart_bridge", {}) if isinstance(payload.get("usb_uart_bridge"), dict) else {}
    selected_serial = str(bridge_cfg.get("selected_serial_number") or "").strip()
    if not selected_serial:
        return {"ok": False, "error": "no selected serial number configured"}
    current = discovery or discover_usb_uart_devices()
    if selected_serial in set(current.get("duplicate_serial_numbers") or []):
        return {"ok": False, "error": f"configured serial number is duplicated in current scan: {selected_serial}"}
    for item in current.get("devices", []):
        if str(item.get("serial_number") or "") == selected_serial:
            return {"ok": True, "selected_serial_number": selected_serial, "device": item}
    return {
        "ok": False,
        "selected_serial_number": selected_serial,
        "error": f"configured serial number not present: {selected_serial}",
    }


def doctor_selected_device(
    config_path: str | Path,
    *,
    serial_factory: Optional[Callable[..., Any]] = None,
    discovery: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    current = discovery or discover_usb_uart_devices()
    resolved = resolve_selected_device(config_path, discovery=current)
    payload = {
        "ok": False,
        "present": False,
        "openable": False,
        "selected_serial_number": resolved.get("selected_serial_number"),
        "resolved_tty_path": None,
        "device": resolved.get("device"),
        "error": resolved.get("error"),
    }
    if not resolved.get("ok"):
        return payload
    device = resolved["device"]
    payload["present"] = True
    payload["resolved_tty_path"] = device.get("device_path")

    config = load_bridge_config(config_path)
    serial_cfg = config.get("usb_uart_bridge", {}).get("serial", {})
    factory = serial_factory
    if factory is None:
        serial_mod = _import_serial()
        factory = serial_mod.Serial
    try:
        handle = factory(
            port=device.get("device_path"),
            baudrate=int(serial_cfg.get("baudrate", 115200)),
            bytesize=int(serial_cfg.get("bytesize", 8)),
            parity=str(serial_cfg.get("parity", "N")),
            stopbits=float(serial_cfg.get("stopbits", 1)),
            timeout=float(serial_cfg.get("timeout", DEFAULT_TIMEOUT)),
        )
        try:
            payload["openable"] = True
            payload["ok"] = True
        finally:
            try:
                handle.close()
            except Exception:
                pass
    except Exception as exc:
        payload["error"] = str(exc)
    return payload


class USBUARTBridgeService:
    def __init__(
        self,
        config_path: str | Path,
        *,
        serial_factory: Optional[Callable[..., Any]] = None,
        list_ports_fn: Optional[Callable[[], Iterable[Any]]] = None,
        by_id_dir: str | Path = "/dev/serial/by-id",
    ) -> None:
        self.config_path = str(config_path)
        self._serial_factory = serial_factory
        self._list_ports_fn = list_ports_fn
        self._by_id_dir = by_id_dir
        self._serial_handle = None

    def _discovery(self) -> Dict[str, Any]:
        return discover_usb_uart_devices(list_ports_fn=self._list_ports_fn, by_id_dir=self._by_id_dir)

    def _serial_settings(self) -> Dict[str, Any]:
        payload = load_bridge_config(self.config_path)
        bridge_cfg = payload.get("usb_uart_bridge", {}) if isinstance(payload.get("usb_uart_bridge"), dict) else {}
        serial_cfg = bridge_cfg.get("serial", {}) if isinstance(bridge_cfg.get("serial"), dict) else {}
        return {
            "baudrate": int(serial_cfg.get("baudrate", 115200)),
            "bytesize": int(serial_cfg.get("bytesize", 8)),
            "parity": str(serial_cfg.get("parity", "N")),
            "stopbits": float(serial_cfg.get("stopbits", 1)),
            "timeout": float(serial_cfg.get("timeout", DEFAULT_TIMEOUT)),
        }

    def _serial_class(self):
        if self._serial_factory is not None:
            return self._serial_factory
        serial_mod = _import_serial()
        return serial_mod.Serial

    def status(self) -> Dict[str, Any]:
        cfg = load_bridge_config(self.config_path)
        selected = resolve_selected_device(self.config_path, discovery=self._discovery())
        return {
            "ok": True,
            "config_path": self.config_path,
            "selected_serial_number": cfg.get("usb_uart_bridge", {}).get("selected_serial_number"),
            "selected_device": selected.get("device"),
            "serial_open": self._serial_handle is not None,
        }

    def list_devices(self) -> Dict[str, Any]:
        return self._discovery()

    def show_selected_device(self) -> Dict[str, Any]:
        return resolve_selected_device(self.config_path, discovery=self._discovery())

    def doctor(self) -> Dict[str, Any]:
        return doctor_selected_device(
            self.config_path,
            serial_factory=self._serial_factory,
            discovery=self._discovery(),
        )

    def open(self) -> Dict[str, Any]:
        if self._serial_handle is not None:
            return {"ok": True, "already_open": True}
        resolved = self.show_selected_device()
        if not resolved.get("ok"):
            return {"ok": False, "error": resolved.get("error")}
        settings = self._serial_settings()
        serial_cls = self._serial_class()
        device_path = resolved["device"]["device_path"]
        try:
            self._serial_handle = serial_cls(port=device_path, **settings)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "device_path": device_path}
        return {"ok": True, "device_path": device_path, "serial_settings": settings}

    def close(self) -> Dict[str, Any]:
        if self._serial_handle is None:
            return {"ok": True, "already_closed": True}
        try:
            self._serial_handle.close()
        finally:
            self._serial_handle = None
        return {"ok": True}

    def write(self, *, text: Optional[str] = None, data_b64: Optional[str] = None) -> Dict[str, Any]:
        if self._serial_handle is None:
            opened = self.open()
            if not opened.get("ok"):
                return opened
        payload = b""
        if data_b64:
            payload = base64.b64decode(data_b64.encode("ascii"))
        elif text is not None:
            payload = text.encode("utf-8")
        else:
            return {"ok": False, "error": "text or data_b64 is required"}
        written = self._serial_handle.write(payload)
        return {"ok": True, "bytes_written": int(written)}

    def read(self, *, size: int = 1024) -> Dict[str, Any]:
        if self._serial_handle is None:
            opened = self.open()
            if not opened.get("ok"):
                return opened
        data = self._serial_handle.read(int(size))
        text = None
        try:
            text = data.decode("utf-8")
        except Exception:
            text = None
        return {
            "ok": True,
            "bytes_read": len(data),
            "data_b64": base64.b64encode(data).decode("ascii"),
            "text": text,
        }


class _USBUARTBridgeRequestHandler(BaseHTTPRequestHandler):
    server: "_USBUARTBridgeHTTPServer"

    def _json_response(self, code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_payload(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self) -> None:  # noqa: N802
        routes = {
            "/status": self.server.service.status,
            "/list_devices": self.server.service.list_devices,
            "/show_selected_device": self.server.service.show_selected_device,
            "/doctor": self.server.service.doctor,
        }
        handler = routes.get(self.path)
        if handler is None:
            self._json_response(404, {"ok": False, "error": "unknown endpoint"})
            return
        self._json_response(200, handler())

    def do_POST(self) -> None:  # noqa: N802
        payload = self._read_payload()
        if self.path == "/open":
            result = self.server.service.open()
        elif self.path == "/close":
            result = self.server.service.close()
        elif self.path == "/write":
            result = self.server.service.write(
                text=payload.get("text"),
                data_b64=payload.get("data_b64"),
            )
        elif self.path == "/read":
            result = self.server.service.read(size=int(payload.get("size", 1024)))
        else:
            self._json_response(404, {"ok": False, "error": "unknown endpoint"})
            return
        code = 200 if result.get("ok") else 400
        self._json_response(code, result)

    def log_message(self, fmt: str, *args: Any) -> None:  # pragma: no cover - keep stdout quiet in tests
        return


class _USBUARTBridgeHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], service: USBUARTBridgeService):
        super().__init__(server_address, _USBUARTBridgeRequestHandler)
        self.service = service


def run_bridge_daemon(
    config_path: str | Path,
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    serial_factory: Optional[Callable[..., Any]] = None,
    list_ports_fn: Optional[Callable[[], Iterable[Any]]] = None,
    by_id_dir: str | Path = "/dev/serial/by-id",
) -> None:
    payload = load_bridge_config(config_path)
    listen_cfg = payload.get("usb_uart_bridge", {}).get("listen", {})
    listen_host = host or str(listen_cfg.get("host") or DEFAULT_LISTEN_HOST)
    listen_port = int(port or listen_cfg.get("port") or DEFAULT_LISTEN_PORT)
    service = USBUARTBridgeService(
        config_path,
        serial_factory=serial_factory,
        list_ports_fn=list_ports_fn,
        by_id_dir=by_id_dir,
    )
    server = _USBUARTBridgeHTTPServer((listen_host, listen_port), service)
    try:
        print(f"USB-UART bridge daemon listening on http://{listen_host}:{listen_port}")
        server.serve_forever()
    finally:
        try:
            service.close()
        finally:
            server.server_close()

