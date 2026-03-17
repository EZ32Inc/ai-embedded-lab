# AEL Instrument Protocol v0.1

## Design Goals

AEL Instrument Protocol (AIP) v0.1 is a minimal, AI-first instrument contract.

- AI-first: endpoints and payloads are predictable JSON with stable keys.
- Minimal verbs: few endpoints, clear request/response semantics.
- Evidence-friendly: each operation returns machine-parseable summary and optional raw payload.
- Transport-flexible: HTTP baseline, optional streaming for high-rate data.
- Local-first: no cloud dependency required.

## Discovery Methods

AIP supports multiple discovery paths. Implementations may support one or more.

- mDNS/SSDP (optional): advertise instrument identity and service endpoint.
- WiFi scan patterns: SSID naming convention can indicate instrument type/id.
- Static IP/manual add: explicit host/port entry for deterministic lab setups.

## Mandatory Endpoints

### `GET /instrument`

Returns identity + capabilities + transports + protocol version.

Minimum fields:

- `instrument_id`
- `protocol_version`
- `model`
- `firmware_version`
- `capabilities`
- `transports`
- `timestamp`

### `GET /capabilities`

Returns capability list and schemas. May be embedded in `/instrument`.

### `POST /action`

Runs a control or measurement action.

Request:

- `capability_id`
- `inputs`
- `request_id` (optional but recommended)

Response:

- `ok`
- `status` (`PASS|FAIL|SKIP|HUMAN_ACTION_REQUIRED`)
- `summary`
- `outputs`
- `evidence`
- `instrument_id`
- `timestamp`

### `POST /capture`

Starts a capture and returns `capture_id`.

### `GET /data/<capture_id>`

Fetches capture results and summary/evidence payload.

## Optional Endpoints

- `WS /stream`: low-latency stream for high-rate telemetry or waveform chunks.
- `GET /health`: readiness and liveness checks.
- `GET /schema`: machine-readable JSON schema for protocol/capabilities.

## Capability Schema Conventions

Each capability should include:

- `capability_id`: stable identifier (example: `measure.voltage`).
- `inputs_schema`: JSON schema-like shape for accepted inputs.
- `outputs_schema`: JSON schema-like shape for outputs.
- `units`: explicit measurement units.
- `ranges`: valid min/max ranges.
- `tolerances`: allowed uncertainty/error bounds.

## Evidence Requirements

Every action/capture response must include:

- machine-parseable summary fields (`ok`, `status`, `summary`)
- `instrument_id`
- `timestamp` (ISO-8601)
- optional raw payload references

Recommended evidence object:

- `metrics`: normalized values
- `raw`: optional raw samples/chunks (or reference path/id)
- `logs`: optional debug lines

## Versioning Rules

- Protocol version uses semantic-style progression.
- Backward-compatible additions must not break existing required fields.
- Breaking changes require a new major protocol version.
- Instruments should expose supported version(s) in `/instrument`.

## Security Model (v0.1)

- Local-network default deployment.
- Optional token auth (header or query) for controlled labs.
- No mandatory cloud dependency.
- TLS optional based on deployment constraints.

## Examples

### ESP32JTAG profile (example capabilities)

- `gpio_capture`
- `uart_log`
- `jtag_control`

### ESP32Meter profile (example capabilities)

- `measure.digital`
- `measure.voltage`

Both profiles should conform to the same endpoint contract and return structured evidence.
