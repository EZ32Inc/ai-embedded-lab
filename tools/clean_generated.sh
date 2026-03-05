#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

ASSUME_YES="${1:-}"

collect_generated_untracked() {
  git ls-files --others --exclude-standard | while IFS= read -r path; do
    case "${path}" in
      queue/done/*.json|queue/done/*.state.json|queue/running/*|reports/*.md|reports/*.json)
        printf '%s\n' "${path}"
        ;;
    esac
  done
}

mapfile -t GENERATED < <(collect_generated_untracked)

if [[ ${#GENERATED[@]} -eq 0 ]]; then
  echo "No generated untracked files found."
  exit 0
fi

echo "Generated untracked files found:"
for path in "${GENERATED[@]}"; do
  echo "  ${path}"
done

if [[ "${ASSUME_YES}" != "--yes" ]]; then
  echo
  read -r -p "To remove these generated files, continue? [Y/n] " reply
  reply="${reply:-Y}"
  case "${reply}" in
    Y|y|yes|YES)
      ;;
    *)
      echo "Cleanup cancelled."
      exit 0
      ;;
  esac
fi

for path in "${GENERATED[@]}"; do
  rm -f "${path}"
done

# Remove now-empty generated directories (best effort).
rmdir reports 2>/dev/null || true
rmdir queue/done 2>/dev/null || true
rmdir queue/running 2>/dev/null || true
rmdir queue 2>/dev/null || true

echo "Removed ${#GENERATED[@]} generated file(s)."
