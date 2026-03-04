# docs/night_tasks_agent_v0_4.md
# AEL Agent v0.4 — “ChatGPT ↔ Codex” Bridge (Local API + Queue + Optional Codex Driver)
#
# Goal
# Make AEL usable from a *remote chat UI* (ChatGPT / phone) by exposing a small, stable HTTP API.
# The API submits tasks into the existing AEL queue, streams logs/results back, and (optionally) can invoke Codex
# as a subprocess “worker” for code-change tasks.
#
# This is NOT about building a full OpenAI integration inside AEL.
# It’s about creating a clean local bridge so any chat UI can “talk to AEL”, and AEL can “drive Codex” when available.
#
# MUST KEEP:
# - ael_guard rules and boundary contract: Core stays clean.
# - No hard-coded board/tool strings in Core.
# - Runner remains the execution engine for runplan steps.
#
# Definitions
# - Bridge API: lightweight HTTP server on the AEL host machine.
# - Task: JSON payload submitted to AEL (write to queue/inbox).
# - Agent: existing queue runner that picks tasks and executes.
# - Codex Driver (optional): a subprocess wrapper that can run "codex" CLI with a prompt, capture output, and attach to artifacts.
#
# Deliverables (by end of night)
# 1) AEL Bridge HTTP API server (submit task, status, stream logs, fetch artifacts).
# 2) Task schema (minimal) and stable on-disk layout for bridge tasks.
# 3) Optional Codex driver abstraction (pluggable, disabled by default).
# 4) Smoke test that exercises the bridge end-to-end with a noop plan and validates outputs.
# 5) Docs: how to use from a phone/ChatGPT (expose via LAN / tunnel), security token, examples.
#
# =============================================================================
# Task 0 — Read & confirm repo context
# =============================================================================
# Read/skim these before coding:
# - ael/agent.py, ael/queue.py, ael/reporting.py
# - ael/runner.py, ael/adapter_registry.py, orchestrator.py (runner integration)
# - docs/runplan_v0_1.md
#
# No design surprises: Bridge just writes tasks into queue/inbox and agent executes.

# =============================================================================
# Task 1 — Create a minimal Bridge API server (stdlib only)
# =============================================================================
# Add: ael/bridge_server.py
#
# Constraints:
# - Prefer stdlib only (http.server + threading) to avoid FastAPI dependency.
# - JSON over HTTP.
# - Token auth: require header "X-AEL-Token: <token>" if AEL_BRIDGE_TOKEN is set.
# - Bind address configurable:
#   - default host=127.0.0.1, port=8844
#   - env: AEL_BRIDGE_HOST, AEL_BRIDGE_PORT
# - Must NOT import board/tool adapters; Bridge is Core-adjacent but should remain generic.
#
# Endpoints (v0.1):
# 1) GET /health
#    -> { "ok": true, "version": "bridge/0.1" }
#
# 2) POST /v1/tasks
#    Request JSON:
#      {
#        "title": "string",
#        "kind": "runplan" | "codex" | "noop",
#        "payload": { ... },     # kind-specific
#        "priority": 0           # optional, default 0
#      }
#    Response:
#      { "ok": true, "task_id": "YYYYMMDD_HHMMSS_<rand>", "path": "queue/inbox/<taskfile>.json" }
#
#    Behavior:
#    - Validate required fields.
#    - Write a single JSON file into queue/inbox atomically.
#    - File naming: queue/inbox/<task_id>__<slug>.json
#
# 3) GET /v1/tasks/<task_id>
#    -> returns current task state by checking:
#       queue/inbox, queue/running, queue/done, queue/failed
#    and if running/done/failed exists, include summary fields.
#
# 4) GET /v1/tasks/<task_id>/result
#    -> if done/failed, return the final state JSON the agent wrote (or 404 if not ready)
#
# 5) GET /v1/tasks/<task_id>/artifacts/<relpath>
#    -> serve raw file bytes from the task run_dir artifacts (safe path join; forbid ..)
#
# 6) GET /v1/tasks/<task_id>/stream
#    -> Server-Sent Events (SSE) “best effort”
#       - If task is running, tail a known log file (see Task 2) and stream lines
#       - If not available, send periodic heartbeat events
#
# Notes:
# - SSE is optional but very useful. Implement simple tailer:
#   - open file, seek to end, poll every 0.2s, emit "data: <line>\n\n"
# - If SSE is too annoying, skip it and provide /result + /artifacts and keep it simple.

# =============================================================================
# Task 2 — Define Bridge task schema + mapping to Agent
# =============================================================================
# Add: ael/bridge_task.py
#
# Purpose:
# - Normalize the on-disk JSON format Bridge writes so Agent can consume consistently.
# - Keep it minimal and stable.
#
# Required fields:
# {
#   "task_id": "...",
#   "title": "...",
#   "kind": "runplan" | "codex" | "noop",
#   "created_at": "iso8601",
#   "payload": { ... },
#   "meta": { "priority": 0, "source": "bridge" }
# }
#
# Mapping rules (Agent side):
# - kind=noop
#   -> create a tiny runplan with single step type "check.noop" and execute via runner
#
# - kind=runplan
#   payload = { "runplan": <dict> , "run_dir": <optional path> }
#   -> agent executes runner.run_plan(runplan, run_dir, registry)
#
# - kind=codex (optional, if you implement Task 3)
#   payload = {
#     "repo_root": ".",
#     "prompt": "....",
#     "files_hint": ["docs/night_tasks_x.md"],
#     "mode": "apply" | "plan"     # optional
#   }
#   -> agent runs Codex driver, captures transcript into artifacts, then (optionally) runs validations
#
# Logging contract:
# - For any task, agent MUST write a running log:
#   - <task_run_dir>/logs/task.log
# - Bridge SSE should stream from that file if present.

# =============================================================================
# Task 3 — Optional: Codex driver abstraction (disabled by default)
# =============================================================================
# If Codex CLI is available on the host, AEL can “ask Codex” to do work.
# This is optional; implement cleanly so it can be turned off.
#
# Add: ael/codex_driver.py
#
# Interface:
# - class CodexDriver:
#     def available(self) -> bool
#     def run(self, *, repo_root: str, prompt: str, timeout_s: int, log_path: str) -> dict
#
# Configuration:
# - env AEL_CODEX_CMD (default "codex")
# - env AEL_CODEX_ENABLED (default "0")
#
# Behavior:
# - If not enabled, return {ok:false, error_summary:"codex disabled"}.
# - If enabled but command missing, return {ok:false, error_summary:"codex cmd not found"}.
# - Use subprocess.Popen, redirect stdout/stderr to log_path.
# - Treat exit code 0 as ok.
#
# IMPORTANT:
# We do not assume any special Codex CLI flags. Use the most generic pattern:
# - Run the command and feed prompt via stdin.
# - Example:
#   p = Popen([cmd], cwd=repo_root, stdin=PIPE, stdout=..., stderr=STDOUT, text=True)
#   p.communicate(prompt, timeout=timeout_s)
#
# Save a transcript artifact:
# - <run_dir>/artifacts/codex_transcript.log
# - <run_dir>/artifacts/codex_result.json
#
# Do NOT block the rest of AEL if Codex is unavailable.

# =============================================================================
# Task 4 — Extend Agent to accept Bridge tasks
# =============================================================================
# Update: ael/agent.py
#
# Add:
# - When reading a task file, detect if it matches Bridge schema (kind/title/payload).
# - Create a run_dir for the task:
#   - queue/running/<task_id>/
#     - logs/task.log
#     - artifacts/
# - Write state transitions:
#   - queue/running/<task_id>.json
#   - queue/done/<task_id>.json or queue/failed/<task_id>.json
#
# Execution:
# - kind=noop: run_plan() with check.noop
# - kind=runplan: run_plan(payload["runplan"], ...)
# - kind=codex: if enabled, codex_driver.run(); optionally run a small validation set after.
#
# Important:
# - Keep all prints/logging duplicated into logs/task.log (tee).
# - Ensure exceptions are caught and written as failed state with error_summary.

# =============================================================================
# Task 5 — CLI entrypoint for the Bridge server
# =============================================================================
# Update: ael/__main__.py
#
# Add a new subcommand:
#   python3 -m ael bridge --host 0.0.0.0 --port 8844
#
# This should:
# - start Bridge server
# - print a clear line:
#   "AEL Bridge listening on http://HOST:PORT (token auth: on/off)"
#
# Ensure this remains Core-clean:
# - importing ael.bridge_server is fine (generic).
# - no board/tool strings.

# =============================================================================
# Task 6 — Smoke test: bridge end-to-end
# =============================================================================
# Add: tools/bridge_smoke.py
#
# What it does:
# 1) Start bridge server in a subprocess (python -m ael bridge ...), bind 127.0.0.1:PORT
# 2) POST /v1/tasks with kind=noop, title="bridge_smoke"
# 3) Poll /v1/tasks/<id> until done (timeout 10s)
# 4) GET /v1/tasks/<id>/result and assert ok==true
# 5) Stop the server cleanly
#
# Use urllib.request (stdlib) to avoid deps.

# =============================================================================
# Task 7 — Docs: how to use “ChatGPT ↔ AEL ↔ Codex” safely
# =============================================================================
# Add docs:
# - docs/bridge_api_v0_1.md
#   Include:
#   - running the bridge
#   - token usage
#   - LAN usage (same WiFi)
#   - optional tunneling (user choice) and security warnings
#   - example curl commands for submit/poll/result
#
# - docs/night_tasks_agent_v0_4_notes.md (short)
#   - what shipped
#   - known limitations
#   - next ideas (webhook to Discord/Telegram later)

# =============================================================================
# Gates (MANDATORY) — run all of them and show output
# =============================================================================
# After ALL tasks:
#
# 1) python3 -m py_compile ael/bridge_server.py ael/bridge_task.py ael/codex_driver.py ael/agent.py tools/bridge_smoke.py
#    (Skip codex_driver.py if you decide not to implement Task 3, but then explain.)
#
# 2) python3 tools/ael_guard.py --fast
#
# 3) python3 tools/agent_smoke.py
#
# 4) python3 tools/bridge_smoke.py
#
# Also:
# - git status --short
# - rg -n "esp32|stm32|rp2040|pico|openocd|esptool|gdb|stlink|wchlink|bmda" ael/bridge_server.py ael/bridge_task.py ael/codex_driver.py
#
# =============================================================================
# Commit strategy
# =============================================================================
# Commit in 3 chunks:
# 1) feat(bridge): add bridge server + task schema
# 2) feat(agent): process bridge tasks + logs/run_dir mapping
# 3) test(docs): add bridge_smoke + docs
#
# Each commit must pass:
# - python3 -m py_compile ...
# - python3 tools/ael_guard.py --fast
#
# =============================================================================
# Acceptance criteria
# =============================================================================
# - You can run:
#     python3 -m ael bridge
#   in one terminal,
#   then in another:
#     curl -X POST http://127.0.0.1:8844/v1/tasks -d '{"title":"t","kind":"noop","payload":{}}' ...
#   and see it complete via agent.
#
# - bridge_smoke passes on a clean repo without manual steps.
#
# - Codex driver is optional but if implemented, it is fully gated by env AEL_CODEX_ENABLED=1.

