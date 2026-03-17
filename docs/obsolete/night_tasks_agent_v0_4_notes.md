# AEL Agent v0.4 Notes

## Shipped

- Added bridge HTTP server: `ael/bridge_server.py`
- Added bridge task schema helpers: `ael/bridge_task.py`
- Extended agent to process bridge tasks (`noop`, `runplan`, `codex`)
- Added optional codex driver: `ael/codex_driver.py` (env gated)
- Added CLI entrypoint: `python3 -m ael bridge`
- Added bridge end-to-end smoke test: `tools/bridge_smoke.py`
- Added bridge usage doc: `docs/bridge_api_v0_1.md`

## Known limitations

- SSE stream is best effort and polls log file changes.
- Task lookup scans queue files by `task_id`.
- Codex execution is optional and disabled unless `AEL_CODEX_ENABLED=1`.

## Next ideas

- Add task cancellation endpoint.
- Add pagination for task history queries.
- Add webhook notifier integration for done/failed events.
