from pathlib import Path

from ael.instrument_metadata import (
    resolve_capability_surface,
    validate_capability_surfaces,
    validate_communication,
)
from ael.instruments.manifest import load_manifest_from_file


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_validate_communication_accepts_simple_and_structured_forms():
    assert validate_communication(
        {"transport": "wifi", "endpoint": "192.168.4.1:9000", "protocol": "gpio_meter_v1"}
    ) == []
    assert validate_communication(
        {
            "primary": "gdb_remote",
            "surfaces": [
                {"name": "gdb_remote", "transport": "wifi", "endpoint": "192.168.2.98:4242", "protocol": "gdb_remote"},
                {"name": "web_api", "transport": "wifi", "endpoint": "https://192.168.2.98:443", "protocol": "esp32jtag_web_api_v1"},
            ],
        }
    ) == []


def test_validate_capability_surfaces_rejects_unknown_surface():
    errors = validate_capability_surfaces(
        {"measure.digital": "missing_surface"},
        capabilities=["measure.digital"],
        communication={"primary": "primary", "surfaces": [{"name": "primary", "transport": "wifi", "endpoint": "x", "protocol": "y"}]},
    )
    assert errors == ["capability_surfaces[measure.digital] references unknown surface: missing_surface"]


def test_resolve_capability_surface_returns_known_mapping():
    surface = resolve_capability_surface(
        "measure.digital",
        {"measure.digital": "primary"},
        {"transport": "wifi", "endpoint": "192.168.4.1:9000", "protocol": "gpio_meter_v1"},
    )
    assert surface == "primary"


def test_load_manifest_from_file_rejects_invalid_capability_surface_mapping(tmp_path):
    path = tmp_path / "bad_manifest.json"
    path.write_text(
        """
{
  "schema": "ael.instrument.manifest.v0.1",
  "id": "bad_inst",
  "kind": "instrument",
  "transports": [{"type": "tcp", "endpoint_hint": "192.168.4.1:9000"}],
  "communication": {"transport": "wifi", "endpoint": "192.168.4.1:9000", "protocol": "gpio_meter_v1"},
  "capabilities": [{"name": "measure.digital"}],
  "capability_surfaces": {"measure.digital": "web_api"}
}
""".strip(),
        encoding="utf-8",
    )
    assert load_manifest_from_file(str(path)) is None
