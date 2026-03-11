# AEL Additional To Do List v0.21
## New Instrument Generation Check

## Purpose

This memo captures an additional important next-step direction for AEL:

- generate a new instrument using the current instrument model and workflow
- validate that the current instrument architecture is not only good for existing instruments, but also good for adding new ones
- use a simple, common, high-value instrument as the first generation example

This is not only about adding one more instrument.
It is also about checking whether the current AEL instrument-generation path really works.

---

## Why This Matters

AEL has already made strong progress on:

- instrument model
- control-instrument terminology
- runtime contracts
- reporting and diagnostics
- compatibility cleanup
- existing instrument integration

The next logical check is:

> Can AEL now support creation of a new instrument in a clean, repeatable way?

If yes, that is strong evidence that the instrument architecture is truly mature.

---

## Proposed First Example

### USB-to-UART Bridge Instrument

Use a USB-to-UART bridge as the first new generated instrument example.

Why this is a strong candidate:

- simple
- extremely common
- directly useful
- low conceptual complexity
- strongly connected to upcoming UART example expansion
- likely to be valuable to a very large percentage of users

This should be treated as the first practical “new instrument generation” example.

---

## Main Goals

### Goal 1
Validate that AEL can add a new instrument through the current model, not through ad hoc special-case work.

### Goal 2
Create a reusable instrument pattern for a UART-related external instrument.

### Goal 3
Support future UART example expansion on mature board families.

### Goal 4
Capture any workflow/skills that emerge while generating and validating this instrument.

---

## Questions To Answer

This work should clarify:

- What is the current canonical path for adding a new instrument?
- What files and contracts are required?
- How much of the work is reusable vs instrument-specific?
- Are the current instrument interfaces sufficient?
- Does the new instrument fit naturally into current inventory / explain / run / diagnostics flows?
- What skills/workflow notes should be captured from the process?

---

## Suggested Scope

Initial scope should stay bounded.

### In scope
- define a USB-to-UART bridge instrument example
- integrate it into the current instrument model
- make it selectable and visible in the expected surfaces
- validate that it can participate in a realistic UART-related path
- capture any missing instrument-generation guidance

### Out of scope for the first pass
- broad redesign of the instrument model
- large new automation framework
- supporting every UART bridge variant at once
- over-generalizing before one practical example is working

---

## Expected Outputs

Possible outputs from this work:

- a new instrument definition/example
- any required runtime/config integration
- validation notes
- one or more workflow/skills docs
- refined instrument-generation guidance if gaps are found

---

## Likely Skills / Workflow Notes

Examples of skills that may emerge:

- new instrument generation workflow
- USB-to-UART bridge instrument integration notes
- UART instrument validation workflow
- instrument selection / diagnostics guidance for serial bridge devices

These should only be added if grounded in actual recurring work.

---

## Recommended Working Principle

This work should follow the established AEL method:

**architecture → roadmap → tasks → review → update architecture → update roadmap → tasks → review again**

For this specific direction:

1. review the current instrument-generation path
2. define the USB-to-UART bridge example as a bounded instrument-generation batch
3. implement and validate it
4. review whether the current instrument architecture handled it cleanly
5. capture any missing rules/skills
6. only then decide whether deeper instrument-generation work is needed

---

## Suggested Next Action

Ask Codex to:

1. review the current repo for the cleanest path to add a new instrument
2. treat USB-to-UART bridge as the first bounded new instrument example
3. identify what can be reused from the current instrument architecture
4. identify what is missing
5. propose the first implementation batch
