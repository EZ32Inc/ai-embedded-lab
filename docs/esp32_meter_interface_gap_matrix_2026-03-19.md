# ESP32 Meter Interface Gap Matrix

Date: 2026-03-19

## Purpose

Compare the desired instrument-interface model for `ESP32-S3 meter` against the
current implementation.

## Current Reference Points

- [ael/instruments/meter_native_api.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/meter_native_api.py)
- [ael/instruments/native_api_dispatch.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/native_api_dispatch.py)
- [configs/instrument_instances/esp32s3_dev_c_meter.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/instrument_instances/esp32s3_dev_c_meter.yaml)

## Matrix

| Area | Desired state | Current state | Gap |
| --- | --- | --- | --- |
| Identity | explicit `instrument_family = esp32_meter` | not explicit in native API payload/profile | moderate |
| Actions | `measure_digital`, `measure_voltage`, `stim_digital` | already present | none |
| Action execution boundary | backend remains owner | already true via `esp32_meter backend` bridge | none |
| Status model | normalized runtime domains | mostly raw reachability payload | moderate |
| Doctor model | subsystem-oriented checks | mostly provision/reachability result | moderate |
| Lifecycle boundary | explicit in profile/docs | partly documented, not encoded in profile | moderate |
| Runtime presentation | more intentional meter family presentation | functional but less modeled | small |

## Main Gap

The main gap is not action coverage.

The main gap is that `meter_native_api` behaves correctly but does not yet
present itself as a fully modeled instrument interface in the same deliberate
way that `ESP32JTAG` now does.

## What Is Already Good

- action surface exists
- runtime consumer path exists
- backend boundary exists
- live evidence exists

## What To Fix First

1. make `instrument_family` explicit
2. define stable status domains
3. define lifecycle ownership in the profile
4. only then adjust runtime presentation text if needed
