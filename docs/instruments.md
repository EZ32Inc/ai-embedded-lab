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
