# ESP32 Meter Minimal Interface Spec

Date: 2026-03-19

## Purpose

Define the minimum follow-up spec needed to make `ESP32-S3 meter` feel like a
first-class instrument interface, without reopening the backend migration work.

## Identity Payload

Recommended minimum fields:

```json
{
  "device_id": "esp32s3_dev_c_meter",
  "device_type": "measurement_and_stimulus_instrument",
  "instrument_family": "esp32_meter",
  "instrument_role": "external_instrument",
  "model": "ESP32-S3 Dev C Meter",
  "protocol_version": "ael.local_instrument.native_api.v0.1",
  "endpoint": "192.168.4.1:9000"
}
```

## Capability Payload

Recommended minimum shape:

```json
{
  "protocol_version": "ael.local_instrument.native_api.v0.1",
  "capability_families": {
    "digital_measurement": ["measure_digital"],
    "voltage_measurement": ["measure_voltage"],
    "digital_stimulation": ["stim_digital"]
  }
}
```

## Status Payload

Recommended minimum domains:

- `network`
- `meter_service`
- `measurement_surface`
- `stimulation_surface`

This does not need to mirror `ESP32JTAG` domains exactly.

## Doctor Payload

Recommended minimum checks:

- reachability
- API responsiveness
- whether core meter actions are expected to be usable

## Lifecycle Boundary

Recommended profile-level declaration:

- owned by native API:
  - identify
  - capabilities
  - status
  - doctor
  - measure/stim action entrypoints
- owned by backend:
  - action execution details
- out of scope:
  - provisioning orchestration
  - Wi-Fi onboarding flow
  - firmware update/reflash lifecycle

## Transition Note

The correct next phase is:

1. clarify interface model
2. normalize payloads
3. keep backend ownership stable

Not:

1. rewrite backend
2. move provision into backend
3. force `ESP32 meter` to look exactly like `ESP32JTAG`
