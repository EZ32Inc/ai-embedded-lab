# Third-party source caches

This directory is for repo-local source caches used during target generation and
similar workflows.

Current workflow:
- `tools/fetch_stm32cubef4.sh` clones or refreshes ST's official
  `STM32CubeF4` source under `third_party/cache/STM32CubeF4`

The cache itself is intentionally gitignored. Generated targets that copy source
from a cache should record the exact upstream repo, revision, and copied paths
in their local `provenance.md`.
