from __future__ import annotations

from ael.instruments import control_instrument_native_api


def test_control_identify_and_capabilities():
    probe_cfg = {"name": "ESP32JTAG", "ip": "192.168.2.98", "gdb_port": 4242, "web_api_protocol": "esp32jtag_web_api_v1"}
    profile = control_instrument_native_api.native_interface_profile()
    assert profile["protocol"] == control_instrument_native_api.NATIVE_API_PROTOCOL
    ident = control_instrument_native_api.identify(probe_cfg)
    assert ident["status"] == "ok"
    assert ident["data"]["endpoint"] == "192.168.2.98:4242"
    caps = control_instrument_native_api.get_capabilities(probe_cfg)
    assert caps["status"] == "ok"
    assert "capture.signature" in caps["data"]["capabilities"]


def test_capture_signature_uses_observe_gpio(monkeypatch):
    probe_cfg = {"name": "ESP32JTAG", "ip": "192.168.2.98", "gdb_port": 4242}

    def _run(*args, **kwargs):
        capture = kwargs["capture_out"]
        capture.update({"blob": b"x", "edges": 4, "high": 10, "low": 11})
        return True

    monkeypatch.setattr("ael.adapters.observe_gpio_pin.run", _run)
    payload = control_instrument_native_api.capture_signature(
        probe_cfg,
        pin="P0.0",
        duration_s=1.0,
        expected_hz=1.0,
        min_edges=2,
        max_edges=6,
    )
    assert payload["status"] == "ok"
    assert payload["data"]["edges"] == 4
