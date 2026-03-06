#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNS_DIR="${AEL_RUNS_ROOT:-$ROOT/runs}"

usage() {
  cat <<'USAGE'
Usage:
  tools/cleanup_runs.sh [cutoff] [--dry-run]
  tools/cleanup_runs.sh --full [--dry-run]

cutoff formats:
  YYYY-MM-DD
  YYYY-MM-DD_HH-MM-SS

Examples:
  tools/cleanup_runs.sh 2026-03-06_15-10-59
  tools/cleanup_runs.sh 2026-03-05

Behavior:
  If cutoff is provided, removes run directories in runs/ with timestamp
  strictly older than cutoff.
  If --full is provided, removes all run directories.
  Without cutoff/--full, prints help and exits.
USAGE
}

if [[ $# -eq 0 ]]; then
  usage
  exit 0
fi

CUTOFF_RAW=""
CUTOFF=""
DELETE_ALL=false
DRY_RUN=false

for arg in "$@"; do
  case "$arg" in
    --full)
      DELETE_ALL=true
      ;;
    --dry-run)
      DRY_RUN=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -n "$CUTOFF_RAW" ]]; then
        echo "Too many cutoff arguments." >&2
        usage
        exit 2
      fi
      CUTOFF_RAW="$arg"
      ;;
  esac
done

if [[ "$DELETE_ALL" == true && -n "$CUTOFF_RAW" ]]; then
  echo "Use either cutoff or --full, not both." >&2
  usage
  exit 2
fi

if [[ "$DELETE_ALL" == false && -z "$CUTOFF_RAW" ]]; then
  usage
  exit 0
fi

if [[ -n "$CUTOFF_RAW" ]]; then
  if [[ "$CUTOFF_RAW" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    CUTOFF="${CUTOFF_RAW}_00-00-00"
  elif [[ "$CUTOFF_RAW" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}$ ]]; then
    CUTOFF="$CUTOFF_RAW"
  else
    echo "Invalid cutoff format: $CUTOFF_RAW" >&2
    usage
    exit 2
  fi
fi

if [[ ! -d "$RUNS_DIR" ]]; then
  echo "Runs directory not found: $RUNS_DIR"
  exit 0
fi

echo "Runs dir: $RUNS_DIR"
if [[ "$DELETE_ALL" == true ]]; then
  echo "WARNING: --full provided; removing all run directories."
else
  echo "Cutoff:   $CUTOFF"
fi
[[ "$DRY_RUN" == true ]] && echo "Mode:     DRY-RUN (no files will be removed)"
echo

deleted=0
kept=0
skipped=0

shopt -s nullglob
for path in "$RUNS_DIR"/*; do
  [[ -d "$path" ]] || continue
  base="$(basename "$path")"

  # Expected prefix: YYYY-MM-DD_HH-MM-SS
  ts="${base:0:19}"
  if [[ ! "$ts" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "SKIP  $base (unexpected name format)"
    skipped=$((skipped + 1))
    continue
  fi

  if [[ "$DELETE_ALL" == true || "$ts" < "$CUTOFF" ]]; then
    if [[ "$DRY_RUN" == true ]]; then
      echo "DRY   $base"
    else
      rm -rf "$path"
      echo "DEL   $base"
    fi
    deleted=$((deleted + 1))
  else
    kept=$((kept + 1))
  fi
done

echo
echo "Summary: deleted=$deleted kept=$kept skipped=$skipped"
