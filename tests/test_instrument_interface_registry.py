from ael.instruments.interfaces.registry import resolve_control_provider, resolve_manifest_provider
from ael.instruments.registry import InstrumentRegistry



def test_manifest_provider_resolves_meter_family():
    manifest = InstrumentRegistry().get("esp32s3_dev_c_meter")
    assert manifest is not None
    provider = resolve_manifest_provider(manifest)
    assert provider is not None
    assert provider.family == "esp32_meter"
    assert "measure_digital" in provider.actions



def test_control_provider_resolves_esp32jtag_family():
    provider = resolve_control_provider(
        {
            "type_id": "esp32jtag",
            "communication": {
                "surfaces": [
                    {"name": "gdb_remote", "endpoint": "192.168.2.10:4242"},
                    {"name": "web_api", "endpoint": "https://192.168.2.10:443"},
                ]
            },
        }
    )
    assert provider is not None
    assert provider.family == "esp32jtag"
    assert "program_firmware" in provider.actions
    assert "capture_signature" in provider.actions



def test_control_provider_resolves_stlink_family():
    provider = resolve_control_provider(
        {
            "type_id": "stlink",
            "ip": "127.0.0.1",
            "gdb_port": 4242,
            "communication": {
                "surfaces": [
                    {"name": "gdb_remote", "endpoint": "127.0.0.1:4242"},
                ]
            },
        }
    )
    assert provider is not None
    assert provider.family == "stlink"
    assert "program_firmware" in provider.actions



def test_manifest_provider_resolves_usb_uart_family():
    manifest = InstrumentRegistry().get("usb_uart_bridge_daemon")
    assert manifest is not None
    provider = resolve_manifest_provider(manifest)
    assert provider is not None
    assert provider.family == "usb_uart_bridge"
    assert "write_uart" in provider.actions



def test_helper_profiles_resolve_for_control_and_manifest():
    from ael.instruments.interfaces.registry import control_native_interface, manifest_native_interface

    control_profile = control_native_interface(
        {
            "type_id": "stlink",
            "ip": "127.0.0.1",
            "gdb_port": 4242,
            "communication": {"surfaces": [{"name": "gdb_remote", "endpoint": "127.0.0.1:4242"}]},
        }
    )
    manifest = InstrumentRegistry().get("esp32s3_dev_c_meter")
    assert manifest is not None
    manifest_profile = manifest_native_interface(manifest)
    assert control_profile["instrument_family"] == "stlink"
    assert manifest_profile["instrument_family"] == "esp32_meter"


def test_control_provider_resolves_legacy_minimal_esp32jtag_shape():
    provider = resolve_control_provider(
        {
            "ip": "192.168.2.63",
            "gdb_port": 4242,
            "web_scheme": "https",
            "web_user": "admin",
            "web_pass": "admin",
            "wifi_mode": "ST",
        }
    )
    assert provider is not None
    assert provider.family == "esp32jtag"
