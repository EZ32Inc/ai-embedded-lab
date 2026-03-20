from __future__ import annotations

from typing import Any, Dict, List


LEGACY_SCHEMA_VERSION = "legacy"
STRUCTURED_SCHEMA_VERSION = "1.0"
KNOWN_TEST_KINDS = {
    "baremetal_mailbox",
    "instrument_specific",
}
KNOWN_REQUIRES_KEYS = {
    "mailbox",
    "datacapture",
}


def extract_plan_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
    declared_schema_version = payload.get("schema_version")
    schema_version = _normalize_schema_version(declared_schema_version)
    metadata = {
        "schema_version": schema_version,
        "declared_schema_version": declared_schema_version,
        "test_kind": payload.get("test_kind"),
        "name": payload.get("name"),
        "supported_instruments": _copy_string_list(payload.get("supported_instruments")),
        "requires": _copy_dict(payload.get("requires")),
        "labels": _copy_string_list(payload.get("labels")),
        "covers": _copy_string_list(payload.get("covers")),
        "validation_errors": [],
    }
    metadata["validation_errors"] = validate_plan_metadata(payload, schema_version=schema_version)
    return metadata


def validate_plan_metadata(payload: Dict[str, Any], *, schema_version: str | None = None) -> List[str]:
    normalized_schema = schema_version if schema_version is not None else _normalize_schema_version(payload.get("schema_version"))
    errors: List[str] = []

    declared_schema_version = payload.get("schema_version")
    if declared_schema_version is not None:
        if not isinstance(declared_schema_version, str) or not declared_schema_version.strip():
            errors.append("schema_version must be a non-empty string")
        elif normalized_schema not in {LEGACY_SCHEMA_VERSION, STRUCTURED_SCHEMA_VERSION}:
            errors.append(f"unknown schema_version: {declared_schema_version}")

    if normalized_schema == STRUCTURED_SCHEMA_VERSION:
        if not isinstance(payload.get("name"), str) or not payload.get("name", "").strip():
            errors.append("structured plan requires non-empty string field: name")
        if "test_kind" not in payload:
            errors.append("structured plan requires field: test_kind")

    if "name" in payload and (not isinstance(payload.get("name"), str) or not payload.get("name", "").strip()):
        errors.append("name must be a non-empty string")

    if "test_kind" in payload:
        test_kind = payload.get("test_kind")
        if not isinstance(test_kind, str) or not test_kind.strip():
            errors.append("test_kind must be a non-empty string")
        elif test_kind not in KNOWN_TEST_KINDS:
            errors.append(f"unknown test_kind: {test_kind}")

    _validate_string_list(payload, "supported_instruments", errors)
    _validate_string_list(payload, "labels", errors)
    _validate_string_list(payload, "covers", errors)

    if "requires" in payload:
        requires = payload.get("requires")
        if not isinstance(requires, dict):
            errors.append("requires must be an object mapping requirement name to boolean")
        else:
            for key, value in requires.items():
                if not isinstance(key, str) or not key.strip():
                    errors.append("requires keys must be non-empty strings")
                    continue
                if key not in KNOWN_REQUIRES_KEYS:
                    errors.append(f"unknown requires key: {key}")
                if not isinstance(value, bool):
                    errors.append(f"requires.{key} must be boolean")

    return errors


def _normalize_schema_version(declared_schema_version: Any) -> str:
    if declared_schema_version is None:
        return LEGACY_SCHEMA_VERSION
    if isinstance(declared_schema_version, str) and declared_schema_version.strip():
        return declared_schema_version
    return ""


def _copy_string_list(value: Any) -> List[str] | None:
    if not isinstance(value, list):
        return None
    return [item for item in value if isinstance(item, str)]


def _copy_dict(value: Any) -> Dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return dict(value)


def _validate_string_list(payload: Dict[str, Any], field: str, errors: List[str]) -> None:
    if field not in payload:
        return
    value = payload.get(field)
    if not isinstance(value, list):
        errors.append(f"{field} must be a list of non-empty strings")
        return
    for item in value:
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{field} must be a list of non-empty strings")
            return
