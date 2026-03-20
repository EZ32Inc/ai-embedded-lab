from __future__ import annotations

from ael.instruments import jtag_native_api
from ael.instruments.interfaces.base import InstrumentProvider


PROVIDER = InstrumentProvider(
    family="esp32jtag",
    native_interface_profile=jtag_native_api.native_interface_profile,
    identify=jtag_native_api.identify,
    get_capabilities=jtag_native_api.get_capabilities,
    get_status=jtag_native_api.get_status,
    doctor=jtag_native_api.doctor,
    actions={
        "preflight_probe": jtag_native_api.preflight_probe,
        "program_firmware": jtag_native_api.program_firmware,
        "capture_signature": jtag_native_api.capture_signature,
    },
)
