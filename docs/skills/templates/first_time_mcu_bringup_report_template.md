# First-Time MCU Bring-Up Report Template

## Identity

- MCU:
- board/module:
- package:
- board family:
- DUT instance or bench target:
- report date:
- author:

## Scope of this round

- goal of this bring-up round:
- what is intentionally out of scope:

## Official source basis

- datasheet:
- reference manual:
- programming manual:
- official SDK/package:
- official startup/system source:
- official example paths reviewed:

## Selected implementation basis

- selected official implementation basis:
- why this basis was chosen:
- official files or examples actually used:
- implementation facts still unknown:

## Selected AEL methodology basis

- closest validated AEL methodology sources:
- why these were chosen:
- methodology elements reused:
- methodology elements intentionally not reused:

## Pre-generation drift check

- family drift:
- package/pinout drift:
- clock drift:
- peripheral-instance drift:
- linker/memory drift:
- bench/setup drift:
- unresolved blockers:

## Tests attempted

| test | implementation basis | methodology basis | result | notes |
| --- | --- | --- | --- | --- |
| | | | | |

## Results summary

- passed:
- failed:
- partial:
- blocked:

## Inferred assumptions

- inference:
  - why it was inferred:
  - confidence:
  - how it should be verified:

## Rejected paths

- rejected path:
  - why it was rejected:
  - what evidence led to rejection:

## Lessons learned

- what succeeded:
- what failed:
- what was learned:
- what should be written back into skills/workflows/specs:

## Recommended next step

- next safest implementation step:
- next safest validation step:
- user or bench facts still needed:

## Closeout validation

- cleaned full per-board suite rerun result:
- representative default-verification decision:
- if added to default verification, exact DUT-backed step selected:
- live default-verification evidence:
- DUT registration result:
- closeout note path:
