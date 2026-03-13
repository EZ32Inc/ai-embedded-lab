from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ael.adapter_registry import AdapterRegistry


def _ctx(tmp_path: Path) -> SimpleNamespace:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(artifacts_dir=artifacts_dir)


def test_signal_verify_adapter_passes_multi_signal_ratio(tmp_path):
    adapter = AdapterRegistry().get("check.signal_verify")
    step = {
        "name": "check_signal",
        "type": "check.signal_verify",
        "inputs": {
            "probe_cfg": {},
            "pin": "P0.0",
            "signal_checks": [
                {"name": "pa4_fast", "pin": "pa4", "resolved_pin": "P0.0", "min_edges": 2, "min_freq_hz": 1000.0, "duty_min": 0.4, "duty_max": 0.6},
                {"name": "pa5_half_rate", "pin": "pa5", "resolved_pin": "P0.1", "min_edges": 2, "min_freq_hz": 500.0, "duty_min": 0.4, "duty_max": 0.6},
            ],
            "signal_relations": [
                {"type": "frequency_ratio", "numerator": "pa4_fast", "denominator": "pa5_half_rate", "min_ratio": 1.8, "max_ratio": 2.2}
            ],
            "duration_s": 1.0,
            "expected_hz": 1.0,
            "min_edges": 2,
            "max_edges": 50000,
            "measure_path": str(tmp_path / "measure.json"),
            "test_limits": {},
        },
    }

    def fake_capture_signature(_probe_cfg, **_kwargs):
        return {
            "status": "ok",
            "data": {
                "blob": b"abc",
                "sample_rate_hz": 260000,
                "bit": 0,
                "pin_bits": {"P0.0": 0, "P0.1": 1},
            },
        }

    def fake_analyze(_blob, _rate, bit, min_edges=2):
        freq = 10000.0 if bit == 0 else 5000.0
        return {
            "ok": True,
            "metrics": {"freq_hz": freq, "duty": 0.5, "bit": bit},
            "reasons": [],
        }

    with patch("ael.adapter_registry.native_api_dispatch.capture_signature", side_effect=fake_capture_signature), patch(
        "ael.adapter_registry.la_verify.analyze_capture_bytes", side_effect=fake_analyze
    ):
        result = adapter.execute(step, {}, _ctx(tmp_path))

    assert result["ok"] is True
    assert result["result"]["relations"][0]["ok"] is True
    assert result["result"]["relations"][0]["ratio"] == 2.0


def test_signal_verify_adapter_fails_multi_signal_ratio(tmp_path):
    adapter = AdapterRegistry().get("check.signal_verify")
    step = {
        "name": "check_signal",
        "type": "check.signal_verify",
        "inputs": {
            "probe_cfg": {},
            "pin": "P0.0",
            "signal_checks": [
                {"name": "pa4_fast", "pin": "pa4", "resolved_pin": "P0.0", "min_edges": 2, "min_freq_hz": 1000.0, "duty_min": 0.4, "duty_max": 0.6},
                {"name": "pa5_half_rate", "pin": "pa5", "resolved_pin": "P0.1", "min_edges": 2, "min_freq_hz": 500.0, "duty_min": 0.4, "duty_max": 0.6},
            ],
            "signal_relations": [
                {"type": "frequency_ratio", "numerator": "pa4_fast", "denominator": "pa5_half_rate", "min_ratio": 1.8, "max_ratio": 2.2}
            ],
            "duration_s": 1.0,
            "expected_hz": 1.0,
            "min_edges": 2,
            "max_edges": 50000,
            "measure_path": str(tmp_path / "measure.json"),
            "test_limits": {},
        },
    }

    def fake_capture_signature(_probe_cfg, **_kwargs):
        return {
            "status": "ok",
            "data": {
                "blob": b"abc",
                "sample_rate_hz": 260000,
                "bit": 0,
                "pin_bits": {"P0.0": 0, "P0.1": 1},
            },
        }

    def fake_analyze(_blob, _rate, bit, min_edges=2):
        freq = 10000.0 if bit == 0 else 9000.0
        return {
            "ok": True,
            "metrics": {"freq_hz": freq, "duty": 0.5, "bit": bit},
            "reasons": [],
        }

    with patch("ael.adapter_registry.native_api_dispatch.capture_signature", side_effect=fake_capture_signature), patch(
        "ael.adapter_registry.la_verify.analyze_capture_bytes", side_effect=fake_analyze
    ):
        result = adapter.execute(step, {}, _ctx(tmp_path))

    assert result["ok"] is False
    assert "relation_failed:pa4_fast:pa5_half_rate" in result["facts"]["reasons"]


def test_signal_verify_adapter_fails_when_ratio_denominator_is_zero(tmp_path):
    adapter = AdapterRegistry().get("check.signal_verify")
    step = {
        "name": "check_signal",
        "type": "check.signal_verify",
        "inputs": {
            "probe_cfg": {},
            "pin": "P0.0",
            "signal_checks": [
                {"name": "pa4_fast", "pin": "pa4", "resolved_pin": "P0.0", "min_edges": 2, "min_freq_hz": 1000.0},
                {"name": "pa5_half_rate", "pin": "pa5", "resolved_pin": "P0.1", "min_edges": 2, "min_freq_hz": 0.0},
            ],
            "signal_relations": [
                {"type": "frequency_ratio", "numerator": "pa4_fast", "denominator": "pa5_half_rate", "min_ratio": 1.8, "max_ratio": 2.2}
            ],
            "duration_s": 1.0,
            "expected_hz": 1.0,
            "min_edges": 2,
            "max_edges": 50000,
            "measure_path": str(tmp_path / "measure.json"),
            "test_limits": {},
        },
    }

    def fake_capture_signature(_probe_cfg, **_kwargs):
        return {
            "status": "ok",
            "data": {
                "blob": b"abc",
                "sample_rate_hz": 260000,
                "bit": 0,
                "pin_bits": {"P0.0": 0, "P0.1": 1},
            },
        }

    def fake_analyze(_blob, _rate, bit, min_edges=2):
        freq = 10000.0 if bit == 0 else 0.0
        return {
            "ok": True,
            "metrics": {"freq_hz": freq, "duty": 0.5, "bit": bit},
            "reasons": [],
        }

    with patch("ael.adapter_registry.native_api_dispatch.capture_signature", side_effect=fake_capture_signature), patch(
        "ael.adapter_registry.la_verify.analyze_capture_bytes", side_effect=fake_analyze
    ):
        result = adapter.execute(step, {}, _ctx(tmp_path))

    assert result["ok"] is False
    assert "relation_failed:pa4_fast:pa5_half_rate" in result["facts"]["reasons"]
    assert result["result"]["relations"][0]["ok"] is False
    assert "ratio" not in result["result"]["relations"][0]


def test_signal_verify_adapter_uses_primary_bit_when_pin_bits_missing(tmp_path):
    adapter = AdapterRegistry().get("check.signal_verify")
    step = {
        "name": "check_signal",
        "type": "check.signal_verify",
        "inputs": {
            "probe_cfg": {},
            "pin": "P0.0",
            "signal_checks": [{"name": "primary", "pin": "pa4", "resolved_pin": "P0.0", "min_edges": 2, "min_freq_hz": 1000.0}],
            "duration_s": 1.0,
            "expected_hz": 1.0,
            "min_edges": 2,
            "max_edges": 50000,
            "measure_path": str(tmp_path / "measure.json"),
            "test_limits": {},
        },
    }

    def fake_capture_signature(_probe_cfg, **_kwargs):
        return {
            "status": "ok",
            "data": {
                "blob": b"abc",
                "sample_rate_hz": 260000,
                "bit": 3,
            },
        }

    observed_bits = []

    def fake_analyze(_blob, _rate, bit, min_edges=2):
        observed_bits.append(bit)
        return {
            "ok": True,
            "metrics": {"freq_hz": 10000.0, "duty": 0.5, "bit": bit},
            "reasons": [],
        }

    with patch("ael.adapter_registry.native_api_dispatch.capture_signature", side_effect=fake_capture_signature), patch(
        "ael.adapter_registry.la_verify.analyze_capture_bytes", side_effect=fake_analyze
    ):
        result = adapter.execute(step, {}, _ctx(tmp_path))

    assert result["ok"] is True
    assert observed_bits == [3]


def test_signal_verify_adapter_fails_when_capture_transport_fails(tmp_path):
    adapter = AdapterRegistry().get("check.signal_verify")
    step = {
        "name": "check_signal",
        "type": "check.signal_verify",
        "inputs": {
            "probe_cfg": {},
            "pin": "P0.0",
            "duration_s": 1.0,
            "expected_hz": 1.0,
            "min_edges": 2,
            "max_edges": 50000,
            "measure_path": str(tmp_path / "measure.json"),
            "test_limits": {},
        },
    }

    with patch(
        "ael.adapter_registry.native_api_dispatch.capture_signature",
        return_value={"status": "error", "error": {"message": "transport down"}},
    ):
        result = adapter.execute(step, {}, _ctx(tmp_path))

    assert result["ok"] is False
    assert result["failure_kind"] == "transport_error"
    assert result["facts"]["observe_ok"] is False
