from pathlib import Path

from ael import golden_reference


def test_rp2040_esp32jtag_resolves_to_existing_golden_reference():
    payload = golden_reference.resolve("rp2040", "coreweaver")

    assert payload["ok"] is True
    assert payload["exact"] is True
    assert payload["board"] == "rp2040_pico_s3jtag"
    assert payload["pack"] == "rp2040_s3jtag_full"
    assert payload["board_config"] == "configs/boards/rp2040_pico_s3jtag.yaml"
    assert "manual GDB" in payload["rule"]


def test_stm32f103_esp32jtag_resolves_to_existing_golden_reference():
    payload = golden_reference.resolve("stm32f103c8t6", "esp32jtag")

    assert payload["ok"] is True
    assert payload["exact"] is True
    assert payload["board"] == "stm32f103c6t6_bluepill_like"
    assert payload["pack"] == "stm32f103c6t6_golden"
    assert payload["board_config"] == "configs/boards/stm32f103c6t6_bluepill_like.yaml"


def test_rp2354_uses_closest_rp2040_reference_when_allowed():
    payload = golden_reference.resolve("rp2354", "s3jtag")

    assert payload["ok"] is True
    assert payload["exact"] is False
    assert payload["board"] == "rp2040_pico_s3jtag"
    assert "closest successful" in payload["reason"]


def test_unknown_target_does_not_silent_invent_reference():
    payload = golden_reference.resolve("madeup_mcu", "esp32jtag")

    assert payload["ok"] is False
    assert payload["error"] == "no golden reference found"
    assert "before hand-building" in payload["next_step"]


def test_render_text_reports_missing_paths_against_repo_root():
    payload = golden_reference.resolve("rp2040", "coreweaver")
    text = golden_reference.render_text(payload, repo_root=Path("."))

    assert "golden_reference_ok: true" in text
    assert "board: rp2040_pico_s3jtag" in text
