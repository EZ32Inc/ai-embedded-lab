from __future__ import annotations

from ael.instruments import meter_native_api
from ael.instruments.interfaces.base import InstrumentProvider


PROVIDER = InstrumentProvider(
    family="esp32_meter",
    native_interface_profile=meter_native_api.native_interface_profile,
    identify=meter_native_api.identify,
    get_capabilities=meter_native_api.get_capabilities,
    get_status=meter_native_api.get_status,
    doctor=meter_native_api.doctor,
    actions={
        "measure_digital": meter_native_api.measure_digital,
        "measure_voltage": meter_native_api.measure_voltage,
        "stim_digital": meter_native_api.stim_digital,
    },
)
