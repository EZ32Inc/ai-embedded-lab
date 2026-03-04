# RunPlan v0.1 (docs/runplan_v0_1.md)

This document defines the RunPlan v0.1 schema.

Fields marked OPTIONAL may be omitted by the Plan stage.
Runners must tolerate missing optional fields.

## Purpose

A **RunPlan** is the deterministic, machine-readable execution plan produced by the **Plan** stage.

It serves as AEL’s execution IR (intermediate representation):

- **Plan outputs** a RunPlan (pure data)
- **Preflight** consumes the RunPlan to validate readiness
- **Runner** executes the RunPlan steps
- **Report** stores the RunPlan alongside logs/artifacts to ensure reproducibility

A RunPlan must be:
- deterministic (same inputs → same plan)
- side-effect free to generate
- serializable (JSON)
- stable enough for `ael replay <run_plan.json>` in the future

---

## Part 1 — RunPlan Schema (Structure)

This section describes the **fields and meanings**.  
Values shown are placeholders; see Part 2 for a concrete example.

### Top-level object

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `version` | string | yes | Must be `"runplan/0.1"` |
| `plan_id` | string | yes | Unique identifier for this plan (uuid or short-id) |
| `created_at` | string | yes | ISO-8601 timestamp with timezone |
| `inputs` | object | yes | High-level identifiers requested by user/pack |
| `selected` | object | yes | Resolved config paths used for this run |
| `context` | object | yes | Run directory and artifact layout policy |
| `capabilities_required` | array[string] | no | Optional list of required capabilities (for preflight/report) |
| `preflight` | object | no | Optional preflight checklist derived from RunPlan |
| `steps` | array[Step] | yes | Ordered executable steps (Build → Run → Check(s)) |
| `recovery_policy` | object | no | Policy controlling retries/allowed recovery actions |
| `report` | object | no | What artifacts to emit/include |

---

### `inputs` object

Purpose: record **what was requested** (by CLI or pack), at an ID level.

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `board_id` | string | yes | Board identifier (e.g. `"stm32f4_nucleo"`) |
| `probe_id` | string | no | Probe identifier (if applicable) |
| `instrument_id` | string | no | Instrument identifier (if applicable) |
| `test_id` | string | yes | Test identifier |
| `pack_id` | string | no | Pack identifier if invoked via pack |

> Note: These are **IDs**, not implementation details. Different runs will have different values.

---

### `selected` object

Purpose: record the **exact configs** resolved by Plan.

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `board_config` | string | yes | Path to resolved board config |
| `probe_config` | string | no | Path to resolved probe config |
| `instrument_config` | string | no | Path to resolved instrument config |
| `test_config` | string | yes | Path to resolved test config |
| `pack_config` | string | no | Path to resolved pack config |

---

### `context` object

Purpose: define where artifacts/logs go, and enable reproducibility.

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `workspace_dir` | string | yes | Repo/workspace root |
| `run_root` | string | yes | Base directory for runs |
| `artifact_root` | string | yes | Artifact directory template |
| `log_root` | string | yes | Log directory template |

---

### `preflight` object (optional)

Purpose: list readiness checks to run **before execution**.

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `checks` | array[PreflightCheck] | yes | Checklist items |
| `policy` | object | no | Preflight behavior flags |

#### `PreflightCheck`

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `type` | string | yes | e.g. `"tool.exists"`, `"device.access"` |
| `args` | object | yes | Parameters for the check |

---

### `steps` array

Purpose: ordered steps that Runner executes.  
Each step is a pure specification: **Runner + adapter registry** perform the work.

#### `Step` object

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | yes | Stable name within the plan (e.g. `"build"`, `"run"`, `"check_uart"`) |
| `type` | string | yes | Adapter type key (registry lookup), e.g. `"build.idf"`, `"load.idf_esptool"`, `"check.uart_log"` |
| `inputs` | object | yes | Adapter-specific inputs |
| `outputs` | object | no | Expected outputs/artifacts (optional) |
| `recovery_hints` | array[RecoveryHint] | no | Optional hints for recoverable situations |

#### `RecoveryHint` (optional)

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `when` | string | yes | Machine-detectable condition label (e.g. `"download_mode_detected"`) |
| `recovery` | object | yes | Suggested recovery action/strategy/scope |

---

### `recovery_policy` object (optional)

Purpose: Runner-controlled recovery limits and allow-list.

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `retries` | object | yes | Retry budget per scope |
| `allow` | array[object] | yes | Allowed recovery actions and scopes |

Scopes:
- `check`, `run`, `build`, `preflight`, `plan`

---

### `report` object (optional)

Purpose: define what should be emitted/recorded.

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `emit` | array[string] | yes | File patterns to include in report |

---

## Part 2 — Example RunPlan (Concrete Instance)

This is a **realistic example** of a RunPlan generated for one specific run.
Your run will have different IDs/paths/steps depending on board/probe/test.

```json
{
  "version": "runplan/0.1",
  "plan_id": "b73c9f2a",
  "created_at": "2026-03-03T12:34:56-05:00",

  "inputs": {
    "board_id": "esp32s3_devkit",
    "probe_id": "esp32jtag",
    "instrument_id": "esp32s3_dev_c_meter",
    "test_id": "esp32s3_gpio_signature_with_meter",
    "pack_id": "esp32meter1"
  },

  "selected": {
    "board_config": "configs/boards/esp32s3_devkit.yaml",
    "probe_config": "configs/esp32jtag.yaml",
    "instrument_config": "configs/instruments/esp32s3_dev_c_meter.yaml",
    "test_config": "tests/esp32s3_gpio_signature_with_meter.json",
    "pack_config": "packs/esp32meter1.json"
  },

  "context": {
    "workspace_dir": ".",
    "run_root": "runs",
    "artifact_root": "runs/<run_id>/artifacts",
    "log_root": "runs/<run_id>/logs"
  },

  "preflight": {
    "checks": [
      { "type": "tool.exists", "args": { "cmd": "python3" } },
      { "type": "device.access", "args": { "path": "/dev/ttyACM0", "mode": "rw" } },
      { "type": "tcp.reachable", "args": { "host": "192.168.4.1", "port": 4242 } }
    ],
    "policy": { "fail_fast": true, "allow_warnings": true }
  },

  "steps": [
    {
      "name": "build",
      "type": "build.idf",
      "inputs": {
        "project_dir": "assets_golden/duts/esp32s3_devkit/gpio_signature/firmware",
        "target": "esp32s3"
      }
    },
    {
      "name": "run",
      "type": "load.idf_esptool",
      "inputs": {
        "port": "/dev/ttyACM0",
        "baud": 460800,
        "artifact": "artifacts/ael_esp32s3_gpio_signature.bin"
      }
    },
    {
      "name": "check_uart",
      "type": "check.uart_log",
      "inputs": {
        "port": "/dev/ttyACM0",
        "baud": 115200,
        "duration_s": 6,
        "expect": [{ "id": "ready", "pattern": "AEL_DUT_READY", "min_count": 1 }],
        "reset_strategy": "rts",
        "auto_reset_on_download": true
      },
      "recovery_hints": [
        {
          "when": "download_mode_detected",
          "recovery": { "action": "reset", "strategy": "rts", "scope": "run" }
        }
      ]
    },
    {
      "name": "check_digital",
      "type": "check.instrument_digital",
      "inputs": {
        "signals": [
          { "name": "GPIO11", "expect": "toggle" },
          { "name": "GPIO12", "expect": "toggle" },
          { "name": "GPIO13", "expect": "high" },
          { "name": "GPIO14", "expect": "low" }
        ]
      }
    },
    {
      "name": "check_voltage",
      "type": "check.instrument_voltage",
      "inputs": { "channel": "GPIO4", "range_v": [3.0, 3.45] }
    }
  ],

  "recovery_policy": {
    "retries": { "check": 2, "run": 2, "build": 1, "preflight": 0, "plan": 0 },
    "allow": [
      { "action": "reset", "scope": "run" },
      { "action": "reconnect", "scope": "run" }
    ]
  },

  "report": {
    "emit": ["run_plan.json", "preflight_report.json", "result.json", "logs/*", "artifacts/*"]
  }
}
