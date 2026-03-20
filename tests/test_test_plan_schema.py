from __future__ import annotations

from ael.test_plan_schema import extract_plan_metadata


def test_extract_plan_metadata_defaults_legacy_when_schema_version_is_absent():
    payload = {
        "name": "legacy_plan",
        "board": "demo_board",
    }

    metadata = extract_plan_metadata(payload)

    assert metadata["schema_version"] == "legacy"
    assert metadata["declared_schema_version"] is None
    assert metadata["test_kind"] is None
    assert metadata["validation_errors"] == []


def test_extract_plan_metadata_accepts_structured_v1_plan():
    payload = {
        "schema_version": "1.0",
        "test_kind": "baremetal_mailbox",
        "name": "structured_mailbox",
        "supported_instruments": ["stlink", "esp32jtag"],
        "requires": {"mailbox": True, "datacapture": False},
        "labels": ["mailbox", "portable"],
        "covers": ["uart"],
    }

    metadata = extract_plan_metadata(payload)

    assert metadata["schema_version"] == "1.0"
    assert metadata["test_kind"] == "baremetal_mailbox"
    assert metadata["supported_instruments"] == ["stlink", "esp32jtag"]
    assert metadata["requires"] == {"mailbox": True, "datacapture": False}
    assert metadata["labels"] == ["mailbox", "portable"]
    assert metadata["covers"] == ["uart"]
    assert metadata["validation_errors"] == []


def test_extract_plan_metadata_rejects_unknown_schema_version():
    metadata = extract_plan_metadata(
        {
            "schema_version": "2.7",
            "name": "future_plan",
        }
    )

    assert metadata["schema_version"] == "2.7"
    assert metadata["validation_errors"] == ["unknown schema_version: 2.7"]


def test_extract_plan_metadata_rejects_malformed_test_kind():
    metadata = extract_plan_metadata(
        {
            "schema_version": "1.0",
            "name": "broken_plan",
            "test_kind": ["mailbox"],
        }
    )

    assert "test_kind must be a non-empty string" in metadata["validation_errors"]


def test_extract_plan_metadata_rejects_malformed_supported_instruments():
    metadata = extract_plan_metadata(
        {
            "schema_version": "1.0",
            "name": "broken_plan",
            "test_kind": "baremetal_mailbox",
            "supported_instruments": ["stlink", 7],
        }
    )

    assert "supported_instruments must be a list of non-empty strings" in metadata["validation_errors"]


def test_extract_plan_metadata_rejects_malformed_requires():
    metadata = extract_plan_metadata(
        {
            "schema_version": "1.0",
            "name": "broken_plan",
            "test_kind": "baremetal_mailbox",
            "requires": {"mailbox": "yes"},
        }
    )

    assert "requires.mailbox must be boolean" in metadata["validation_errors"]


def test_extract_plan_metadata_rejects_unknown_requires_key():
    metadata = extract_plan_metadata(
        {
            "schema_version": "1.0",
            "name": "broken_plan",
            "test_kind": "baremetal_mailbox",
            "requires": {"uart_console": True},
        }
    )

    assert "unknown requires key: uart_console" in metadata["validation_errors"]


def test_extract_plan_metadata_rejects_unknown_label_value():
    metadata = extract_plan_metadata(
        {
            "schema_version": "1.0",
            "name": "broken_plan",
            "test_kind": "baremetal_mailbox",
            "labels": ["mailbox", "unexpected_label"],
        }
    )

    assert "unknown labels value: unexpected_label" in metadata["validation_errors"]


def test_extract_plan_metadata_rejects_unknown_cover_value():
    metadata = extract_plan_metadata(
        {
            "schema_version": "1.0",
            "name": "broken_plan",
            "test_kind": "instrument_specific",
            "covers": ["gpio", "banana"],
        }
    )

    assert "unknown covers value: banana" in metadata["validation_errors"]


def test_extract_plan_metadata_accepts_i2c_cover_value():
    metadata = extract_plan_metadata(
        {
            "schema_version": "1.0",
            "name": "i2c_plan",
            "test_kind": "instrument_specific",
            "covers": ["i2c", "voltage"],
        }
    )

    assert metadata["validation_errors"] == []
