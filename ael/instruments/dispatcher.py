"""
Central action dispatcher for Instrument Action Model v0.1.

Primary entry point:

    from ael.instruments.dispatcher import run_action

    result = run_action(dut="stm32f103_target_1", action="flash", request={"firmware": "build/app.elf"})
    result = run_action(instrument="esp_jtag_1", action="gpio_measure", request={"channel": "ch1"})

The dispatcher:
  1. validates the action name and required request fields
  2. resolves the DUT or instrument from the catalog
  3. selects a compatible instrument if needed
  4. routes to the correct backend
  5. returns a standard result dict

The catalog is loaded once and cached.  Pass catalog= explicitly to use a
custom catalog (useful in tests or when configs live in a non-default location).
"""

from __future__ import annotations

from typing import Any

from .action_registry import validate_action
from .config_loader import InstrumentCatalog, load_catalog
from .result import make_error_result
from .selection import select_instrument_for_action

# Mapping from driver name -> backend module path
_DRIVER_BACKENDS: dict[str, str] = {
    "stlink": "ael.instruments.backends.stlink",
    "esp_remote_jtag": "ael.instruments.backends.esp_remote_jtag",
    "esp32_jtag": "ael.instruments.backends.esp32_jtag.backend",
    "usb_uart_bridge": "ael.instruments.backends.usb_uart_bridge",
}

_catalog_cache: InstrumentCatalog | None = None


def _get_catalog() -> InstrumentCatalog:
    global _catalog_cache
    if _catalog_cache is None:
        _catalog_cache = load_catalog()
    return _catalog_cache


def _get_backend(driver: str):
    """Import and return the backend module for a given driver name."""
    module_path = _DRIVER_BACKENDS.get(driver)
    if not module_path:
        return None
    import importlib
    try:
        return importlib.import_module(module_path)
    except ImportError as exc:
        raise ImportError(f"Cannot load backend for driver '{driver}': {exc}") from exc


def run_action(
    *,
    dut: str | None = None,
    instrument: str | None = None,
    action: str,
    request: dict | None = None,
    catalog: InstrumentCatalog | None = None,
) -> dict[str, Any]:
    """Execute an instrument action.

    Either *dut* or *instrument* must be provided, not both.

    Args:
        dut:        DUT name — system selects a compatible attached instrument.
        instrument: Instrument name — used directly, no selection needed.
        action:     Action name (e.g. "flash", "reset", "gpio_measure").
        request:    Action parameters dict.
        catalog:    Optional explicit catalog; uses default if not given.

    Returns:
        Standard result dict with at least: ok, action, instrument, dut.
    """
    request = request or {}

    if dut is None and instrument is None:
        return make_error_result(
            action=action,
            instrument=None,
            dut=None,
            error_code="invalid_request",
            message="Either 'dut' or 'instrument' must be provided",
        )

    if dut is not None and instrument is not None:
        return make_error_result(
            action=action,
            instrument=instrument,
            dut=dut,
            error_code="invalid_request",
            message="Provide either 'dut' or 'instrument', not both",
        )

    # Validate action and required request fields
    validation_error = validate_action(action, request)
    if validation_error:
        return make_error_result(
            action=action,
            instrument=instrument,
            dut=dut,
            error_code="invalid_request" if "requires" in validation_error else "unknown_action",
            message=validation_error,
        )

    cat = catalog or _get_catalog()
    context: dict[str, Any] = {}

    if dut is not None:
        # DUT-oriented invocation: select a compatible instrument
        dut_entry = cat.get_dut(dut)
        if dut_entry is None:
            return make_error_result(
                action=action,
                instrument=None,
                dut=dut,
                error_code="invalid_request",
                message=f"DUT '{dut}' not found in catalog. Known DUTs: {cat.list_duts()}",
            )
        instrument_entry = select_instrument_for_action(dut, action, cat)
        if instrument_entry is None:
            return make_error_result(
                action=action,
                instrument=None,
                dut=dut,
                error_code="no_instrument_available",
                message=f"No attached instrument for DUT '{dut}' supports action '{action}'",
            )
        context["dut"] = dut

    else:
        # Instrument-oriented invocation
        instrument_entry = cat.get_instrument(instrument)
        if instrument_entry is None:
            return make_error_result(
                action=action,
                instrument=instrument,
                dut=None,
                error_code="invalid_request",
                message=f"Instrument '{instrument}' not found in catalog. Known instruments: {cat.list_instruments()}",
            )
        # Verify that this instrument supports the action
        supported = instrument_entry.get("supports") or []
        if action not in supported:
            return make_error_result(
                action=action,
                instrument=instrument,
                dut=None,
                error_code="not_supported",
                message=f"Instrument '{instrument}' does not support action '{action}'. Supported: {supported}",
            )
        context["dut"] = None

    # Route to backend
    driver = str(instrument_entry.get("driver") or "").strip()
    backend = _get_backend(driver)
    if backend is None:
        return make_error_result(
            action=action,
            instrument=instrument_entry.get("name"),
            dut=context.get("dut"),
            error_code="not_supported",
            message=f"No backend registered for driver '{driver}'",
        )

    try:
        return backend.invoke(action, instrument_entry, request, context)
    except Exception as exc:
        return make_error_result(
            action=action,
            instrument=instrument_entry.get("name"),
            dut=context.get("dut"),
            error_code="program_failed",
            message=f"Backend error: {exc}",
            retryable=True,
        )


def invalidate_catalog_cache() -> None:
    """Force reload of the catalog on the next run_action call."""
    global _catalog_cache
    _catalog_cache = None
