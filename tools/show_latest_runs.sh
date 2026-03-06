#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNS_DIR="${AEL_RUNS_ROOT:-$ROOT/runs}"
COUNT="${1:-5}"

if [[ ! -d "$RUNS_DIR" ]]; then
  echo "No runs directory: $RUNS_DIR"
  exit 0
fi

echo "Runs dir: $RUNS_DIR"
echo

mapfile -t RUNS < <(ls -1dt "$RUNS_DIR"/* 2>/dev/null | head -n "$COUNT")

if [[ ${#RUNS[@]} -eq 0 ]]; then
  echo "No run folders found."
  exit 0
fi

for run in "${RUNS[@]}"; do
  result="$run/result.json"
  status="unknown"
  failed_step=""
  if [[ -f "$result" ]]; then
    status="$(python3 - <<'PY' "$result"
import json, sys
p = sys.argv[1]
try:
    data = json.load(open(p, "r", encoding="utf-8"))
except Exception:
    print("invalid")
    raise SystemExit(0)
print("ok" if data.get("ok") else "fail")
PY
)"
    failed_step="$(python3 - <<'PY' "$result"
import json, sys
p = sys.argv[1]
try:
    data = json.load(open(p, "r", encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
print((data.get("failed_step") or "").strip())
PY
)"
  fi

  echo "$run"
  echo "  status: $status"
  if [[ -n "$failed_step" ]]; then
    echo "  failed_step: $failed_step"
  fi
  [[ -f "$run/preflight.log" ]] && echo "  preflight: $run/preflight.log"
  [[ -f "$run/build.log" ]] && echo "  build: $run/build.log"
  [[ -f "$run/flash.log" ]] && echo "  flash: $run/flash.log"
  [[ -f "$run/verify.log" ]] && echo "  verify: $run/verify.log"
  echo
done
