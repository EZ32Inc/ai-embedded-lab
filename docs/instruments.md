# Instruments In AEL

AEL interacts with real hardware through instruments.

An instrument is any device or service that can act on, observe, or help verify
a DUT. Examples include:

- SWD/JTAG debug adapters
- UART bridges and monitors
- logic capture devices
- signal generators
- power switches
- meters and scopes
- network-facing instrument daemons

The preferred current term is **control instrument**. The older term **probe**
still appears in code and output for compatibility, especially around debug and
flash paths.

## Current CLI Entry

Use:

```bash
python3 -m ael instruments --help
```

Current subcommands include:

- `list`
- `describe`
- `show`
- `find`
- `doctor`
- `usb-probe`
- `detect-mcu`
- ESP32 meter Wi-Fi helpers such as `wifi-scan`, `wifi-connect`, and
  `meter-ready`

Verify exact options with the subcommand help before running live bench actions.

## Current Model

The instrument layer is designed around:

- stable identity
- declared capabilities
- explicit transports
- action/result contracts
- clear fallback and degraded-instrument reporting

Start with:

- [instrument_model_v1.md](./instrument_model_v1.md)
- [control_instrument_compatibility.md](./control_instrument_compatibility.md)
- [degraded_instrument_policy.md](./degraded_instrument_policy.md)
- [instruments/usb_uart_bridge_daemon_v0_1.md](./instruments/usb_uart_bridge_daemon_v0_1.md)

Older architecture and migration notes may still be useful as history, but
current behavior should be checked against code, configs, and CLI output.

## Manifest Direction

Instrument manifests describe:

- identity
- transports
- capabilities
- safety limits
- documentation and examples

Example shape:

```json
{
  "schema": "ael.instrument.manifest.v0.1",
  "id": "example_instrument",
  "kind": "instrument",
  "transports": [
    {"type": "serial", "endpoint_hint": "<serial-port>", "protocol": "line-json-v0.1"}
  ],
  "capabilities": [
    {"name": "uart.observe", "version": "v0.1"}
  ]
}
```

Keep public examples generic. Do not publish real private IPs, Wi-Fi details,
USB serial numbers, or bench-local paths.

## ESP32 Meter Notes

ESP32 meter helpers can normalize AP discovery, connection, reachability, and
meter readiness from instrument configuration. Public documentation should show
generic command shapes:

```bash
python3 -m ael instruments wifi-scan --id <instrument-id> --ifname <wifi-interface>
python3 -m ael instruments wifi-connect --id <instrument-id> --ifname <wifi-interface> --ssid-suffix <suffix>
python3 -m ael instruments meter-ready --id <instrument-id> --ifname <wifi-interface> --ssid-suffix <suffix>
python3 -m ael instruments meter-reachability --id <instrument-id>
python3 -m ael instruments meter-ping --id <instrument-id>
```

Do not commit real SSIDs, passwords, interface MAC-derived names, or private
meter IPs in public docs.

## Public-Repo Safety

Instrument docs are especially likely to contain local bench details. Before
committing:

- replace private IPs with `<probe-ip>` or `<instrument-ip>`
- replace serial devices with `<serial-port>`
- replace local interface names with `<wifi-interface>`
- replace real SSID suffixes with `<suffix>`
- summarize raw logs instead of linking transcripts

See [SECURITY_AND_PUBLIC_REPO.md](./SECURITY_AND_PUBLIC_REPO.md).
