# ESP32 Family Target Skill Metadata Example

```yaml
skill_id: skill.target_expansion.esp32.from_reference.v0_1
name: add_esp32_family_target_from_reference
type: target_expansion
family: esp32
target: esp32c6_devkit
capability: gpio_signature_plus_uart
version: 0.1.0
status: candidate
reference_target: esp32s3_devkit
created_from:
  report: docs/esp32c6_phase1_extension_report.md
  prompt: /nvme1t/work/1/prompt_23.txt
last_validated:
  date: 2026-03-07
  method: static_structure_only
related_reports:
  - docs/esp32c6_phase1_extension_report.md
known_good_evidence:
  - configs/boards/esp32c6_devkit.yaml
  - tests/plans/esp32c6_gpio_signature.json
  - tests/plans/esp32c6_gpio_signature_with_meter.json
known_pitfalls:
  - target-specific hardcoded build artifact names
  - placeholder AP SSID may not match final instrument naming
fallback_to:
  - esp32s3_devkit
supersedes: null
```
