from __future__ import annotations

from typing import Any, Dict, Optional

from ael.instruments.interfaces.base import InstrumentProvider
from ael.instruments.interfaces.esp32_meter import PROVIDER as ESP32_METER_PROVIDER
from ael.instruments.interfaces.esp32jtag import PROVIDER as ESP32JTAG_PROVIDER
from ael.instruments.interfaces.stlink import PROVIDER as STLINK_PROVIDER
from ael.instruments.interfaces.usb_uart_bridge import PROVIDER as USB_UART_BRIDGE_PROVIDER


_MANIFEST_PROVIDERS: dict[str, InstrumentProvider] = {
    "esp32_meter": ESP32_METER_PROVIDER,
    "usb_uart_bridge": USB_UART_BRIDGE_PROVIDER,
}

_CONTROL_PROVIDERS: dict[str, InstrumentProvider] = {
    "esp32jtag": ESP32JTAG_PROVIDER,
    "stlink": STLINK_PROVIDER,
}



def _manifest_family(manifest: Dict[str, Any]) -> Optional[str]:
    instrument_id = str(manifest.get("id") or "").strip()
    if instrument_id == "esp32s3_dev_c_meter":
        return "esp32_meter"
    if instrument_id == "usb_uart_bridge_daemon":
        return "usb_uart_bridge"
    native_interface = manifest.get("native_interface") if isinstance(manifest.get("native_interface"), dict) else {}
    family = str(native_interface.get("instrument_family") or manifest.get("type") or "").strip()
    return family or None



def _control_family(cfg: Dict[str, Any]) -> Optional[str]:
    for key in ("type_id", "probe_type", "type"):
        value = str(cfg.get(key) or "").strip()
        if value:
            return value
    communication = cfg.get("communication") if isinstance(cfg.get("communication"), dict) else {}
    surfaces = communication.get("surfaces") if isinstance(communication.get("surfaces"), list) else []
    names = {str(item.get("name") or "").strip() for item in surfaces if isinstance(item, dict)}
    if "web_api" in names:
        return "esp32jtag"
    if "gdb_remote" in names:
        host = str(cfg.get("ip") or "").strip()
        if host == "127.0.0.1":
            return "stlink"
    return None



def resolve_manifest_provider(manifest: Dict[str, Any]) -> Optional[InstrumentProvider]:
    family = _manifest_family(manifest)
    if family is None:
        return None
    return _MANIFEST_PROVIDERS.get(family)



def resolve_control_provider(cfg: Dict[str, Any]) -> Optional[InstrumentProvider]:
    family = _control_family(cfg)
    if family is None:
        return None
    return _CONTROL_PROVIDERS.get(family)
