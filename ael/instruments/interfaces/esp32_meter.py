from __future__ import annotations

from ael.instruments import meter_native_api
from ael.instruments.interfaces.base import InstrumentProvider
from ael.instruments.interfaces.model import (
    normalize_capabilities_result,
    normalize_doctor_result,
    normalize_status_result,
    wrap_legacy_action,
)


METER_CAPABILITIES = {
    "measure.digital": {"actions": ["measure_digital"], "surfaces": ["meter_tcp"]},
    "measure.voltage": {"actions": ["measure_voltage"], "surfaces": ["meter_tcp"]},
    "stim.digital": {"actions": ["stim_digital"], "surfaces": ["meter_tcp"]},
}


STATUS_FALLBACK = {
    "strategy": "recover_meter_connectivity",
    "suggestion": "confirm the ESP32 meter is reachable on its control endpoint before measuring or stimulating",
}


DOCTOR_FALLBACK = {
    "strategy": "recover_meter_then_retry",
    "suggestion": "restore ESP32 meter reachability or power before retrying measurement work",
}


MEASURE_DIGITAL_FALLBACK = {
    "strategy": "recover_meter_then_retry_measurement",
    "suggestion": "restore ESP32 meter connectivity before retrying digital measurement",
}


MEASURE_VOLTAGE_FALLBACK = {
    "strategy": "recover_meter_then_retry_measurement",
    "suggestion": "restore ESP32 meter connectivity before retrying voltage measurement",
}


STIM_DIGITAL_FALLBACK = {
    "strategy": "recover_meter_then_retry_stimulus",
    "suggestion": "restore ESP32 meter connectivity before retrying digital stimulation",
}



def _get_capabilities(manifest):
    payload = meter_native_api.get_capabilities(manifest)
    return wrap_legacy_action(
        payload,
        family="esp32_meter",
        action="get_capabilities",
        success_mapper=lambda _data: normalize_capabilities_result(
            family="esp32_meter",
            capabilities=METER_CAPABILITIES,
            lifecycle_boundary=meter_native_api.native_interface_profile().get("lifecycle_scope"),
        ),
        failure_boundary="instrument_capabilities",
    )



def _get_status(manifest):
    payload = meter_native_api.get_status(manifest)
    return wrap_legacy_action(
        payload,
        family="esp32_meter",
        action="get_status",
        success_mapper=lambda data: normalize_status_result(
            family="esp32_meter",
            reachable=(data.get("reachability") or {}).get("ok") if isinstance(data.get("reachability"), dict) else None,
            health_domains=(data.get("health_domains") or {}) if isinstance(data.get("health_domains"), dict) else {},
            endpoints={"meter_tcp": f"{data.get('host')}:{data.get('port')}"} if data.get("host") and data.get("port") is not None else {},
            observations={"reachability": data.get("reachability")} if isinstance(data.get("reachability"), dict) else {},
        ),
        failure_boundary="instrument_status",
        fallback=STATUS_FALLBACK,
    )



def _doctor(manifest):
    payload = meter_native_api.doctor(manifest)
    return wrap_legacy_action(
        payload,
        family="esp32_meter",
        action="doctor",
        success_mapper=lambda data: normalize_doctor_result(
            family="esp32_meter",
            reachable=data.get("reachable"),
            checks=(data.get("checks") or {}) if isinstance(data.get("checks"), dict) else {},
            lifecycle_boundary=data.get("lifecycle_boundary") if isinstance(data.get("lifecycle_boundary"), dict) else None,
            recovery_hint="restore ESP32 meter reachability or power before retrying measurement work",
            failure_boundary="instrument_health",
        ),
        failure_boundary="instrument_health",
        fallback=DOCTOR_FALLBACK,
    )


def _measure_digital(manifest, **kwargs):
    requested = {
        "pins": list(kwargs.get("pins") or []),
        "duration_ms": kwargs.get("duration_ms", 500),
    }
    payload = meter_native_api.measure_digital(manifest, **kwargs)
    return wrap_legacy_action(
        payload,
        family="esp32_meter",
        action="measure_digital",
        requested=requested,
        success_mapper=lambda data: {
            "measurement_kind": "digital",
            "pins": list(data.get("pins") or []),
            "duration_ms": data.get("duration_ms", kwargs.get("duration_ms", 500)),
            "sample_count": data.get("samples"),
            "result_rows": list(data.get("pins") or []),
        },
        failure_boundary="instrument_measurement",
        fallback=MEASURE_DIGITAL_FALLBACK,
    )



def _measure_voltage(manifest, **kwargs):
    requested = {
        "gpio": kwargs.get("gpio", 4),
        "avg": kwargs.get("avg", 16),
    }
    payload = meter_native_api.measure_voltage(manifest, **kwargs)
    return wrap_legacy_action(
        payload,
        family="esp32_meter",
        action="measure_voltage",
        requested=requested,
        success_mapper=lambda data: {
            "measurement_kind": "voltage",
            "gpio": data.get("gpio", kwargs.get("gpio", 4)),
            "avg": data.get("avg", kwargs.get("avg", 16)),
            "voltage_v": data.get("voltage_v", data.get("v", data.get("value_v", data.get("voltage", data.get("value"))))),
            "v": data.get("v", data.get("voltage_v", data.get("value_v", data.get("voltage", data.get("value"))))),
            "mv": data.get("mv"),
            "result": dict(data),
        },
        failure_boundary="instrument_measurement",
        fallback=MEASURE_VOLTAGE_FALLBACK,
    )



def _stim_digital(manifest, **kwargs):
    requested = {
        "gpio": kwargs["gpio"],
        "mode": kwargs["mode"],
        "duration_us": kwargs.get("duration_us"),
        "freq_hz": kwargs.get("freq_hz"),
        "pattern": kwargs.get("pattern"),
        "keep": kwargs.get("keep", 0),
    }
    payload = meter_native_api.stim_digital(manifest, **kwargs)
    return wrap_legacy_action(
        payload,
        family="esp32_meter",
        action="stim_digital",
        requested=requested,
        success_mapper=lambda data: {
            "stimulus_kind": "digital",
            "gpio": data.get("gpio", kwargs["gpio"]),
            "mode": data.get("mode", kwargs["mode"]),
            "duration_us": data.get("duration_us", kwargs.get("duration_us")),
            "freq_hz": data.get("freq_hz", kwargs.get("freq_hz")),
            "pattern": data.get("pattern", kwargs.get("pattern")),
            "keep": data.get("keep", kwargs.get("keep", 0)),
            "result": dict(data),
        },
        failure_boundary="instrument_stimulus",
        fallback=STIM_DIGITAL_FALLBACK,
    )


PROVIDER = InstrumentProvider(
    family="esp32_meter",
    native_interface_profile=meter_native_api.native_interface_profile,
    identify=meter_native_api.identify,
    get_capabilities=_get_capabilities,
    get_status=_get_status,
    doctor=_doctor,
    actions={
        "measure_digital": _measure_digital,
        "measure_voltage": _measure_voltage,
        "stim_digital": _stim_digital,
    },
)
