from pathlib import Path

from ael.probe_binding import load_probe_binding


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_load_probe_binding_merges_type_and_instance_manifest():
    binding = load_probe_binding(REPO_ROOT, instance_id="esp32jtag_rp2040_lab")

    assert binding.instance_id == "esp32jtag_rp2040_lab"
    assert binding.type_id == "esp32jtag"
    assert binding.endpoint_host == "192.168.2.63"
    assert binding.endpoint_port == 4242
    assert binding.raw["probe"]["name"] == "ESP32JTAG"
    assert binding.raw["connection"]["ip"] == "192.168.2.63"
    assert binding.communication["primary"] == "gdb_remote"
    assert len(binding.communication["surfaces"]) == 2
    assert binding.instance_path and binding.instance_path.endswith("configs/instrument_instances/esp32jtag_rp2040_lab.yaml")
    assert binding.type_path and binding.type_path.endswith("configs/instrument_types/esp32jtag.yaml")


def test_load_probe_binding_keeps_legacy_probe_config_with_warning():
    binding = load_probe_binding(REPO_ROOT, probe_path="configs/esp32jtag.yaml")

    assert binding.instance_id is None
    assert binding.endpoint_host == "192.168.2.98"
    assert binding.endpoint_port == 4242
    assert binding.communication["primary"] == "gdb_remote"
    assert binding.legacy_warning == "Using legacy shared probe config; explicit instrument instance is recommended."
