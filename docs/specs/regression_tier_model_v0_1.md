## Regression Tier Model

Purpose:
- define the minimum necessary rerun scope after future changes
- keep rerun cost proportional to the actual change

### Regression tiers

#### Tier 0: Software / contract only
- scope:
  - docs
  - specs
  - catalog entries
  - closeout notes
  - non-runtime helper notes
- rerun:
  - targeted tests only

#### Tier 1: Bounded path validation
- scope:
  - one target/test/instrument path
  - one fixture-specific firmware/test-plan/runtime binding change
- rerun:
  - targeted tests
  - `inventory describe-test`
  - `explain-stage --stage plan`
  - one real run of the affected path

#### Tier 2: Core default baseline
- scope:
  - shared runtime used by default verification
  - default-verification config/model/routing
  - shared Local Instrument Interface path changes used by baseline workers
- rerun:
  - targeted tests
  - Anchor Set A

#### Tier 3: Baseline health check
- scope:
  - changes that may affect stability, locking, degraded-instrument handling, or repeat behavior
- rerun:
  - Anchor Set A
  - Anchor Set E with bounded `N`

#### Tier 4: Sample-board capability baseline
- scope:
  - capability expansion work on the primary sample board
  - bounded execution proofs beyond the default suite
- rerun:
  - Anchor Set B

#### Tier 5: Extended / high-friction validation
- scope:
  - new family setup
  - new external bench provisioning
  - major fixture identity changes
  - remote-host deployment changes
- rerun:
  - only the minimum affected anchors plus any specific new fixture run

### Change-class to regression-level mapping

#### Class 1: contract/docs/catalog only
- regression tier:
  - Tier 0

#### Class 2: non-runtime tooling/helper
- regression tier:
  - Tier 0 or Tier 1
- choose Tier 1 only if the helper directly affects a real executable path

#### Class 3: bounded path-specific runtime change
- regression tier:
  - Tier 1
- add Tier 4 if the path is part of the primary STM32 capability anchor set

#### Class 4: shared runtime / default-verification core change
- regression tier:
  - Tier 2
- add Tier 3 if stability/health semantics changed

#### Class 5: fixture/model boundary change
- regression tier:
  - Tier 2 minimum
- add Tier 5 if the change affects hardware identity, remote endpoints, or fixture provisioning

### Practical rerun rule

Use the smallest tier that still exercises the changed runtime surface.

Default rule:
- if a change is local to one path, use Tier 1
- if a change touches default-verification shared logic, use Tier 2
- if a change may affect stability/locking/health, use Tier 3
- if a change extends capability on STM32, use Tier 4
- use Tier 5 only when a real new fixture or remote/provisioned setup is involved
