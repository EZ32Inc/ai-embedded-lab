# ESP32 Meter Backend Consumer Migration

## Purpose

Use this skill when `ESP32-S3 meter` already has a backend package, but some
 runtime consumer paths still call the low-level TCP adapter directly.

## Rule

Do not reopen the whole meter architecture.

Migrate only the action path:

- `measure.digital`
- `measure.voltage`
- `stim.digital`

Keep these bounded where they already work:

- doctor
- reachability
- provision
- status metadata

## Recommended Migration Order

1. move native action wrappers onto the backend package
2. move one real consumer path onto the backend package
3. verify adapter-registry and native-dispatch paths still behave the same
4. only then consider higher-level migration

## Implementation Pattern

- keep endpoint parsing at the native wrapper boundary
- instantiate the backend wrapper from manifest-derived host/port
- call backend `execute(...)`
- preserve existing native API success/error envelope

## Why

This keeps migration risk low:

- transport stays in one place
- runtime callers converge on the new backend
- metadata and bench diagnostics do not need to be rewritten in the same batch
