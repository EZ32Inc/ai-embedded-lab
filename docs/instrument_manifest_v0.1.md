# AEL Instrument Manifest v0.1

This document defines how an **Instrument** describes itself to AEL.

An Instrument is any device that can interact with a DUT, such as:

- SWD/JTAG debugger
- logic analyzer
- UART monitor
- frequency meter
- signal generator
- power switch

The Instrument Manifest allows AEL to:

- discover instruments
- select them by capability
- operate them safely
- automate workflows

---

## Location

A manifest may exist in one of these places:

Local (Golden):

```
assets_golden/instruments/<instrument_id>/manifest.json
```

Local (User):

```
assets_user/instruments/<instrument_id>/manifest.json
```

Network (Instrument-hosted):

```
http://<instrument>/.well-known/ael/manifest.json
```

Golden manifests are part of the AEL platform.

User manifests may be created or modified by AI or users.

---

## Required Fields

A valid v0.1 manifest must include:

```json
{
  "schema": "ael.instrument.manifest.v0.1",
  "id": "instrument_id",
  "kind": "instrument",
  "transports": [...],
  "capabilities": [...]
}
```

---

## Transports

Defines how AEL communicates with the Instrument.

Examples:

```json
{ "type": "serial", "endpoint_hint": "/dev/ttyACM*" }
{ "type": "tcp", "endpoint_hint": "192.168.1.50:9000" }
```

Transport types may include:

- serial
- tcp
- websocket
- hid
- vendor-specific protocols

---

## Capabilities

Defines what the Instrument can do.

Examples:

```json
{ "name": "debug.swd" }
{ "name": "debug.jtag" }
{ "name": "observe.logic", "channels": 8 }
{ "name": "observe.uart" }
{ "name": "measure.freq" }
{ "name": "power.switch" }
```

AEL selects Instruments based on capabilities.

---

## Optional Fields

### Identity

Used for stable detection:

```json
"identity": {
  "usb": { "vid": "...", "pid": "...", "serial": "..." },
  "network": { "mac": "..." }
}
```

---

### Safety

Important for unattended operation:

```json
"safety": {
  "hotplug_allowed": false
}
```

---

### Docs

Provide usage guidance:

```json
"docs": {
  "ai": [{ "path": "docs_ai.md" }],
  "human": [{ "url": "https://example.com" }]
}
```

---

## Ownership

Golden manifests are created by:

- AEL platform
- Instrument vendors

They are not dynamically generated.

User manifests may be created for custom hardware.

---

## Versioning

Future updates will use:

```
schema: ael.instrument.manifest.v0.2
```

---

## Summary

The Instrument Manifest makes Instruments:

- discoverable
- safe
- automatable

It is the foundation for scalable hardware orchestration in AEL.
