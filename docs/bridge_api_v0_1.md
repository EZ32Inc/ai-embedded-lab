# Bridge API v0.1

## Purpose

The bridge exposes a small HTTP API so a remote chat UI can submit tasks into AEL.

Flow:

Chat UI -> Bridge API -> `queue/inbox` -> `ael.agent` -> result/artifacts

## Run

```bash
python3 -m ael bridge --host 127.0.0.1 --port 8844
```

Environment defaults:

- `AEL_BRIDGE_HOST` (default `127.0.0.1`)
- `AEL_BRIDGE_PORT` (default `8844`)
- `AEL_QUEUE_ROOT` (default `queue`)
- `AEL_BRIDGE_TOKEN` (optional auth token)

## Token auth

If `AEL_BRIDGE_TOKEN` is set, send:

```http
X-AEL-Token: <token>
```

Keep the token private. Do not expose the bridge to untrusted networks without authentication.

## Endpoints

- `GET /health`
- `POST /v1/tasks`
- `GET /v1/tasks/<task_id>`
- `GET /v1/tasks/<task_id>/result`
- `GET /v1/tasks/<task_id>/artifacts/<relpath>`
- `GET /v1/tasks/<task_id>/stream` (SSE best effort)

## Submit task example

```bash
curl -X POST http://127.0.0.1:8844/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title":"bridge smoke",
    "kind":"noop",
    "payload":{},
    "priority":0
  }'
```

Kinds:

- `noop`: creates an internal noop runplan
- `runplan`: payload must include `runplan` object
- `codex`: payload includes prompt for optional codex driver

## Poll task status

```bash
curl http://127.0.0.1:8844/v1/tasks/<task_id>
curl http://127.0.0.1:8844/v1/tasks/<task_id>/result
```

## LAN and tunnel usage

- LAN: bind with `--host 0.0.0.0` and restrict access at network level.
- Tunnel: user-managed option. Only tunnel behind token auth.

Security guidance:

- Use a long random token.
- Prefer local-only (`127.0.0.1`) unless remote access is required.
- Rotate token if shared accidentally.
