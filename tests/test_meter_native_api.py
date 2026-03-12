from __future__ import annotations

from pathlib import Path

from ael.instruments.registry import InstrumentRegistry
from ael.instruments import meter_native_api


REPO_ROOT = Path(__file__).resolve().parents[1]


def _manifest():
    manifest = InstrumentRegistry().get("esp32s3_dev_c_meter")
    assert manifest
    return manifest


def test_meter_identify_and_capabilities():
    manifest = _manifest()
    profile = meter_native_api.native_interface_profile()
    assert profile["protocol"] == meter_native_api.NATIVE_API_PROTOCOL
    assert "measure_digital" in profile["action_commands"]

    identify = meter_native_api.identify(manifest)
    assert identify["status"] == "ok"
    assert identify["data"]["protocol_version"] == meter_native_api.NATIVE_API_PROTOCOL
    assert identify["data"]["device_id"] == "esp32s3_dev_c_meter"
    assert identify["data"]["endpoint"] == "192.168.4.1:9000"

    caps = meter_native_api.get_capabilities(manifest)
    assert caps["status"] == "ok"
    assert "measure.digital" in caps["data"]["capabilities"]
    assert "stim.digital" in caps["data"]["capabilities"]


def test_meter_status_and_doctor_error_shapes(monkeypatch):
    manifest = _manifest()

    def _fail(**kwargs):
        raise RuntimeError("meter unreachable")

    monkeypatch.setattr("ael.instruments.provision.ensure_meter_reachable", _fail)

    status = meter_native_api.get_status(manifest)
    assert status["status"] == "error"
    assert status["error"]["code"] == "meter_status_failed"
    assert status["error"]["details"]["host"] == "192.168.4.1"

    doctor = meter_native_api.doctor(manifest)
    assert doctor["status"] == "error"
    assert doctor["error"]["code"] == "meter_doctor_failed"
    assert doctor["error"]["details"]["protocol_version"] == meter_native_api.NATIVE_API_PROTOCOL


def test_meter_action_wrappers(monkeypatch):
    manifest = _manifest()

    monkeypatch.setattr(
        "ael.adapters.esp32s3_dev_c_meter_tcp.measure_digital",
        lambda cfg, pins, duration_ms=500, out_path=None: {"ok": True, "pins": pins, "duration_ms": duration_ms},
    )
    monkeypatch.setattr(
        "ael.adapters.esp32s3_dev_c_meter_tcp.measure_voltage",
        lambda cfg, gpio=4, avg=16, out_path=None: {"ok": True, "gpio": gpio, "avg": avg},
    )
    monkeypatch.setattr(
        "ael.adapters.esp32s3_dev_c_meter_tcp.stim_digital",
        lambda cfg, gpio, mode, duration_us=None, freq_hz=None, pattern=None, keep=0, out_path=None: {"ok": True, "gpio": gpio, "mode": mode},
    )

    dig = meter_native_api.measure_digital(manifest, pins=[11, 12], duration_ms=250)
    assert dig["status"] == "ok"
    assert dig["data"]["pins"] == [11, 12]

    volt = meter_native_api.measure_voltage(manifest, gpio=4, avg=8)
    assert volt["status"] == "ok"
    assert volt["data"]["avg"] == 8

    stim = meter_native_api.stim_digital(manifest, gpio=15, mode="toggle")
    assert stim["status"] == "ok"
    assert stim["data"]["mode"] == "toggle"
