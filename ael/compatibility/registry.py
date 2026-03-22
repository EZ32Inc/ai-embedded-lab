"""Capability registry: standard types and instrument surface key mappings.

Instrument manifests (YAML) declare capability_surfaces as a mapping of
surface-key → surface-name, e.g.:

    capability_surfaces:
      swd: gdb_remote
      gpio_in: web_api
      reset_out: web_api

The surface-keys (swd, gpio_in, …) are the instrument's hardware/protocol
capabilities.  This module maps them to the canonical capability type
vocabulary defined in the compatibility spec (§5).

Note: CAPABILITY_TAXONOMY_KEYS in ael/instruments/interfaces/model.py
(capture.digital, debug.flash, …) are INTERNAL action-contract keys used by
the pipeline, not manifest surface keys.  They are separate from this module.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Set

# ---------------------------------------------------------------------------
# Canonical capability type vocabulary (from spec §5)
# ---------------------------------------------------------------------------

#: All recognised canonical capability type strings.
CANONICAL_CAPABILITY_TYPES: FrozenSet[str] = frozenset({
    # Digital interfaces
    "swd",
    "jtag",
    "uart",
    "spi_master",
    "spi_slave",
    "i2c_master",
    "gpio_input",
    "gpio_output",
    "logic_capture",
    # Analog measurement
    "voltage_measure",
    "current_measure",
    "analog_in",
    "waveform_capture",
    # Control
    "power_control",
    "reset_control",
    "boot_mode_control",
    "relay_switch",
    # Programming / debug
    "flash_program",
    "debug_attach",
    "trace_capture",
    # System support
    "firmware_deploy",
    "serial_console",
    "result_artifact_upload",
    # Internal
    "preflight",
})

# ---------------------------------------------------------------------------
# Instrument surface-key → canonical capability types (one-to-many)
#
# Maps each instrument manifest surface-key to the set of canonical capability
# types that key provides.  For example, "swd" provides both "flash_program"
# and "debug_attach" because SWD is used for both operations.
# ---------------------------------------------------------------------------

SURFACE_KEY_TO_CAPABILITIES: Dict[str, FrozenSet[str]] = {
    "swd":       frozenset({"flash_program", "debug_attach", "reset_control"}),
    "gpio_in":   frozenset({"logic_capture", "gpio_input"}),
    "gpio_out":  frozenset({"gpio_output"}),
    "adc_in":    frozenset({"voltage_measure", "analog_in"}),
    "reset_out": frozenset({"reset_control"}),
    "uart":      frozenset({"uart", "serial_console"}),
}

# ---------------------------------------------------------------------------
# Canonical capability → set of surface keys that provide it (reverse map)
# ---------------------------------------------------------------------------

def _build_reverse() -> Dict[str, FrozenSet[str]]:
    reverse: Dict[str, Set[str]] = {}
    for sk, caps in SURFACE_KEY_TO_CAPABILITIES.items():
        for cap in caps:
            reverse.setdefault(cap, set()).add(sk)
    return {cap: frozenset(keys) for cap, keys in reverse.items()}


CAPABILITY_TO_SURFACE_KEYS: Dict[str, FrozenSet[str]] = _build_reverse()


# ---------------------------------------------------------------------------
# DUT feature → required instrument surface keys (Phase 3: DUT↔Instrument)
#
# Maps DUT features (from board YAML) to the instrument surface key(s) that
# must be present for the instrument to interface with the DUT.
# "required" means the instrument MUST have this surface to be usable.
# "optional" means missing it generates a warning, not a failure.
# ---------------------------------------------------------------------------

#: DUT features that require a specific instrument surface key.
DUT_FEATURE_TO_REQUIRED_SURFACES: Dict[str, FrozenSet[str]] = {
    "programmable_via_swd":  frozenset({"swd"}),
    # programmable_via_jtag uses esptool/IDF directly — no instrument surface needed
    "programmable_via_jtag": frozenset(),
}

#: DUT features where a missing instrument surface generates a warning (not failure).
DUT_FEATURE_TO_OPTIONAL_SURFACES: Dict[str, FrozenSet[str]] = {
    "has_reset_pin": frozenset({"reset_out"}),
    "has_gpio":      frozenset({"gpio_in", "gpio_out"}),
    "has_adc":       frozenset({"adc_in"}),
    "has_uart_console": frozenset({"uart"}),
}

#: All known valid DUT kind values.
VALID_DUT_KINDS: FrozenSet[str] = frozenset({
    "bare_mcu", "soc", "board", "module", "fpga_target", "mixed_system",
})


def capabilities_from_surface_key(surface_key: str) -> FrozenSet[str]:
    """Return canonical capability types provided by a given surface key."""
    return SURFACE_KEY_TO_CAPABILITIES.get(surface_key, frozenset())


def surface_keys_for_capability(capability_type: str) -> FrozenSet[str]:
    """Return surface keys that provide a given canonical capability type."""
    return CAPABILITY_TO_SURFACE_KEYS.get(capability_type, frozenset())


def provided_capabilities_from_surfaces(
    capability_surfaces: Dict[str, str],
) -> FrozenSet[str]:
    """Convert a capability_surfaces dict to a set of canonical capability types.

    Args:
        capability_surfaces: Mapping of surface_key → surface_name as stored
            in instrument manifests (e.g. {"swd": "gdb_remote",
            "gpio_in": "web_api", "reset_out": "web_api"}).

    Returns:
        Frozenset of canonical capability type strings that the instrument
        provides based on the populated surface keys.
    """
    if not isinstance(capability_surfaces, dict):
        return frozenset()
    caps: Set[str] = set()
    for sk, surface in capability_surfaces.items():
        if not str(surface or "").strip():
            continue
        caps |= SURFACE_KEY_TO_CAPABILITIES.get(sk, frozenset())
    return frozenset(caps)
