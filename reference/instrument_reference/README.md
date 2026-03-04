# Reference Instrument Skeleton

This scaffold defines a minimal reference layout for building an AEL-compatible instrument.

## Purpose

- Provide a copyable structure for vendors and users.
- Keep protocol and capability definitions explicit.
- Enable contract-first development before firmware implementation.

## File Layout

- `contract.json`: example `GET /instrument` response.
- `capabilities/`: capability contracts and schema hints.
- `transport/`: endpoint and transport implementation notes.
- `security/`: token and local-network security notes.

## Endpoints to Implement

- `GET /instrument`
- `GET /capabilities` (or embed in `/instrument`)
- `POST /action`
- `POST /capture`
- `GET /data/<capture_id>`
- Optional: `WS /stream`, `GET /health`, `GET /schema`

## Recommended Libraries

- HTTP server: lightweight embedded HTTP stack with JSON support
- JSON parser/serializer: deterministic, bounded memory use
- Optional WebSocket library for high-rate streams
- Optional mDNS/SSDP helper for discovery

## Minimal Test Checklist

- `/instrument` returns stable `instrument_id`, `version`, `capabilities`.
- Every capability validates inputs and returns machine-parseable output.
- Action/capture responses include timestamp and evidence fields.
- Invalid input returns clear error summary.
- All required endpoints respond under expected timeout budget.
