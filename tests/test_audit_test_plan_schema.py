from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tools.audit_test_plan_schema import build_report, render_text


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_audit_test_plan_schema_counts_structured_and_legacy_plans():
    report = build_report(REPO_ROOT)

    assert report["ok"] is True
    assert report["summary"]["structured_count"] >= 1
    assert report["summary"]["legacy_count"] >= 1
    uart = next(item for item in report["plans"] if item["path"] == "tests/plans/stm32f103_uart_loopback_mailbox.json")
    assert uart["schema_version"] == "1.0"
    assert uart["test_kind"] == "baremetal_mailbox"
    assert uart["validation_errors"] == []
    selftest = next(item for item in report["plans"] if item["path"] == "tests/plans/instrument_esp32s3_dev_c_meter_selftest.json")
    assert selftest["schema_version"] == "1.0"
    assert selftest["test_kind"] == "instrument_specific"
    c3_meter = next(item for item in report["plans"] if item["path"] == "tests/plans/esp32c3_gpio_signature_with_meter.json")
    assert c3_meter["schema_version"] == "1.0"
    assert c3_meter["test_kind"] == "instrument_specific"
    assert report["summary"]["structured_ready_count"] >= 1
    assert report["summary"]["legacy_mailbox_candidate_count"] >= 0
    assert report["summary"]["invalid_structured_count"] == 0
    assert report["readiness"]["status"] in {"ready", "needs_attention"}
    assert report["readiness"]["invalid_structured_zero"] is True
    assert "test_kind_summary" in report
    assert report["test_kind_summary"]["baremetal_mailbox"] >= 1
    assert report["test_kind_summary"]["instrument_specific"] >= 1
    assert isinstance(report["migration"]["structured_ready"], list)
    assert isinstance(report["migration"]["legacy_mailbox_candidates"], list)
    assert "family_summary" in report
    assert isinstance(report["family_summary"], dict)


def test_audit_test_plan_schema_renders_text_summary():
    report = build_report(REPO_ROOT)
    text = render_text(report)

    assert "Test plan schema audit" in text
    assert "readiness_status:" in text
    assert "test_kind_summary:" in text
    assert "structured_count:" in text
    assert "legacy_count:" in text
    assert "migration:" in text
    assert "family_summary:" in text
    assert "baremetal_mailbox:" in text
    assert "instrument_specific:" in text
    assert "structured_ready:" in text
    assert "legacy_mailbox_candidates:" in text
    assert "stm32f407_discovery:" in text or "stm32f407:" in text
    assert "esp32s3_dev_c_meter:" in text
    assert "tests/plans/stm32f103_uart_loopback_mailbox.json [1.0]" in text
    assert "tests/plans/esp32c3_gpio_signature_with_meter.json [1.0]" in text


def test_inventory_audit_test_schema_cli_json_output():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [sys.executable, "-m", "ael", "inventory", "audit-test-schema"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    payload = json.loads(res.stdout)
    assert payload["ok"] is True
    assert "readiness" in payload
    assert "test_kind_summary" in payload
    assert "migration" in payload
    assert "structured_ready" in payload["migration"]


def test_inventory_audit_test_schema_cli_text_output():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [sys.executable, "-m", "ael", "inventory", "audit-test-schema", "--format", "text"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert "Test plan schema audit" in res.stdout
    assert "migration:" in res.stdout
    assert "readiness_status:" in res.stdout
    assert "test_kind_summary:" in res.stdout
    assert "structured_ready:" in res.stdout
