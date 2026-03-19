# USB-UART Bridge Package Alignment

## Purpose

Use this skill when a backend already works functionally, but still exists as a
 single-file legacy module while newer backends use the package form:

- `backend.py`
- `transport.py`
- `capability.py`
- `actions/...`

## Rule

Treat this as shape alignment, not feature expansion.

Do not redesign behavior in the same batch unless the current single-file
backend is already incorrect.

## Minimal Package Split

1. create package directory
2. move transport/open-connection logic into `transport.py`
3. move each action into `actions/...`
4. add thin `backend.py` wrapper
5. keep the old module as a compatibility shim

## Why

This gives packaging consistency without forcing immediate migration of every
import site and without mixing shape cleanup with behavioral changes.
