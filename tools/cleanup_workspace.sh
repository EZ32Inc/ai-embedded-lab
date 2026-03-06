#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNS_DIR="${AEL_RUNS_ROOT:-$ROOT/runs}"
QUEUE_DIR="$ROOT/queue"
REPORTS_DIR="$ROOT/reports"
CUTOFF=""
FULL=false

usage() {
  cat <<'USAGE'
Usage:
  tools/cleanup_workspace.sh [cutoff] [--dry-run]
  tools/cleanup_workspace.sh --full [--dry-run]

cutoff formats:
  YYYY-MM-DD
  YYYY-MM-DD_HH-MM-SS

Examples:
  tools/cleanup_workspace.sh 2026-03-05
  tools/cleanup_workspace.sh 2026-03-06_15-10-59
  tools/cleanup_workspace.sh --full
USAGE
}

if [[ $# -eq 0 ]]; then
  usage
  exit 0
fi

if [[ $# -gt 2 ]]; then
  usage
  exit 2
fi

if [[ $# -eq 1 ]]; then
  :
fi
DRY_RUN=false
for arg in "$@"; do
  case "$arg" in
    --full)
      FULL=true
      ;;
    --dry-run)
      DRY_RUN=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -n "$CUTOFF" ]]; then
        echo "[cleanup_workspace] too many cutoff arguments" >&2
        usage
        exit 2
      fi
      CUTOFF="$arg"
      ;;
  esac
done

if [[ "$FULL" == true && -n "$CUTOFF" ]]; then
  echo "[cleanup_workspace] use either cutoff or --full, not both" >&2
  usage
  exit 2
fi

echo "[cleanup_workspace] root=$ROOT"
echo

echo "[cleanup_workspace] runs"
if [[ "$FULL" == true ]]; then
  if [[ "$DRY_RUN" == true ]]; then
    "$ROOT/tools/cleanup_runs.sh" --full --dry-run
  else
    "$ROOT/tools/cleanup_runs.sh" --full
  fi
elif [[ -n "$CUTOFF" ]]; then
  if [[ "$DRY_RUN" == true ]]; then
    "$ROOT/tools/cleanup_runs.sh" "$CUTOFF" --dry-run
  else
    "$ROOT/tools/cleanup_runs.sh" "$CUTOFF"
  fi
fi
echo

echo "[cleanup_workspace] artifacts"
if [[ "$FULL" == true ]]; then
  if [[ "$DRY_RUN" == true ]]; then
    "$ROOT/tools/cleanup_artifacts.sh" --full --dry-run
  else
    "$ROOT/tools/cleanup_artifacts.sh" --full
  fi
elif [[ -n "$CUTOFF" ]]; then
  if [[ "$DRY_RUN" == true ]]; then
    "$ROOT/tools/cleanup_artifacts.sh" "$CUTOFF" --dry-run
  else
    "$ROOT/tools/cleanup_artifacts.sh" "$CUTOFF"
  fi
fi
echo

cleanup_flat_dir() {
  local dir="$1"
  local label="$2"
  local cutoff_spec="$3"
  if [[ ! -d "$dir" ]]; then
    echo "[cleanup_workspace] $label: missing ($dir)"
    return
  fi
  local deleted=0
  local kept=0
  local clear_with_gitkeep
  clear_with_gitkeep() {
    local target_dir="$1"
    find "$target_dir" -mindepth 1 ! -path "$target_dir/.gitkeep" -exec rm -rf {} + >/dev/null 2>&1 || true
  }
  shopt -s nullglob
  for p in "$dir"/*; do
    [[ -e "$p" ]] || continue
    if [[ -z "$cutoff_spec" ]]; then
      if [[ "$DRY_RUN" == true ]]; then
        :
      else
        if [[ -d "$p" && -f "$p/.gitkeep" ]]; then
          clear_with_gitkeep "$p"
        else
          rm -rf "$p"
        fi
      fi
      deleted=$((deleted + 1))
    else
      if find "$p" -maxdepth 0 -newermt "$cutoff_spec" | grep -q .; then
        kept=$((kept + 1))
      else
        if [[ "$DRY_RUN" == true ]]; then
          :
        else
          if [[ -d "$p" && -f "$p/.gitkeep" ]]; then
            clear_with_gitkeep "$p"
          else
            rm -rf "$p"
          fi
        fi
        deleted=$((deleted + 1))
      fi
    fi
  done
  echo "[cleanup_workspace] $label: deleted=$deleted kept=$kept"
}

CUTOFF_SPEC=""
if [[ "$FULL" == true ]]; then
  echo "[cleanup_workspace] WARNING: --full provided; removing all generated entries."
elif [[ -n "$CUTOFF" ]]; then
  if [[ "$CUTOFF" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    CUTOFF_SPEC="${CUTOFF} 00:00:00"
  elif [[ "$CUTOFF" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}$ ]]; then
    CUTOFF_SPEC="${CUTOFF:0:10} ${CUTOFF:11:2}:${CUTOFF:14:2}:${CUTOFF:17:2}"
  else
    echo "[cleanup_workspace] invalid cutoff format: $CUTOFF" >&2
    exit 2
  fi
fi

cleanup_flat_dir "$QUEUE_DIR" "queue" "$CUTOFF_SPEC"
cleanup_flat_dir "$REPORTS_DIR" "reports" "$CUTOFF_SPEC"

echo
echo "[cleanup_workspace] remove Python cache files"
if [[ -z "$CUTOFF_SPEC" ]]; then
  if [[ "$DRY_RUN" != true ]]; then
    find "$ROOT" -type d -name "__pycache__" -prune -exec rm -rf {} + >/dev/null 2>&1 || true
    find "$ROOT" -type f -name "*.pyc" -delete >/dev/null 2>&1 || true
  fi
else
  if [[ "$DRY_RUN" != true ]]; then
    find "$ROOT" -type d -name "__pycache__" ! -newermt "$CUTOFF_SPEC" -prune -exec rm -rf {} + >/dev/null 2>&1 || true
    find "$ROOT" -type f -name "*.pyc" ! -newermt "$CUTOFF_SPEC" -delete >/dev/null 2>&1 || true
  fi
fi

echo
echo "[cleanup_workspace] remove tool cache dirs/files"
cleanup_tool_caches() {
  local cutoff_spec="$1"
  local deleted=0
  local kept=0
  while IFS= read -r -d '' p; do
    if [[ -n "$cutoff_spec" ]] && find "$p" -maxdepth 0 -newermt "$cutoff_spec" | grep -q .; then
      kept=$((kept + 1))
      continue
    fi
    if [[ "$DRY_RUN" != true ]]; then
      rm -rf "$p"
    fi
    deleted=$((deleted + 1))
  done < <(
    find "$ROOT" \
      \( \
        \( -type d \( -name ".pytest_cache" -o -name ".mypy_cache" -o -name ".ruff_cache" -o -name ".tox" -o -name ".nox" \) \) \
        -o \
        \( -type f \( -name ".coverage" -o -name ".coverage.*" -o -name "*.pyo" \) \) \
      \) \
      -print0 2>/dev/null || true
  )
  echo "[cleanup_workspace] tool-caches: deleted=$deleted kept=$kept"
}

cleanup_tool_caches "$CUTOFF_SPEC"

if [[ "$DRY_RUN" == true ]]; then
  echo "[cleanup_workspace] done (dry-run)"
else
  echo "[cleanup_workspace] done"
fi
