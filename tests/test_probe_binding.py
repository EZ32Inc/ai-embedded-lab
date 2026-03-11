from pathlib import Path

from ael.probe_binding import load_probe_binding
from ael import config_resolver


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
    assert binding.capability_surfaces["swd"] == "gdb_remote"
    assert binding.capability_surfaces["gpio_in"] == "web_api"
    assert binding.metadata_validation_errors == ()
    assert binding.instance_path and binding.instance_path.endswith("configs/instrument_instances/esp32jtag_rp2040_lab.yaml")
    assert binding.type_path and binding.type_path.endswith("configs/instrument_types/esp32jtag.yaml")


def test_load_probe_binding_keeps_legacy_probe_config_with_warning():
    binding = load_probe_binding(REPO_ROOT, probe_path="configs/esp32jtag.yaml")

    assert binding.instance_id is None
    assert binding.endpoint_host == "192.168.2.98"
    assert binding.endpoint_port == 4242
    assert binding.communication["primary"] == "gdb_remote"
    assert binding.capability_surfaces["reset_out"] == "web_api"
    assert binding.metadata_validation_errors == ()
    assert binding.legacy_warning == "Using legacy shared probe config; explicit instrument instance is recommended."


def test_load_probe_binding_notify_config_has_normalized_metadata():
    binding = load_probe_binding(REPO_ROOT, probe_path="configs/esp32jtag_notify.yaml")

    assert binding.communication["primary"] == "gdb_remote"
    assert binding.capability_surfaces["swd"] == "gdb_remote"
    assert binding.metadata_validation_errors == ()


def test_control_instrument_aliases_match_legacy_board_policy(tmp_path):
    boards = tmp_path / "configs" / "boards"
    boards.mkdir(parents=True)
    (boards / "alias_board.yaml").write_text(
        """board:
  control_instrument_instance: esp32jtag_rp2040_lab
  control_instrument_required: false
  allow_legacy_control_instrument_fallback: false
  control_instrument_config: configs/instrument_instances/esp32jtag_rp2040_lab.yaml
""",
        encoding="utf-8",
    )

    assert config_resolver.resolve_control_instrument_instance(str(tmp_path), args=None, board_id="alias_board") is None
    assert config_resolver.resolve_control_instrument_config(str(tmp_path), args=None, board_id="alias_board") is None


def test_control_instrument_aliases_use_explicit_instance_when_required(tmp_path):
    boards = tmp_path / "configs" / "boards"
    boards.mkdir(parents=True)
    (boards / "alias_board.yaml").write_text(
        """board:
  control_instrument_instance: esp32jtag_rp2040_lab
  control_instrument_required: true
""",
        encoding="utf-8",
    )

    assert (
        config_resolver.resolve_control_instrument_instance(str(tmp_path), args=None, board_id="alias_board")
        == "esp32jtag_rp2040_lab"
    )
    assert config_resolver.resolve_control_instrument_config(str(tmp_path), args=None, board_id="alias_board").endswith(
        "configs/instrument_instances/esp32jtag_rp2040_lab.yaml"
    )
