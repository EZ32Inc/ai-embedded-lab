# STLinkInstrument

AEL direct-integration backend for ST-Link.

**Current phase:** direct integration — build, probe, flash, GDB server.
Full AEL instrument packaging is deferred to a later phase.

---

## Backend source

This instrument uses the EZ32Inc fork of the open-source stlink project:

- Fork: https://github.com/EZ32Inc/stlink
- Location in this repo: `upstream/stlink/` (git submodule)

### Submodule setup

If you cloned the AEL repo without submodules:

```bash
git submodule update --init --recursive
```

For a fresh clone:

```bash
git clone --recurse-submodules <AEL repo URL>
```

---

## Directory structure

```
STLinkInstrument/
├── README.md
├── upstream/
│   └── stlink/          # git submodule — EZ32Inc/stlink fork
├── scripts/
│   ├── build.sh         # build st-flash, st-info, st-util from source
│   ├── probe.sh         # probe connected ST-Link + target
│   ├── flash.sh         # flash a .bin to STM32
│   └── gdb_server.sh    # start st-util GDB server
├── runtime/
│   └── stlink_backend.py  # thin Python glue for probe/flash/gdb_server
├── doctor/
│   └── doctor.sh        # check setup health
└── notes/
    ├── integration.md   # integration notes and AEL path
    └── known_issues.md  # known issues and fixes
```

---

## Build

Build st-flash, st-info, and st-util from the fork source:

```bash
instruments/STLinkInstrument/scripts/build.sh
```

Binaries land in `upstream/stlink/build/bin/`.
All scripts fall back to system-installed binaries if the local build is absent.

**Dependencies:** cmake, libusb-1.0-dev, build-essential (on Debian/Ubuntu).

```bash
sudo apt install cmake libusb-1.0-0-dev build-essential
```

---

## Usage

### Probe

Detect connected ST-Link device and print target info:

```bash
instruments/STLinkInstrument/scripts/probe.sh
```

### Flash

Flash a firmware binary to the target:

```bash
instruments/STLinkInstrument/scripts/flash.sh firmware.bin
instruments/STLinkInstrument/scripts/flash.sh firmware.bin --addr 0x08000000 --reset
```

### GDB server

Start a GDB remote server on port 4242:

```bash
instruments/STLinkInstrument/scripts/gdb_server.sh
instruments/STLinkInstrument/scripts/gdb_server.sh --port 4242
```

Connect with GDB:

```bash
arm-none-eabi-gdb firmware.elf
(gdb) target extended-remote :4242
```

---

## Doctor

Check setup health (submodule, build artifacts, USB device, probe):

```bash
instruments/STLinkInstrument/doctor/doctor.sh
```

---

## Python runtime

```python
import sys
sys.path.insert(0, 'instruments/STLinkInstrument/runtime')
import stlink_backend

# Check if built
print(stlink_backend.is_built())

# Probe
result = stlink_backend.probe()
print(result)

# Flash
result = stlink_backend.flash('firmware.bin', addr='0x08000000', reset=True)
print(result)

# Tool versions
print(stlink_backend.tool_versions())
```

---

## USB permissions (Linux)

If you get permission denied errors:

```bash
sudo cp upstream/stlink/config/udev/rules.d/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Replug the ST-Link after applying rules.

---

## What comes next (future packaging)

- AEL adapter: `ael/adapters/flash_stlink.py`
- Instrument instance configs: `configs/instrument_instances/stlink_*.yaml`
- Integration with `ael doctor` command
- AEL instrument manifest entry
