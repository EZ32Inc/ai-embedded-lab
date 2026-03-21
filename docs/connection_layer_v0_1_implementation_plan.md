# Connection Layer v0.1 — Implementation Plan

**Date:** 2026-03-21
**Status:** Ready for Implementation
**Goal:** Formalize the existing connection metadata into a contract layer so AI can reason about bench setup correctness.

---

## Background

The codebase already has rich connection infrastructure. This plan closes the gap between "data exists" and "setup correctness is answerable."

### What already exists (do not rebuild)

| File | What it does |
|---|---|
| `ael/connection_model.py` | `NormalizedConnectionContext` dataclass — `default_wiring`, `bench_connections`, `observe_map`, `bench_setup`, `warnings`, `validation_errors` |
| `ael/connection_metadata.py` | Schema validation for all `bench_setup` sub-fields |
| `ael/connection_doctor.py` | Consistency checks — duplicate pins, ground confirmation, verify mapping |
| `ael/adapters/preflight.py` | Probe TCP reachability checks (does NOT check connection/wiring) |
| `configs/boards/*.yaml` | Already carry `bench_connections`, `default_wiring`, `observe_map`, `verification_views` |
| Test plans (`tests/plans/`) | Already use `bench_setup.dut_to_instrument`, `instrument_roles`, `external_inputs`, `peripheral_signals` |

### Existing field names (exact, for reference)

**Board-level fields:**
- `default_wiring` — dict with keys `swd`, `reset`, `verify`
- `bench_connections` — list of `{from, to}` pairs
- `observe_map` — symbolic aliases (sig, led, etc.)
- `verification_views` — named observation interpretations with `pin` and `resolved_to`
- `safe_pins` — list of pins safe for discovery (defined but unused)

**Test plan `bench_setup` sub-fields:**
- `dut_to_instrument[]` — `{dut_gpio, inst_gpio, expect, freq_hz}`
- `dut_to_instrument_analog[]` — `{dut_signal, inst_adc_gpio, expect_v_min, expect_v_max, avg}`
- `ground_required`, `ground_confirmed` — booleans
- `serial_console` — `{port, baud}`
- `peripheral_signals[]` — `{role, dut_signal, direction, notes}`
- `external_inputs[]` — `{source, dut_signal, kind, required, status, notes}`
- `instrument_roles[]` — `{role, instrument_id, endpoint, required, notes}`

**Validation that already exists:**
- Type checking (dict, list, bool, string)
- Required field presence per sub-schema
- Non-empty string validation
- Boolean type checking for `required`, `ground_required`, `ground_confirmed`

**Validation that does NOT exist yet (this plan adds it):**
- Enum validation (`expect` should be one of `toggle`, `high`, `low`)
- Cross-field constraints
- Endpoint reachability at preflight
- Setup completeness rollup
- Power/boot structure

---

## Implementation: Three Gaps to Close

---

### Gap 1 — Setup Completeness Contract

**Priority: Implement first. Highest impact.**

**The problem:** Tests can declare `external_inputs` with `status: "manual_loopback_required"`, but nothing stops execution if setup is incomplete. AI cannot answer "is this bench ready to run?"

**What to implement:**

#### 1a. Add `SetupComponentStatus` enum

In `ael/connection_model.py`, add:

```python
from enum import Enum

class SetupComponentStatus(str, Enum):
    VERIFIED = "verified"                          # confirmed by discovery or prior run
    PROVISIONED_UNVERIFIED = "provisioned_unverified"  # wired but not auto-confirmed
    DEFINED_NOT_PROVISIONED = "defined_not_provisioned"  # in config, not yet wired
    MANUALLY_UNSPECIFIED = "manually_unspecified"  # manual step required, status unknown
    NOT_APPLICABLE = "not_applicable"
```

#### 1b. Add `SetupReadinessSummary` dataclass

In `ael/connection_model.py`, add alongside `NormalizedConnectionContext`:

```python
@dataclass
class SetupComponentEntry:
    component_type: str        # "instrument_role", "external_input", "dut_to_instrument"
    component_id: str          # role name or source name
    status: SetupComponentStatus
    required: bool
    notes: str = ""

@dataclass
class SetupReadinessSummary:
    overall: SetupComponentStatus          # worst-case rollup across required components
    components: List[SetupComponentEntry]
    blocking_issues: List[str]             # human-readable list of what blocks execution
    warnings: List[str]                    # non-blocking issues
    ready_to_run: bool                     # True only if all required components are VERIFIED or PROVISIONED_UNVERIFIED
```

#### 1c. Add `build_setup_readiness()` function

New function in `ael/connection_metadata.py` (or new file `ael/setup_readiness.py`):

```python
def build_setup_readiness(bench_setup: dict) -> SetupReadinessSummary:
    """
    Build a SetupReadinessSummary from bench_setup dict.
    Maps existing status strings to SetupComponentStatus enum.
    """
    STATUS_MAP = {
        "manual_loopback_required": SetupComponentStatus.MANUALLY_UNSPECIFIED,
        "defined_not_provisioned": SetupComponentStatus.DEFINED_NOT_PROVISIONED,
        "provisioned": SetupComponentStatus.PROVISIONED_UNVERIFIED,
        "verified": SetupComponentStatus.VERIFIED,
    }
    components = []

    # Process instrument_roles
    for role in bench_setup.get("instrument_roles", []):
        status_str = role.get("status", "provisioned")
        components.append(SetupComponentEntry(
            component_type="instrument_role",
            component_id=role.get("role", "unknown"),
            status=STATUS_MAP.get(status_str, SetupComponentStatus.PROVISIONED_UNVERIFIED),
            required=role.get("required", True),
            notes=role.get("notes", ""),
        ))

    # Process external_inputs
    for ext in bench_setup.get("external_inputs", []):
        status_str = ext.get("status", "defined_not_provisioned")
        components.append(SetupComponentEntry(
            component_type="external_input",
            component_id=ext.get("source", "unknown"),
            status=STATUS_MAP.get(status_str, SetupComponentStatus.DEFINED_NOT_PROVISIONED),
            required=ext.get("required", True),
            notes=ext.get("notes", ""),
        ))

    # Process dut_to_instrument (assumed provisioned unless overridden)
    for conn in bench_setup.get("dut_to_instrument", []):
        components.append(SetupComponentEntry(
            component_type="dut_to_instrument",
            component_id=conn.get("dut_gpio", "unknown"),
            status=SetupComponentStatus.PROVISIONED_UNVERIFIED,
            required=True,
        ))

    blocking = [
        f"{c.component_type} '{c.component_id}': {c.status.value}"
        for c in components
        if c.required and c.status in (
            SetupComponentStatus.DEFINED_NOT_PROVISIONED,
            SetupComponentStatus.MANUALLY_UNSPECIFIED,
        )
    ]

    required_statuses = [c.status for c in components if c.required]
    if not required_statuses:
        overall = SetupComponentStatus.NOT_APPLICABLE
    elif SetupComponentStatus.MANUALLY_UNSPECIFIED in required_statuses:
        overall = SetupComponentStatus.MANUALLY_UNSPECIFIED
    elif SetupComponentStatus.DEFINED_NOT_PROVISIONED in required_statuses:
        overall = SetupComponentStatus.DEFINED_NOT_PROVISIONED
    elif SetupComponentStatus.PROVISIONED_UNVERIFIED in required_statuses:
        overall = SetupComponentStatus.PROVISIONED_UNVERIFIED
    else:
        overall = SetupComponentStatus.VERIFIED

    return SetupReadinessSummary(
        overall=overall,
        components=components,
        blocking_issues=blocking,
        warnings=[],
        ready_to_run=len(blocking) == 0,
    )
```

#### 1d. Attach to `NormalizedConnectionContext`

Add `setup_readiness: Optional[SetupReadinessSummary] = None` to the dataclass.

Populate it in the existing normalization function that builds `NormalizedConnectionContext`.

#### 1e. Surface in `describe_connection()` output

In `ael/inventory.py`, add `setup_readiness` to the connection descriptor returned by `describe_connection()` / `describe_test()`.

---

### Gap 2 — Preflight Connection Check

**Priority: Implement second.**

**The problem:** `ael/adapters/preflight.py` checks probe TCP reachability but never checks whether declared connection setup is valid or complete.

**What to implement:**

#### 2a. Add `check_connection_readiness()` to preflight

In `ael/adapters/preflight.py`, add a new check function:

```python
def check_connection_readiness(run_context: dict) -> List[PreflightIssue]:
    """
    Check connection/setup readiness before run.
    Returns list of issues (blocking or advisory).
    """
    issues = []
    bench_setup = run_context.get("bench_setup", {})
    readiness = build_setup_readiness(bench_setup)  # from Gap 1

    # Blocking: required components not provisioned
    for issue_text in readiness.blocking_issues:
        issues.append(PreflightIssue(
            kind="connection_setup_incomplete",
            severity="blocking",
            message=issue_text,
        ))

    # Advisory: instrument_roles endpoint reachability
    for role in bench_setup.get("instrument_roles", []):
        endpoint = role.get("endpoint")
        if endpoint and role.get("required", True):
            reachable = _tcp_ping(endpoint)  # existing helper
            if not reachable:
                issues.append(PreflightIssue(
                    kind="instrument_role_unreachable",
                    severity="blocking",
                    message=f"instrument_role '{role.get('role')}' endpoint {endpoint} not reachable",
                ))

    # Advisory: warn if dut_to_instrument declared but no discovery run
    if bench_setup.get("dut_to_instrument") and not bench_setup.get("discovery_status"):
        issues.append(PreflightIssue(
            kind="wiring_not_verified",
            severity="advisory",
            message="dut_to_instrument mappings declared but wiring not verified by auto-discovery",
        ))

    return issues
```

#### 2b. Call from existing preflight flow

Wire `check_connection_readiness()` into the preflight adapter step so it runs before flash/verify. If any `blocking` issues are found, fail the preflight step with a clear error message that lists what setup is missing.

---

### Gap 3 — Power/Boot Setup Explicit in Board Configs

**Priority: Implement third (lower urgency, but needed before DUT abstraction).**

**The problem:** Reset timing, boot mode pins, power sequencing are all implicit in firmware or operator knowledge. AI cannot reason about them. This creates silent failures and implicit assumptions.

**What to implement:**

#### 3a. Add optional `power_and_boot` section to board config schema

Add to board YAML files (e.g. `configs/boards/stm32f401rct6.yaml`):

```yaml
power_and_boot:
  reset_strategy: "connect_under_reset"   # or "pulse_reset", "none"
  boot_mode_default: "normal"             # or "bootloader", "isp"
  power_rails:
    - name: "VCC_3V3"
      nominal_v: 3.3
      tolerance_v: 0.2
  boot_pins: []                           # list of pins that control boot mode, if any
  notes: "NRST must pulse >10µs for clean reset"
```

#### 3b. Add validation for `power_and_boot`

In `ael/connection_metadata.py`, add validation:

```python
VALID_RESET_STRATEGIES = {"connect_under_reset", "pulse_reset", "none"}
VALID_BOOT_MODES = {"normal", "bootloader", "isp"}

def validate_power_and_boot(power_and_boot: dict) -> List[str]:
    errors = []
    strategy = power_and_boot.get("reset_strategy")
    if strategy and strategy not in VALID_RESET_STRATEGIES:
        errors.append(f"reset_strategy '{strategy}' not in {VALID_RESET_STRATEGIES}")
    boot_mode = power_and_boot.get("boot_mode_default")
    if boot_mode and boot_mode not in VALID_BOOT_MODES:
        errors.append(f"boot_mode_default '{boot_mode}' not in {VALID_BOOT_MODES}")
    for rail in power_and_boot.get("power_rails", []):
        if "name" not in rail or "nominal_v" not in rail:
            errors.append("power_rail entry missing required 'name' or 'nominal_v'")
    return errors
```

#### 3c. Include in board config loading

In wherever board YAML is loaded (likely `ael/config_resolver.py` or `ael/pipeline.py`), parse the `power_and_boot` section and pass it through to the run context so it's available to preflight and stage_explain.

#### 3d. Populate `power_and_boot` in existing board configs

For each board in `configs/boards/`:
- Add `reset_strategy` (check existing flash config for what's already being used)
- Add `power_rails` with at least the main VCC rail
- Add `boot_mode_default`

This is data entry, not code — but required for the schema to have real coverage.

---

## Testing

For each gap, add or extend tests:

- **Gap 1:** `tests/test_connection_model.py` or new `tests/test_setup_readiness.py`
  - Test `build_setup_readiness()` with `manual_loopback_required` input → expect `ready_to_run=False`
  - Test with all `provisioned` inputs → expect `ready_to_run=True`
  - Test rollup logic (worst-case wins)

- **Gap 2:** `tests/test_preflight.py` or extend existing
  - Test that blocking `external_inputs` produces a blocking preflight issue
  - Test that unreachable `instrument_roles` endpoint produces a blocking issue
  - Test that missing `discovery_status` produces advisory (not blocking)

- **Gap 3:** Add to board config validation tests
  - Valid `reset_strategy` values pass
  - Invalid value produces error
  - Missing optional section is fine (no error)

All changes must continue to pass `python3 -m ael verify-default run` without regression.

---

## Acceptance Criteria

The Connection Layer v0.1 is complete when:

- [ ] `NormalizedConnectionContext` carries a `setup_readiness` field with per-component status
- [ ] `build_setup_readiness()` correctly maps existing `bench_setup` status strings to enum values
- [ ] Preflight raises a blocking issue when required setup components are not provisioned
- [ ] Preflight raises a blocking issue when a required `instrument_roles` endpoint is unreachable
- [ ] Preflight raises an advisory warning when `dut_to_instrument` is declared but wiring is unverified
- [ ] All board configs have a `power_and_boot` section with at least `reset_strategy` and `power_rails`
- [ ] `validate_power_and_boot()` rejects invalid enum values
- [ ] All existing tests pass
- [ ] `verify-default run` passes without regression

---

## What NOT to implement in v0.1

- Bench wiring auto-discovery (GPIO frequency scan) — designed but not now
- Distributed or cross-host connection tracking
- Voltage domain cross-validation between bench_setup and power_rails
- Dynamic setup state tracking across multiple runs
- Any changes to the runner or pipeline orchestration

---

## File Change Summary

| File | Change |
|---|---|
| `ael/connection_model.py` | Add `SetupComponentStatus`, `SetupComponentEntry`, `SetupReadinessSummary`; add `setup_readiness` field to `NormalizedConnectionContext` |
| `ael/connection_metadata.py` | Add `build_setup_readiness()`, `validate_power_and_boot()` |
| `ael/adapters/preflight.py` | Add `check_connection_readiness()`, wire into preflight step |
| `ael/inventory.py` | Surface `setup_readiness` in `describe_connection()` output |
| `configs/boards/*.yaml` | Add `power_and_boot` section to each board config |
| `tests/test_setup_readiness.py` | New test file for Gap 1 |
| `tests/test_preflight.py` | Extend or create for Gap 2 |
