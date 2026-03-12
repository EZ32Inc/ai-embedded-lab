from __future__ import annotations

from ael.adapter_registry import AdapterRegistry


def test_preflight_uses_control_native_api(monkeypatch):
    registry = AdapterRegistry()
    adapter = registry.get("preflight.probe")

    monkeypatch.setattr(
        "ael.instruments.native_api_dispatch.preflight_probe",
        lambda probe_cfg: {"status": "ok", "data": {"ping_ok": True, "tcp_ok": True}},
    )

    result = adapter.execute(
        {
            "type": "preflight.probe",
            "inputs": {"probe_cfg": {"name": "ESP32JTAG", "ip": "192.168.2.98", "gdb_port": 4242}},
        },
        None,
        {},
    )
    assert result["ok"] is True
    assert result["result"]["ping_ok"] is True


def test_load_bmda_uses_control_native_api(monkeypatch):
    registry = AdapterRegistry()
    adapter = registry.get("load.gdbmi")

    monkeypatch.setattr(
        "ael.instruments.native_api_dispatch.program_firmware",
        lambda probe_cfg, **kwargs: {"status": "ok", "data": {"firmware_path": kwargs["firmware_path"]}},
    )

    result = adapter.execute(
        {
            "type": "load.bmda",
            "inputs": {
                "probe_cfg": {"name": "ESP32JTAG", "ip": "192.168.2.98", "gdb_port": 4242},
                "firmware_path": "/tmp/fake.elf",
                "flash_cfg": {},
            },
        },
        {},
        {},
    )
    assert result["ok"] is True
