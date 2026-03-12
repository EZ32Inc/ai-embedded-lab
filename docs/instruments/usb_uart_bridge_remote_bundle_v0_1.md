# USB-UART Bridge Remote Bundle v0.1

This note defines the minimum remote-host package shape for USB-to-UART
verification path Phase 2b.

## Purpose

The remote host should act only as an instrument node/service for the
`usb_uart_bridge_daemon`.

It should not run a full AEL orchestrator or worker.

## Minimum bundle contents

- `ael/usb_uart_bridge_cli.py`
- `ael/instruments/usb_uart_bridge_daemon.py`
- package `__init__.py` files
- `configs/instruments/usb_uart_bridge.example.yaml`
- short usage README
- `requirements.txt`

## Minimum runtime dependencies

- Python 3
- `pyserial`
- `PyYAML`

## Expected remote-host flow

1. unpack the bundle
2. copy the example config to `usb_uart_bridge.yaml`
3. select the attached USB-UART device
4. start the daemon:

```bash
python3 -m ael.usb_uart_bridge_cli --config configs/instruments/usb_uart_bridge.yaml serve --host 0.0.0.0 --port 8767
```

## Build helper

Use:

```bash
python3 tools/build_usb_uart_bridge_bundle.py
```

The zip bundle will be created at:

- `artifacts/usb_uart_bridge_bundle/usb_uart_bridge_bundle_v0_1.zip`

## Scope boundary

This bundle is intentionally minimal.

It is not:

- a full AEL install
- a second orchestrator
- cloud/session infrastructure
- a general remote worker package
