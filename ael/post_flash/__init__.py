"""
ael.post_flash
==============
Post-flash runtime verification for ESP32 boards connected via USB-UART bridge.

Core principle: flash success ≠ runtime ready.

After idf.py (or esptool) reports a successful flash, the firmware image is on
the chip — but the chip has not necessarily booted cleanly, connected to WiFi,
or started its application services.  This package provides the tooling to
confirm that the board has actually reached its expected operational state via
the UART serial log before AEL proceeds to network checks or functional tests.

Public surface
--------------
    from ael.post_flash.profiles import get_profile, INSTRUMENT_READY, BOOT_ONLY
    from ael.adapters.post_flash_verify import run as post_flash_verify
"""
from __future__ import annotations
