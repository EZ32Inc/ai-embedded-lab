# ESP32-JTAG Acceptance Test Checklist

**Date:** 2026-03-18
**Version:** v0.1
**Status:** Draft

---

## Goal

Determine whether ESP32-JTAG is ready to be declared the AEL **reference instrument**.

---

## A. Structural Checks

- [ ] Code layout follows reference skeleton (`backend.py`, `transport.py`, `actions/`, `errors.py`, `capability.py`)
- [ ] Action files are separated by action type
- [ ] Transport layer is separated from action logic
- [ ] Result normalization layer exists
- [ ] Error normalization layer exists (backend exceptions mapped to IAM error shape)

---

## B. Functional Checks

### flash

- [ ] Valid firmware image can be programmed successfully
- [ ] Success output is structured (IAM-compliant)
- [ ] Failure output is structured (e.g. programming failure, timeout)

### reset

- [ ] Reset executes correctly on real hardware
- [ ] Reset type (hard/soft/line) is explicitly declared
- [ ] Reset result is structured

### gpio_measure

- [ ] Measurement executes correctly on real hardware
- [ ] Output shape matches IAM definition
- [ ] Pass/fail-compatible data is returned

---

## C. Stability Checks

- [ ] Smoke pack passes at least once end-to-end
- [ ] Smoke pack passes 5 consecutive times without intervention
- [ ] Result shape is consistent across all runs (no field differences)
- [ ] No flaky behavior observed

---

## D. Failure Path Checks

- [ ] Device disconnected case: handled and returns structured error
- [ ] Timeout case: handled and returns structured error
- [ ] Invalid parameter case: handled and returns structured error
- [ ] All failure returns are machine-readable (no raw exception dumps as primary result)

---

## E. AI Usability Checks

- [ ] AI agent can select ESP32-JTAG correctly given a relevant task
- [ ] AI agent can invoke actions with correct parameters
- [ ] AI agent can interpret success result correctly
- [ ] AI agent can interpret failure result and recover or escalate appropriately

---

## F. Documentation Checks

- [ ] Packaging plan exists (`esp32_jtag_implementation_plan_v0_1.md`)
- [ ] Action mapping document exists (`esp32_jtag_action_mapping_v0_1.md`)
- [ ] Validation plan exists (`esp32_jtag_validation_plan_v0_1.md`)
- [ ] Backend skeleton document exists (`esp32_jtag_backend_skeleton_v0_1.md`)
- [ ] Instrument authoring guide references this implementation
- [ ] Instrument compatibility matrix updated to reflect reference status

---

## Reference-Ready Decision

ESP32-JTAG may be declared **reference-ready** only when **all sections A through F** are complete.

Once declared reference-ready, it becomes the measuring stick for aligning:
- ST-Link
- USB-UART bridge
- Future instruments
