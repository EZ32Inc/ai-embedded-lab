#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACTS_DIR="$ROOT/artifacts"

usage() {
  cat <<'USAGE'
Usage:
  tools/cleanup_artifacts.sh [cutoff] [--dry-run]
  tools/cleanup_artifacts.sh --full [--dry-run]

cutoff formats:
  YYYY-MM-DD
  YYYY-MM-DD_HH-MM-SS

Examples:
  tools/cleanup_artifacts.sh 2026-03-06_15-10-59
  tools/cleanup_artifacts.sh 2026-03-05
  tools/cleanup_artifacts.sh

Behavior:
  If cutoff is provided, removes top-level entries in artifacts/ older than cutoff
  based on mtime.
  If --full is provided, removes all top-level entries in artifacts/.
  Without cutoff/--full, prints help and exits.
USAGE
}

if [[ $# -eq 0 ]]; then
  usage
  exit 0
fi

CUTOFF_RAW=""
CUTOFF_SPEC=""
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
    CUTOFF_SPEC="${CUTOFF_RAW} 00:00:00"
  elif [[ "$CUTOFF_RAW" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}$ ]]; then
    CUTOFF_SPEC="${CUTOFF_RAW:0:10} ${CUTOFF_RAW:11:2}:${CUTOFF_RAW:14:2}:${CUTOFF_RAW:17:2}"
  else
    echo "Invalid cutoff format: $CUTOFF_RAW" >&2
    usage
    exit 2
  fi
fi

if [[ ! -d "$ARTIFACTS_DIR" ]]; then
  echo "Artifacts directory not found: $ARTIFACTS_DIR"
  exit 0
fi

echo "Artifacts dir: $ARTIFACTS_DIR"
if [[ "$DELETE_ALL" == true ]]; then
  echo "WARNING: --full provided; removing all top-level entries."
else
  echo "Cutoff:        $CUTOFF_RAW"
fi
[[ "$DRY_RUN" == true ]] && echo "Mode:          DRY-RUN (no files will be removed)"
echo

deleted=0
kept=0

clear_with_gitkeep() {
  local target_dir="$1"
  find "$target_dir" -mindepth 1 ! -path "$target_dir/.gitkeep" -exec rm -rf {} + >/dev/null 2>&1 || true
}

shopt -s nullglob
for path in "$ARTIFACTS_DIR"/*; do
  [[ -e "$path" ]] || continue
  base="$(basename "$path")"
  if [[ "$DELETE_ALL" == true ]]; then
    if [[ "$DRY_RUN" == true ]]; then
      echo "DRY   $base"
    else
      if [[ -d "$path" && -f "$path/.gitkeep" ]]; then
        clear_with_gitkeep "$path"
      else
        rm -rf "$path"
      fi
      echo "DEL   $base"
    fi
    deleted=$((deleted + 1))
    continue
  fi

  # Keep entry if it is newer than or equal to cutoff.
  if find "$path" -maxdepth 0 -newermt "$CUTOFF_SPEC" | grep -q .; then
    kept=$((kept + 1))
  else
    if [[ "$DRY_RUN" == true ]]; then
      echo "DRY   $base"
    else
      if [[ -d "$path" && -f "$path/.gitkeep" ]]; then
        clear_with_gitkeep "$path"
      else
        rm -rf "$path"
      fi
      echo "DEL   $base"
    fi
    deleted=$((deleted + 1))
  fi
done

echo
echo "Summary: deleted=$deleted kept=$kept"
