# Skill: Example Generation Build Isolation

## Purpose

This note captures a key rule discovered during cross-family example generation work:

Generated examples must not collide with default/golden target build artifacts.

This is especially important when:
- a board already has a default/golden validation path
- new generated examples are added for the same family or board
- build systems such as CMake reuse cached build directories

---

## Problem

A real regression occurred when a generated RP2040 UART example reused a generic build directory that was also implicitly used by the default RP2040 golden path.

This caused:
- wrong CMake cache reuse
- source/build mismatch
- failure in default verification
- regression in a path unrelated to the new example itself

The problem was not bench-side instability.
It was a build/artifact isolation gap.

---

## Root Cause

The default RP2040 golden path did not have explicit build metadata.
It relied on a generic shared build directory.

When the generated UART example populated that directory with a different source tree, the default path inherited the wrong cache.

This created an unintended collision between:
- golden/default build path
- generated example build path

---

## Rule

Generated examples must not share build/artifact state with default/golden paths unless that sharing is explicitly intended and safe.

In practice:

- default/golden paths should have explicit build metadata when needed
- generated examples should use distinct build directories
- artifact stems should be explicit enough to avoid ambiguity
- generic shared build paths should not silently bind multiple unrelated sources

---

## Practical Review Checklist

When adding a generated example, review:

1. Does the board’s default/golden path have explicit build metadata?
2. Does the new example have its own build directory?
3. Does the new example have a unique artifact stem?
4. Can the example accidentally populate a cache used by a default/golden path?
5. After the new example is added, does `verify-default run` still pass?

---

## Recommended Validation

For example-generation batches, do not stop at:
- describe-test
- explain-stage
- build smoke

Also check:
- whether default/golden paths remain isolated
- whether a live `python3 -m ael verify-default run` still passes when runtime/build behavior could be affected

---

## Fix Pattern

When a collision is found, prefer:
- explicit board-level build metadata
- explicit example-level build metadata
- dedicated build directories
- clear artifact naming

Avoid:
- relying on generic shared build directories
- fixing the problem only by cleaning caches manually
- treating the issue as transient if the real cause is path collision

---

## Example Case

RP2040 default golden path:
- needed explicit:
  - `project_dir`
  - `artifact_stem`
  - `build_dir`

This isolated the golden path from the generated UART example path and restored green default verification.

---

## Why This Matters

Example generation is not only about adding new examples.

It also stress-tests:
- artifact policy
- build isolation
- default/golden path robustness
- family-specific generation boundaries

This should be treated as a normal part of example-expansion review.

---

## Rule For Future Work

For future generated examples:

> Example generation review must include build/artifact isolation review.

This should become part of the reusable workflow for:
- UART example expansion
- ADC example expansion
- SPI example expansion
- future family expansion work

