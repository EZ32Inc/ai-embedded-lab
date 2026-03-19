from __future__ import annotations

from unittest.mock import patch

from ael.instruments.backends.stlink import StlinkBackend, invoke


def _instrument() -> dict:
    return {
        "name": "stlink_1",
        "driver": "stlink",
        "connection": {"host": "127.0.0.1", "gdb_port": 4242},
        "config": {"target_id": 1},
    }


def test_stlink_backend_reports_structured_unsupported_action():
    backend = StlinkBackend()
    out = backend.execute("gpio_measure", _instrument(), {}, {"dut": "dut1"})
    assert out["status"] == "failure"
    assert out["action"] == "gpio_measure"
    assert out["error"]["code"] == "unsupported_action"


def test_stlink_backend_reports_structured_reset_success():
    backend = StlinkBackend()
    with patch(
        "ael.instruments.backends.stlink_backend.actions.reset.gdb_batch",
        return_value="monitor reset run\nok\n",
    ):
        out = backend.execute("reset", _instrument(), {}, {"dut": "dut1"})
    assert out["status"] == "success"
    assert out["action"] == "reset"


def test_stlink_invoke_bridges_structured_result_to_legacy_shape():
    with patch(
        "ael.instruments.backends.stlink_backend.actions.debug_halt.gdb_batch",
        return_value="monitor halt\nok\n",
    ):
        out = invoke("debug_halt", _instrument(), {}, {"dut": "dut1"})
    assert out["ok"] is True
    assert out["action"] == "debug_halt"
    assert out["instrument"] == "stlink_1"
