#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
QUEUE_ROOT="/tmp/ael_agent_demo_queue"
RUN_DIR="/tmp/ael_agent_demo_run"
GATES_JSON="/tmp/ael_agent_demo_gates.json"
REPORT_ROOT="/tmp/ael_agent_demo_reports"
TASK_ID="agent-demo"
TASK_NAME="2099-01-01_00-00-00_${TASK_ID}.json"
TASK_PATH="${QUEUE_ROOT}/inbox/${TASK_NAME}"
TODAY="$(date +%F)"
BRANCH_NAME="agent/${TODAY}/task-0001-agent-demo"

rm -rf "$QUEUE_ROOT" "$RUN_DIR" "$REPORT_ROOT"
rm -f "$GATES_JSON"
mkdir -p "$QUEUE_ROOT/inbox"

ORIG_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"
if [ "$ORIG_BRANCH" = "$BRANCH_NAME" ]; then
  git -C "$REPO_ROOT" checkout master >/dev/null 2>&1 || git -C "$REPO_ROOT" checkout main >/dev/null
  ORIG_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"
fi
git -C "$REPO_ROOT" branch -D "$BRANCH_NAME" >/dev/null 2>&1 || true

cat > "$TASK_PATH" <<JSON
{
  "task_version": "agenttask/0.1",
  "task_id": "${TASK_ID}",
  "created_at": "2026-03-04T00:00:00Z",
  "priority": 10,
  "plan": {
    "version": "runplan/0.1",
    "plan_id": "agent-demo-plan",
    "created_at": "2026-03-04T00:00:00Z",
    "inputs": {"board_id": "demo", "test_id": "agent_demo"},
    "selected": {"test_config": "tests/none.json"},
    "context": {
      "workspace_dir": "${REPO_ROOT}",
      "run_root": "${REPO_ROOT}/runs",
      "artifact_root": "${RUN_DIR}/artifacts",
      "log_root": "${RUN_DIR}/logs"
    },
    "steps": [
      {
        "name": "check_demo",
        "type": "check.noop",
        "inputs": {
          "note": "agent-demo",
          "out_json": "${RUN_DIR}/artifacts/demo_noop.json"
        }
      }
    ],
    "recovery_policy": {"enabled": false},
    "meta": {"run_dir": "${RUN_DIR}"}
  },
  "validate": {"pre": [], "post": []}
}
JSON

cat > "$GATES_JSON" <<JSON
{
  "commands": [
    "python3 -m py_compile ael/agent.py ael/queue.py ael/reporting.py",
    "python3 tools/runner_smoke.py",
    "python3 -m py_compile ael/runner.py",
    "python3 -m py_compile tools/agent_smoke.py"
  ]
}
JSON

(
  cd "$REPO_ROOT"
  AEL_AGENT_ALLOW_DIRTY=1 python3 -m ael.agent --once --branch-worker --no-push --queue "$QUEUE_ROOT" --gates "$GATES_JSON" --report-root "$REPORT_ROOT"
)

DONE_TASK="${QUEUE_ROOT}/done/${TASK_NAME}"
FAILED_TASK="${QUEUE_ROOT}/failed/${TASK_NAME}"
STATE_PATH="${QUEUE_ROOT}/done/${TASK_NAME%.json}.state.json"
if [ ! -f "$STATE_PATH" ] && [ -f "${QUEUE_ROOT}/failed/${TASK_NAME%.json}.state.json" ]; then
  STATE_PATH="${QUEUE_ROOT}/failed/${TASK_NAME%.json}.state.json"
fi

if [ ! -f "$DONE_TASK" ] && [ ! -f "$FAILED_TASK" ]; then
  echo "[AGENT_DEMO] FAIL: task not moved to done/failed"
  exit 2
fi

if [ ! -f "$STATE_PATH" ]; then
  echo "[AGENT_DEMO] FAIL: state file missing"
  exit 2
fi

if [ ! -f "${RUN_DIR}/artifacts/run_plan.json" ] || [ ! -f "${RUN_DIR}/artifacts/result.json" ]; then
  echo "[AGENT_DEMO] FAIL: run artifacts missing"
  exit 2
fi

REPORT_PATH="${REPORT_ROOT}/nightly_${TODAY}.md"
if [ ! -f "$REPORT_PATH" ]; then
  echo "[AGENT_DEMO] FAIL: report missing"
  exit 2
fi

if ! git -C "$REPO_ROOT" show-ref --verify "refs/heads/${BRANCH_NAME}" >/dev/null 2>&1; then
  echo "[AGENT_DEMO] FAIL: branch not created"
  exit 2
fi

git -C "$REPO_ROOT" checkout "$ORIG_BRANCH" >/dev/null 2>&1 || true
git -C "$REPO_ROOT" branch -D "$BRANCH_NAME" >/dev/null 2>&1 || true

echo "[AGENT_DEMO] OK"
echo "- queue: $QUEUE_ROOT"
echo "- run_dir: $RUN_DIR"
echo "- report: $REPORT_PATH"
echo "- state: $STATE_PATH"
