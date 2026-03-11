# USB-UART Bridge Daemon v0.1

## What this is

This is a first bounded Linux/Ubuntu-only daemon for exposing a USB-to-UART
bridge as a network-facing AEL instrument.

The practical model is:

- Ubuntu/Linux host
- attached USB-to-UART hardware
- small daemon process
- network API for basic serial access

This is intentionally a first working bridge, not a broad final framework.

## Why USB serial number is required

This daemon uses the USB serial number as the stable device identity.

It does not use:

- `/dev/ttyUSBx`
- `/dev/ttyACMx`

as identity, because those can change across boots and reattachment.

Out of scope for this version:

- devices with no serial number
- devices with an empty serial number
- devices where the current scan contains duplicate serial numbers

Those are rejected rather than handled heuristically.

## Discovery and selection

Discovery uses:

- `pyserial`
- `serial.tools.list_ports`
- `/dev/serial/by-id` when available

`list` shows structured metadata:

- current device path
- VID
- PID
- serial number
- manufacturer
- product
- `/dev/serial/by-id` path if present

`select` stores only the USB serial number as the stable identity.

At runtime, the daemon:

1. scans current USB serial devices
2. finds the configured serial number
3. resolves the current tty path
4. opens that path using configured serial settings

## Config shape

Example config:

- [usb_uart_bridge.example.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/instruments/usb_uart_bridge.example.yaml)

Main fields:

- `selected_serial_number`
- `listen.host`
- `listen.port`
- `serial.baudrate`
- `serial.bytesize`
- `serial.parity`
- `serial.stopbits`
- `serial.timeout`

## CLI

Module:

- [usb_uart_bridge_cli.py](/nvme1t/work/codex/ai-embedded-lab/ael/usb_uart_bridge_cli.py)

Commands:

- `list`
- `select --serial <USB_SERIAL_NUMBER>`
- `show`
- `doctor`
- `serve`

Example usage:

```bash
python3 -m ael.usb_uart_bridge_cli --config configs/instruments/usb_uart_bridge.yaml list --format text
python3 -m ael.usb_uart_bridge_cli --config configs/instruments/usb_uart_bridge.yaml select --serial ABC123456
python3 -m ael.usb_uart_bridge_cli --config configs/instruments/usb_uart_bridge.yaml show --format text
python3 -m ael.usb_uart_bridge_cli --config configs/instruments/usb_uart_bridge.yaml doctor --format text
python3 -m ael.usb_uart_bridge_cli --config configs/instruments/usb_uart_bridge.yaml serve
```

## Network API

Module:

- [usb_uart_bridge_daemon.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/usb_uart_bridge_daemon.py)

Current API is JSON over HTTP using Python stdlib `http.server`.

GET:

- `/status`
- `/list_devices`
- `/show_selected_device`
- `/doctor`

POST:

- `/open`
- `/close`
- `/write`
- `/read`

Current write/read behavior:

- `write` accepts UTF-8 `text` or base64 payload
- `read` returns base64 and UTF-8 text when decodable

## How it fits the AEL instrument model

This daemon is a host-provided instrument endpoint.

The identity rule matches AEL’s current direction:

- stable identity first
- runtime endpoint resolution second

For this first version, it is intentionally not integrated into every existing
AEL instrument surface.

It is a clean standalone bridge with a clear later integration path.

## Doctor behavior

`doctor` reports:

- configured serial number
- whether the device is present
- current resolved tty path
- whether it can be opened
- any current mismatch/error

## Out of scope

Not included in v0.1:

- Windows/macOS support
- heuristic matching without serial number
- support for duplicate serial numbers
- full integration into `ael instruments ...`
- broad multi-client concurrency policy
- authentication or production-grade service hardening

## Likely next AEL integration step

The next bounded step should be:

- add a manifest/instrument entry for this daemon type
- then let selected AEL flows treat it as a network instrument endpoint

That should happen after the basic daemon and doctor behavior are proven useful.
