import json
from pathlib import Path

from ael.connection_model import normalize_connection_context
from ael.pipeline import _simple_yaml_load


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_live_plans_use_bench_setup_not_legacy_connections():
    plans_dir = REPO_ROOT / "tests" / "plans"
    for path in sorted(plans_dir.glob("*.json")):
        payload = _load_json(path)
        assert "connections" not in payload, f"live plan should not use legacy connections: {path.name}"


def test_meter_backed_live_plans_explicitly_confirm_ground_when_required():
    plans_dir = REPO_ROOT / "tests" / "plans"
    for path in sorted(plans_dir.glob("*_with_meter.json")):
        payload = _load_json(path)
        bench_setup = payload.get("bench_setup", {})
        assert isinstance(bench_setup, dict), f"meter plan missing bench_setup: {path.name}"
        assert bench_setup.get("ground_required") is True, f"meter plan missing ground_required: {path.name}"
        assert bench_setup.get("ground_confirmed") is True, f"meter plan missing ground_confirmed: {path.name}"


def test_probe_observed_live_boards_explicitly_include_ground_in_bench_connections():
    boards_dir = REPO_ROOT / "configs" / "boards"
    for board_name in ("rp2040_pico", "stm32f103_gpio", "stm32f103_uart", "stm32f401rct6"):
        text = (boards_dir / f"{board_name}.yaml").read_text(encoding="utf-8")
        assert "from: GND" in text, f"{board_name} missing explicit GND bench connection"


def test_live_signal_boards_have_no_semantic_conn_a_warnings_for_gpio_signature():
    plan_by_board = {
        "rp2040_pico": "rp2040_gpio_signature.json",
        "stm32f103_gpio": "stm32f103_gpio_signature.json",
    }
    for board_name, plan_name in plan_by_board.items():
        test_payload = _load_json(REPO_ROOT / "tests" / "plans" / plan_name)
        raw = _simple_yaml_load(str(REPO_ROOT / "configs" / "boards" / f"{board_name}.yaml"))
        board_cfg = raw.get("board", {}) if isinstance(raw, dict) else {}
        ctx = normalize_connection_context(board_cfg, test_payload, required_wiring=["verify"])
        semantic = [
            item
            for item in ctx.warnings
            if "observe_map.sig resolves" in item or "verification view" in item or "test pin" in item
        ]
        assert semantic == [], f"{board_name} has semantic ConnA warning(s): {semantic}"


def test_generated_example_plans_expose_formal_connection_contract_extensions():
    plan_names = (
        "rp2040_uart_banner.json",
        "rp2040_adc_banner.json",
        "rp2040_spi_banner.json",
        "rp2040_i2c_banner.json",
        "rp2350_gpio_signature.json",
        "rp2350_uart_banner.json",
        "stm32f103_uart_banner.json",
        "stm32f103_adc_banner.json",
        "stm32f103_spi_banner.json",
        "stm32f103_i2c_banner.json",
        "esp32c6_uart_banner.json",
        "esp32c6_adc_meter.json",
        "esp32c6_spi_banner.json",
        "esp32c6_i2c_banner.json",
    )
    plans_dir = REPO_ROOT / "tests" / "plans"
    for name in plan_names:
        payload = _load_json(plans_dir / name)
        bench_setup = payload.get("bench_setup", {})
        assert isinstance(bench_setup, dict) and bench_setup, f"generated example missing bench_setup: {name}"
        if "serial_console" in bench_setup:
            assert isinstance(bench_setup.get("serial_console"), dict), f"generated example malformed serial_console: {name}"
            serial = bench_setup["serial_console"]
            assert serial.get("port"), f"generated example missing serial_console.port: {name}"
            assert serial.get("baud"), f"generated example missing serial_console.baud: {name}"

        if "adc" in name:
            external = bench_setup.get("external_inputs")
            assert isinstance(external, list) and external, f"adc example missing external_inputs: {name}"
            assert external[0].get("status"), f"adc example missing external_inputs.status: {name}"
        if "spi" in name:
            signals = bench_setup.get("peripheral_signals")
            assert isinstance(signals, list) and signals, f"spi example missing peripheral_signals: {name}"
        if "i2c" in name:
            signals = bench_setup.get("peripheral_signals")
            assert isinstance(signals, list) and signals, f"i2c example missing peripheral_signals: {name}"
