# Phase-1 CLI Policy Cleanup (Core Boundary)

## What changed
- Added [`ael/config_resolver.py`](../ael/config_resolver.py) as the central policy layer for:
  - probe config resolution
  - notify probe policy
  - board config defaults
  - doctor required tool list
- Refactored [`ael/__main__.py`](../ael/__main__.py) to call resolver helpers instead of embedding board/probe/tool-specific policy.
- Added regression check script: [`tools/check_resolver_defaults.py`](../tools/check_resolver_defaults.py).

## Why
This removes board/probe/tool-specific policy from CLI orchestration code and keeps Core cleaner.  
Behavior remains compatible with existing flows by preserving prior defaults and routing policy inside resolver.

## Behavior compatibility
- `ael run` still works without explicit `--probe`.
- `ael doctor` still resolves default probe/board if not provided.
- `ael pack` still applies board-based notify-probe policy as before.
