# STLinkInstrument — Integration Notes

## Phase

Direct integration (phase 1). Full AEL instrument packaging is deferred.

## Backend source

Fork: https://github.com/EZ32Inc/stlink
Managed as a git submodule at: `instruments/STLinkInstrument/upstream/stlink`

## Build

cmake-based. See `scripts/build.sh`.
Output binaries land in `upstream/stlink/build/bin/`.

All scripts fall back to system-installed binaries if the local build is absent.

## AEL integration path

Current: standalone scripts + thin Python runtime glue (`runtime/stlink_backend.py`).
Not yet wired into the AEL adapter registry or instrument manifest system.

Future packaging will add:
- `configs/instrument_instances/stlink_*.yaml`
- AEL adapter in `ael/adapters/flash_stlink.py`
- Instrument manifest entry

## Flash method

`st-flash write <firmware.bin> 0x08000000`

For SWD targets this is direct — no GDB involved.
For targets requiring connect-under-reset, use `st-flash --connect-under-reset`.

## GDB server

`st-util --port 4242` starts a GDB remote server.
Used when GDB-based flash or runtime inspection is needed.
Compatible with arm-none-eabi-gdb.

## Tested path (direct integration)

- `st-info --probe` — probes connected ST-Link and prints chipid/serial
- `st-flash write` — writes .bin to STM32 flash at 0x08000000
- `st-util` — starts GDB server on port 4242

## USB permissions (Linux)

If st-flash/st-info returns permission denied on USB:
```bash
# Install udev rules from the stlink repo:
sudo cp upstream/stlink/config/udev/rules.d/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```
Then replug the ST-Link.
