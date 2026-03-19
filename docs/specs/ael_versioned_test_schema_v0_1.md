# AEL Versioned Test Schema Specification v0.1

**Date:** 2026-03-19
**Version:** v0.1
**Status:** Draft

---

## 1. Purpose

Define a **versioned and extensible test definition model** for AEL that:

- preserves legacy tests
- enables structured new tests
- supports multiple test kinds
- allows future schema evolution

This document describes a **schema version** for test-plan structure.
It does **not** yet define a separate semantic versioning model for a logical
family such as `gpio_signature v2`.

---

## 2. Scope and Current Repo Fit

In the current codebase, tests are primarily identified and loaded as plan files
under `tests/plans/*.json`.

That means v0.1 should be interpreted as an **in-place extension** of the
existing plan files, not as a new test storage layout.

For v0.1:

- canonical runtime reference remains the plan path
- packs continue to reference tests by plan path
- structured schema fields are added inside existing plan JSON files
- legacy plans remain valid without modification

This keeps the spec aligned with the current inventory, pack-loading, and
runner model.

---

## 3. Core Model

Each test plan is interpreted under one of the following:

### 3.1 Legacy Test Plan

A test plan is considered **legacy** if:

- it has no `schema_version`, OR
- `schema_version: "legacy"`

**Execution:** handled by the current legacy plan/runner path.

### 3.2 Structured Test Plan

A test plan is considered **structured** if:

- it declares a `schema_version` other than `legacy`

In v0.1, this primarily means:

- the plan carries explicit structured metadata
- inventory and static validation may use that metadata
- future runtime dispatch may use that metadata

Structured schema support should therefore be introduced in phases rather than
assuming immediate runner branching.

---

## 4. Required Fields (Structured Test Plans)

### 4.1 `schema_version`

```yaml
schema_version: "1.0"
```

- Identifies the **plan schema version**
- Does **not** mean the semantic version of the logical test family
- May later be used by validation and runner dispatch logic

### 4.2 `test_kind`

```yaml
test_kind: "baremetal_mailbox"
```

- Defines the execution/validation model of the plan
- Intended to guide future executor selection
- In v0.1, should first be treated as explicit metadata

### 4.3 `name`

```yaml
name: "stm32f103_gpio_mailbox"
```

- Logical identifier for humans, inventory, and reporting
- The plan path remains the canonical runtime reference in v0.1

---

## 5. Optional Fields (v1.0)

### 5.1 `target`

```yaml
target: "stm32f103c8t6"
```

### 5.2 `labels`

```yaml
labels:
  - mailbox
  - portable
  - default_candidate
```

### 5.3 `supported_instruments`

```yaml
supported_instruments:
  - stlink
  - esp32jtag
```

### 5.4 `requires`

```yaml
requires:
  mailbox: true
  datacapture: false
```

### 5.5 `covers`

```yaml
covers:
  - adc
  - uart
  - spi
  - exti
```

These fields are intentionally modest.
They should be added without requiring a broader runtime refactor.

---

## 6. Identity and Reference Rules

### 6.1 Canonical Runtime Reference

In v0.1, the canonical runtime reference is still the plan path, for example:

```text
tests/plans/stm32f103rct6_mailbox.json
```

### 6.2 Logical Identifier

`name` is the logical identifier.
It is useful for:

- inventory output
- reporting
- documentation
- future higher-level resolution

It should not replace plan-path references in v0.1 pack or runner flows.

### 6.3 No New Layout Yet

This specification does **not** require introducing a new layout such as:

```text
ael/tests/<family>/v1/test.yaml
```

That is a possible future design, but it is outside the bounded scope of this
schema spec.

---

## 7. Execution and Adoption Rules

### 7.1 Phase 1: Metadata Acceptance

The system should first support:

1. legacy plans with no `schema_version`
2. structured plans with explicit metadata fields
3. static validation of structured fields

### 7.2 Phase 2: Inventory and Reporting Awareness

After metadata is accepted, inventory and reporting surfaces may expose:

- `schema_version`
- `test_kind`
- `supported_instruments`
- `requires`

### 7.3 Phase 3: Optional Runtime Dispatch

Only after the metadata model is stable should the runner optionally branch on:

- `schema_version`
- `test_kind`

This is a future execution phase, not an immediate requirement of v0.1.

### 7.4 Unknown Versions

| `schema_version` | Behavior |
|------------------|----------|
| absent | treat as legacy |
| `legacy` | legacy execution path |
| `1.0` | structured metadata path |
| unknown | produce explicit validation error or warning |

---

## 8. Backward Compatibility

- All existing tests remain runnable without modification
- Absence of structured schema implies legacy behavior
- Existing packs do not need format changes
- Existing plan-path references remain valid
- Legacy execution must remain stable

---

## 9. Design Constraints

### 9.1 No Implicit Guessing

Runtime and validation logic should not:

- infer mechanism from file names alone
- guess instrument requirements
- assume mailbox or datacapture without declaration when structured metadata is present

### 9.2 Explicit Over Implicit

Structured test plans should:

- declare required capabilities
- declare supported instruments when known
- avoid hidden dependencies

### 9.3 Schema Version Is Not Test Family Version

This document intentionally separates:

- plan schema version
- future semantic evolution of a logical test family

If AEL later needs `gpio_signature` contract versions, that should be defined in
another layer rather than overloaded into `schema_version`.

---

## 10. Examples

### 10.1 Structured Mailbox Plan (In-Place Upgrade)

```yaml
schema_version: "1.0"
test_kind: "baremetal_mailbox"
name: "stm32f103_gpio_mailbox"
target: "stm32f103c8t6"
labels:
  - mailbox
  - portable
  - cross_instrument
  - default_candidate
supported_instruments:
  - stlink
  - esp32jtag
requires:
  mailbox: true
  datacapture: false
covers:
  - adc
  - uart
  - spi
  - exti
```

Notes:

- This plan still lives under `tests/plans/*.json`
- Packs still reference it by path
- The added fields are structured metadata, not a new storage model

### 10.2 Legacy Equivalent (Logical Form)

```yaml
schema_version: "legacy"
test_kind: "instrument_specific"
name: "stm32f103_gpio_signature"
target: "stm32f103c8t6"
supported_instruments:
  - esp32jtag
requires:
  mailbox: false
  datacapture: true
```

Notes:

- In practice, many legacy plans may contain no structured schema block at all
- Missing `schema_version` is interpreted as legacy for compatibility

### 10.3 Pack Reference Remains Unchanged

```json
{
  "name": "base_pack",
  "tests": [
    "tests/plans/stm32f103rct6_mailbox.json"
  ]
}
```

Notes:

- v0.1 does not require packs to reference tests by logical ID
- Path-based pack references remain the current-compatible form

---

## 11. Evolution Policy

- Schema may evolve across versions (`1.0` -> `1.1` -> `2.0`)
- New fields should be backward-compatible within the same major version
- Breaking structural changes require a major version bump

### Version Roadmap (Anticipated)

| Version | Scope |
|---------|-------|
| `legacy` | old plans, no structured metadata, legacy execution path |
| `1.0` | first structured schema: `test_kind`, labels, `supported_instruments`, `requires` |
| `1.1` | optional enhancements: `preferred_instruments`, `fallback_policy`, `verification_tier`, timeouts |
| `2.0` | richer dispatch semantics, dependency graph, test composition |

---

## 12. Test Kind Reference

Known `test_kind` values (v1.0):

| `test_kind` | Description |
|-------------|-------------|
| `baremetal_mailbox` | bare-metal MCU test using Mailbox for observation |
| `instrument_specific` | test requiring instrument-side capability such as DataCapture |

Future kinds (anticipated):

| `test_kind` | Description |
|-------------|-------------|
| `rtos_functional` | RTOS-based functional test |
| `linux_system` | Linux OS-level system test |
| `linux_driver` | Linux kernel driver test |
| `integration` | multi-component integration test |

---

## 13. Guiding Principle

> Prefer structured test plans for new development.
> Preserve legacy tests without modification.
> Keep v0.1 aligned with the current path-based plan model.

---

## 14. Initial Implementation Guidance

Recommended first implementation order:

1. accept structured fields inside existing `tests/plans/*.json`
2. add static validation for those fields
3. expose them in inventory/reporting
4. only later consider runner dispatch changes

Recommended initial required fields:

- `schema_version`
- `test_kind`
- `name`

Recommended initial optional fields:

- `supported_instruments`
- `requires`
- `labels`
- `covers`

---

## 15. Revision Note

This document is a **draft**.

The following may be revised in future versions:

- field names
- field meanings
- required vs optional fields
- example structures
- supported `test_kind` values
- exact validation and dispatch behavior

> The examples in this document are illustrative, not final.
> The schema should evolve with the repo, but should not outrun the current
> inventory/pack/runner model without an explicit migration step.

---

## 16. Summary

- legacy plans remain valid
- structured plans are in-place extensions of `tests/plans/*.json`
- plan path remains the canonical runtime reference in v0.1
- `schema_version` is a plan schema version, not a logical test family version
- inventory/reporting should adopt the schema before runner dispatch depends on it

> This enables AEL to add explicit structure without breaking the current
> plan-based execution model.
