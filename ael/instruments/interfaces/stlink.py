from __future__ import annotations

from ael.instruments import stlink_native_api
from ael.instruments.interfaces.base import InstrumentProvider


PROVIDER = InstrumentProvider(
    family="stlink",
    native_interface_profile=stlink_native_api.native_interface_profile,
    identify=stlink_native_api.identify,
    get_capabilities=stlink_native_api.get_capabilities,
    get_status=stlink_native_api.get_status,
    doctor=stlink_native_api.doctor,
    actions={
        "preflight_probe": stlink_native_api.preflight_probe,
        "program_firmware": stlink_native_api.program_firmware,
    },
)
