# Instruments in AEL

AEL interacts with real hardware through **Instruments**.

An Instrument is any device that can interact with a DUT (Device Under Test), such as:

- debug adapters (SWD / JTAG)
- logic capture devices
- UART monitors
- signal generators
- power switches
- scopes / meters (now or later)

AEL is designed so instruments can be added without changing core orchestration logic.

See also:
- `docs/instrument_model.md` for the repo-level architecture position, including the planned retirement of `probe` as a parallel top-level concept.
- `docs/architecture/cloud_instrument_architecture_v0_1.md` for the network-native/cloud-ready instrument direction.
- `docs/specs/cloud_instrument_profile_v0_1.md` for the bounded cloud-ready instrument profile.

Terminology note:
- preferred current term: `control instrument`
- legacy compatibility term: `probe`
- in current AEL output, debug/JTAG-style hardware may still carry legacy `probe_*` fields for compatibility, but the preferred user-facing wording is `control_instrument*`

---

## Instrument Manifest (v0.1)

Each instrument is described by a machine-readable manifest:

- Local (shipped with AEL):  
  `assets_golden/instruments/<instrument_id>/manifest.json`

- Local (user workspace):  
  `assets_user/instruments/<instrument_id>/manifest.json`

- Network (instrument-hosted):  
  `http://<ip>/.well-known/ael/manifest.json`

The manifest is the contract between AEL (Orchestrator) and the instrument.

It declares:

- identity (USB VID/PID, serial, MAC, etc.)
- transports (USB/serial/TCP, endpoints, discovery hints)
- capabilities (debug, observe, power, etc.)
- safety limits (voltage, current, hotplug)
- docs and examples (human + AI usage notes)

---

## Required Manifest Fields

A v0.1 manifest must include:

- `schema`: must be `"ael.instrument.manifest.v0.1"`
- `id`: stable instrument id (string)
- `kind`: must be `"instrument"`
- `transports`: list (at least one transport)
- `capabilities`: list (at least one capability)

Minimal example:

```json
{
  "schema": "ael.instrument.manifest.v0.1",
  "id": "my_instrument_01",
  "kind": "instrument",
  "transports": [
    { "type": "serial", "endpoint_hint": "/dev/ttyACM*", "protocol": "line-json-v0.1" }
  ],
  "capabilities": [
    { "name": "observe.logic", "version": "v0.1", "channels": 8 }
  ]
}
```

## ESP32 Meter Wi-Fi Control

For Wi-Fi instruments like `esp32s3_dev_c_meter`, AEL can normalize AP discovery and connection from the instrument manifest instead of relying on ad hoc shell commands.

Examples:

```bash
python3 -m ael instruments meter-setup --id esp32s3_dev_c_meter --port /dev/ttyACM0 --ifname wlxf0090d36d617 --ssid-suffix 67A9
python3 -m ael instruments meter-ready --id esp32s3_dev_c_meter --ifname wlxf0090d36d617 --ssid-suffix 67A9
python3 -m ael instruments meter-list --id esp32s3_dev_c_meter --ifname wlxf0090d36d617
python3 -m ael instruments wifi-scan --id esp32s3_dev_c_meter --ifname wlxf0090d36d617
python3 -m ael instruments wifi-connect --id esp32s3_dev_c_meter --ifname wlxf0090d36d617 --ssid-suffix 67A9
python3 -m ael instruments meter-reachability --id esp32s3_dev_c_meter
python3 -m ael instruments meter-ping --id esp32s3_dev_c_meter
```

Behavior:

- `meter-setup` performs `flash -> wait for AP -> connect`
- `meter-ready` performs `scan -> connect -> ping`
- `meter-list` reports all visible `ESP32_GPIO_METER_XXXX` candidates in a canonical agent-facing structure
- `wifi-scan` filters visible SSIDs by the manifest `wifi.ap_ssid_prefix`
- `wifi-connect` uses the manifest password automatically
- `meter-reachability` ICMP-pings the meter IP before a run
- `meter-ping` verifies the instrument responds on the manifest TCP endpoint
- if exactly one matching SSID is visible, `wifi-connect` may select it directly
- if multiple matching SSIDs are visible, provide `--ssid` or `--ssid-suffix`

Canonical `meter-list` fields:

- `available_meters`: list of `{ssid, suffix, signal, in_use}`
- `meter_count`
- `selection_required`
- `recommended_action`
