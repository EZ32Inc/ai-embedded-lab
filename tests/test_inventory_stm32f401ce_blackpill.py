from pathlib import Path

from ael import inventory


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_describe_test_for_stm32f401ce_led_blink():
    payload = inventory.describe_test("stm32f401ce_blackpill", "tests/plans/stm32f401ce_led_blink.json", REPO_ROOT)

    assert payload["ok"] is True
    assert payload["selected_dut"]["id"] == "stm32f401ce_blackpill"
    assert payload["selected_board_profile"]["id"] == "stm32f401ce_blackpill"
    assert payload["selected_board_profile"]["config"] == "configs/boards/stm32f401ce_blackpill.yaml"
    assert payload["selected_instrument"]["id"] == "esp32jtag_blackpill_192_168_2_106"
    assert payload["selected_instrument"]["endpoint"]["host"] == "192.168.2.106"
    assert any(conn["from"] == "PC13" and conn["to"] == "LED" for conn in payload["connections"])
    assert payload["connection_setup"]["resolved_wiring"]["swd"] == "P3"
    assert any(check["type"] == "led" for check in payload["expected_checks"])
