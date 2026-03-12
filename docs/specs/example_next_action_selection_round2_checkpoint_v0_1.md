# Example Next Action Selection Round 2 Checkpoint v0.1

This note records the second round of the current 3-round review sequence.

## Scope

Round 2 focused on:

- turning the runtime-readiness model into a next-action selection workflow
- updating the example expansion decision so it respects real runtime blockers

## Main conclusion

The next step for a generated example should no longer be chosen by family
strength alone.

It should be chosen by:

1. formal contract completeness
2. runtime readiness
3. actual runtime-validation status

## Practical result

- RP2 and STM32 remain strong generation families, but many current examples are
  blocked by missing bench setup
- ESP32 examples remain usable, but runtime claims must stay conservative while
  the current meter path is unstable
- ADC examples remain deferred for stronger runtime claims until their external
  analog-source contracts are defined

## Recommended next direction

Until more bench setup exists, the best next work is:

- bounded spec/governance improvements
- or more example generation that stays honest about readiness

Not:

- forcing live validation on blocked paths
