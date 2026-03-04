# HTTP Server Notes

Implement a compact HTTP server with JSON request/response support.

## Required routes

- `GET /instrument`
- `GET /capabilities`
- `POST /action`
- `POST /capture`
- `GET /data/<capture_id>`

## Behavior guidance

- Validate request schema and return clear `error_summary` for invalid input.
- Include `instrument_id` and `timestamp_utc` in successful responses.
- Keep payloads bounded and deterministic where possible.
- Return machine-parseable evidence payloads suitable for `artifacts/*.json`.
