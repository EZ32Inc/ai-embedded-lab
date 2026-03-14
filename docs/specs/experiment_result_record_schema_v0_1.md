# Experiment Result Record Schema v0.1

Purpose:
- define a small, machine-readable record structure for bounded capability-demo results
- keep raw run artifacts separate from durable experiment-memory records

## Required fields

### `schema_version`
- type: string
- required
- current value: `0.1`

### `board`
- type: string
- required
- board or DUT identity used for the experiment

### `fixture_variant`
- type: string
- required
- short name for the concrete fixture/setup variant

### `capability_demo`
- type: string
- required
- bounded capability/demo name

### `status`
- type: string
- required
- allowed values:
  - `design-confirmed`
  - `contract-complete`
  - `live-pass`
  - `repeat-pass`
  - `blocked`
  - `failed`

### `wiring`
- type: array of objects
- required
- exact physical wiring relevant to the result

### `firmware_target`
- type: string
- required

### `test_plan`
- type: string
- required

### `instrument_paths`
- type: array of objects
- required
- instruments actually involved in the run/result

### `evidence`
- type: object
- required
- should contain:
  - `run_id`
  - `run_path`
  - `summary_metrics`
  - `strongest_artifact`

### `conclusion`
- type: string
- required
- concise statement of what the result proves

## Optional fields

### `repeat_count`
- type: integer
- optional

### `failure_modes`
- type: array of strings
- optional

### `does_not_prove`
- type: array of strings
- optional

### `anchor_impact`
- type: string
- optional
- how this result affects anchor confidence
- state explicitly whether anchor confidence changed or did not change

### `notes`
- type: array of strings
- optional

### Closeout alignment
- closeout notes that accompany a record should use this section order:
  1. fixture/wiring
  2. proof method
  3. run evidence
  4. what this proves
  5. what this does not prove
  6. anchor impact

## Classification vocabulary

### `design-confirmed`
- design/wiring/peripheral correctness reviewed and accepted
- no real execution claim yet

### `contract-complete`
- formal contract/setup is complete enough to run
- no live pass claim yet

### `live-pass`
- one real bounded live experiment passed

### `repeat-pass`
- repeated real bounded runs passed consistently

### `blocked`
- execution not meaningfully completed because of an external blocker

### `failed`
- execution ran and did not satisfy bounded success criteria
