"""
ESP32 post-flash runtime verification profiles.

A profile defines the set of regex patterns that MUST appear in the UART boot
log (required), the patterns that must NOT appear (forbidden), and optionally
a heartbeat pattern to confirm the firmware is still alive after boot.

Pattern matching is case-insensitive (re.IGNORECASE).

Profiles
--------
instrument_ready
    For ESP32 instrument firmware that brings up WiFi and starts a server
    (e.g. S3JTAG / ESP32JTAG boards).  All four required groups must match.

boot_only
    Minimal gate — confirms that ESP-IDF app_main started.  No WiFi required.
    Useful as a sanity check for DUT firmware that does not use networking.

custom
    No built-in required patterns.  The caller supplies custom_patterns via the
    post_flash_verify adapter config.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class VerifyProfile:
    name: str
    # All patterns must match at least once (AND semantics, case-insensitive).
    required: List[str]
    # Any match in this list → firmware is not in expected state (OR semantics).
    forbidden: List[str]
    # The single pattern whose first appearance marks "firmware is ready".
    # Used to set the firmware_ready_seen flag in the result.
    firmware_ready_anchor: str
    # Optional: a pattern expected to repeat after the board is ready.
    # When set, post_flash_verify waits an extra heartbeat_confirm_s window
    # and checks for at least one occurrence after the ready anchor.
    heartbeat_pattern: Optional[str] = None


# ---------------------------------------------------------------------------
# instrument_ready  — for ESP32 instrument firmware (S3JTAG / ESP32JTAG)
# ---------------------------------------------------------------------------
# Matches the log sequence produced by AEL-standard instrument firmware:
#
#   I (nnn) ael: wifi connected ssid=AEL
#   I (nnn) ael: ip=192.168.2.251
#   I (nnn) ael: server ready port=4242
#   I (nnn) ael: AEL S3JTAGboard is OK
#   I (nnn) ael: heartbeat
#
# All four required groups must appear.  Forbidden patterns cover all
# ESP-IDF fatal conditions that indicate the board is not usable.

INSTRUMENT_READY = VerifyProfile(
    name="instrument_ready",
    required=[
        # WiFi connected (STA link up)
        r"wifi.*connected|sta.*connected|WiFi.*connected",
        # IP address assigned (DHCP or static)
        r"ip=\d+\.\d+\.\d+\.\d+|got ip:|IP\s*[=:]\s*\d+",
        # Application server / JTAG server is ready
        r"server.*ready|Listening.*port|gdb.*ready|jtag.*ready|ws.*ready|TCP.*port",
        # Board-level OK signal (firmware's final "I am healthy" line)
        r"AEL.*board.*OK|board.*ready|instrument.*ready|S3JTAG.*OK|FPGA.*OK|AEL.*OK",
    ],
    forbidden=[
        r"Guru Meditation",
        r"\bpanic\b",
        r"assert failed",
        r"abort\(\)",
        r"\bBrownout\b",
        r"\bTWDT\b",
        r"Task watchdog",
        r"LoadProhibited|StoreProhibited|InstrFetchProhibited|IllegalInstruction",
        r"Rebooting\.\.\.",
    ],
    firmware_ready_anchor=r"AEL.*board.*OK|board.*ready|instrument.*ready|S3JTAG.*OK|FPGA.*OK|AEL.*OK",
    heartbeat_pattern=r"heartbeat|Free internal|free mem",
)


# ---------------------------------------------------------------------------
# boot_only  — minimal: confirm IDF app_main started, no WiFi required
# ---------------------------------------------------------------------------
BOOT_ONLY = VerifyProfile(
    name="boot_only",
    required=[
        # At least one ESP-IDF log line from the application layer
        r"I \(\d+\)|cpu_start:|app_main|AEL|esp_idf",
    ],
    forbidden=[
        r"Guru Meditation",
        r"\bpanic\b",
        r"assert failed",
        r"abort\(\)",
        r"\bTWDT\b",
        r"Task watchdog",
        r"Rebooting\.\.\.",
    ],
    firmware_ready_anchor=r"app_main|AEL|cpu_start:",
    heartbeat_pattern=None,
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
PROFILES: Dict[str, VerifyProfile] = {
    "instrument_ready": INSTRUMENT_READY,
    "boot_only": BOOT_ONLY,
}


def get_profile(name: str) -> Optional[VerifyProfile]:
    """Return the named profile, or None if not found."""
    return PROFILES.get(str(name or "").strip().lower())
