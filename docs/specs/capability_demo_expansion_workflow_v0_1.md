# Capability Demo Expansion Workflow v0.1

Purpose:
- define the bounded board-capability expansion process for AEL
- keep work ordered, evidence-based, and tied to current fixtures

## Stage 1: Choose Next Bounded Path

### Entry
- current anchor board and fixture are known
- at least one next capability candidate exists

### Actions
- choose one next capability path only
- confirm the path is worth doing now

### Exit
- one bounded path is selected
- one-sentence objective exists

### Expected artifacts
- bounded path decision note or spec

### AI stop rule
- stop if the path requires broad setup/framework change

## Stage 2: Validate Fixture / Pin / Peripheral Correctness

### Entry
- bounded path selected

### Actions
- verify pinmux/peripheral correctness
- identify conflicts with preserved paths
- confirm machine-checkable observe strategy
- define required wiring

### Exit
- corrected wiring proposal accepted
- bounded success method accepted

### Expected artifacts
- fixture/setup update
- per-demo spec draft

### Human-required action
- approve or confirm physical wiring if setup changes

### AI stop rule
- stop if correctness is uncertain or the setup assumption is risky

## Stage 3: Generate Repo Artifacts

### Entry
- fixture and success method accepted

### Actions
- generate/update:
  - demo spec
  - plan
  - firmware target
  - validation commands
  - regression framing

### Exit
- plan/build path is ready

### Expected artifacts
- repo-facing files sufficient for plan/build and bench execution

## Stage 4: User Wires Hardware

### Entry
- artifacts are ready
- exact wiring is documented

### Actions
- user performs physical wiring

### Exit
- hardware ready confirmation

### Human-required action
- yes

### AI stop rule
- stop until hardware-ready confirmation exists

## Stage 5: Run Bounded Real Experiment

### Entry
- hardware ready
- validation commands ready

### Actions
- run:
  - `inventory describe-test`
  - `explain-stage --stage plan`
  - one bounded live experiment
  - bounded repeat only if justified

### Exit
- real run evidence exists

### Expected artifacts
- run evidence under `runs/...`

## Stage 6: Capture Result

### Entry
- run evidence exists

### Actions
- summarize the experiment result
- create structured result record
- create closeout/health note if warranted

### Exit
- result is classified

### Expected artifacts
- result record
- optional closeout note

## Stage 7: Classify Result

### Entry
- result capture complete

### Actions
- classify as:
  - `design-confirmed`
  - `contract-complete`
  - `live-pass`
  - `repeat-pass`
  - `blocked`
  - `failed`

### Exit
- path status is clear

## Stage 8: Update Project Knowledge / Anchor Status

### Entry
- classification complete

### Actions
- update anchor/path status
- decide whether regression implications changed
- choose next bounded path

### Exit
- project memory updated
- next-step decision exists

## Mandatory stage-gate
- no next capability path starts until result capture and anchor status update are complete for the current path

## How This Applies To Current STM32F103 SPI Work
- Stage 1:
  - choose SPI self-check as the next bounded path
- Stage 2:
  - validate `PA5/PA6/PA7` internal SPI loopback and `PA4` as external observe output
- Stage 3:
  - generate STM32 SPI spec/plan/commands
- Stage 4:
  - user wires `PA7 -> PA6`
- Stage 5:
  - run the bounded SPI live test
- Stage 6-8:
  - capture result, classify it, and update STM32 anchor status
