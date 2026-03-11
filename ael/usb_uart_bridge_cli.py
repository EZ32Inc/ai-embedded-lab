from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from ael.instruments import usb_uart_bridge_daemon as bridge


DEFAULT_CONFIG = Path("configs") / "instruments" / "usb_uart_bridge.yaml"


def _render_text_list(payload):
    lines = []
    for item in payload.get("devices", []):
        lines.append(
            f"{item.get('serial_number')} {item.get('device_path')} "
            f"vid=0x{(item.get('vid') or 0):04x} pid=0x{(item.get('pid') or 0):04x}"
        )
        if item.get("manufacturer") or item.get("product"):
            lines.append(f"  {item.get('manufacturer') or ''} {item.get('product') or ''}".strip())
        if item.get("by_id_path"):
            lines.append(f"  by-id: {item.get('by_id_path')}")
    if payload.get("rejected"):
        lines.append("rejected:")
        for item in payload["rejected"]:
            lines.append(f"  {item.get('device_path')}: {item.get('reason')}")
    return "\n".join(lines) + ("\n" if lines else "")


def _render_text_show(payload):
    lines = []
    if payload.get("selected_serial_number"):
        lines.append(f"selected_serial_number: {payload.get('selected_serial_number')}")
    if payload.get("device"):
        device = payload["device"]
        lines.append(f"resolved_tty_path: {device.get('device_path')}")
        if device.get("by_id_path"):
            lines.append(f"by_id_path: {device.get('by_id_path')}")
    if payload.get("error"):
        lines.append(f"error: {payload.get('error')}")
    return "\n".join(lines) + ("\n" if lines else "")


def _render_text_doctor(payload):
    lines = [
        f"selected_serial_number: {payload.get('selected_serial_number')}",
        f"present: {payload.get('present')}",
        f"openable: {payload.get('openable')}",
    ]
    if payload.get("resolved_tty_path"):
        lines.append(f"resolved_tty_path: {payload.get('resolved_tty_path')}")
    if payload.get("error"):
        lines.append(f"error: {payload.get('error')}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m ael.usb_uart_bridge_cli")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--format", choices=["json", "text"], default="json")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list")

    select_p = sub.add_parser("select")
    select_p.add_argument("--serial", required=True)

    sub.add_parser("show")
    sub.add_parser("doctor")

    serve_p = sub.add_parser("serve")
    serve_p.add_argument("--host", default=None)
    serve_p.add_argument("--port", type=int, default=None)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config_path = args.config

    if args.cmd == "serve":
        bridge.run_bridge_daemon(config_path, host=args.host, port=args.port)
        return 0

    if args.cmd == "list":
        payload = bridge.discover_usb_uart_devices()
        if args.format == "text":
            sys.stdout.write(_render_text_list(payload))
        else:
            sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 0

    if args.cmd == "select":
        try:
            payload = bridge.select_bridge_device(config_path, args.serial)
            out = {
                "ok": True,
                "config_path": str(config_path),
                "selected_serial_number": payload["usb_uart_bridge"]["selected_serial_number"],
            }
            sys.stdout.write(json.dumps(out, indent=2, sort_keys=True) + "\n")
            return 0
        except Exception as exc:
            sys.stdout.write(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True) + "\n")
            return 1

    if args.cmd == "show":
        payload = bridge.resolve_selected_device(config_path)
        if args.format == "text":
            sys.stdout.write(_render_text_show(payload))
        else:
            sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 0 if payload.get("ok") else 1

    if args.cmd == "doctor":
        payload = bridge.doctor_selected_device(config_path)
        if args.format == "text":
            sys.stdout.write(_render_text_doctor(payload))
        else:
            sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 0 if payload.get("ok") else 1

    parser.error(f"unsupported command: {args.cmd}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

