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
    for board_name in ("rp2040_pico", "stm32f103", "stm32f401rct6"):
        text = (boards_dir / f"{board_name}.yaml").read_text(encoding="utf-8")
        assert "from: GND" in text, f"{board_name} missing explicit GND bench connection"


def test_live_signal_boards_have_no_semantic_conn_a_warnings_for_gpio_signature():
    test_payload = _load_json(REPO_ROOT / "tests" / "plans" / "gpio_signature.json")
    for board_name in ("rp2040_pico", "stm32f103"):
        raw = _simple_yaml_load(str(REPO_ROOT / "configs" / "boards" / f"{board_name}.yaml"))
        board_cfg = raw.get("board", {}) if isinstance(raw, dict) else {}
        ctx = normalize_connection_context(board_cfg, test_payload, required_wiring=["verify"])
        semantic = [
            item
            for item in ctx.warnings
            if "observe_map.sig resolves" in item or "verification view" in item or "test pin" in item
        ]
        assert semantic == [], f"{board_name} has semantic ConnA warning(s): {semantic}"
