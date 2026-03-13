## STM32F103 ADC Loopback Closeout

Status:
- bounded generated-example execution proof

Board / test:
- board: `stm32f103`
- test: `stm32f103_adc_banner`

Control instrument:
- `esp32jtag_stm32_golden @ 192.168.2.98:4242`

Physical wiring:
- keep the normal STM32F103 golden GPIO setup
- add loopback:
  - `PA1 -> PA0`

Signal roles:
- `PA1` = ADC loopback source
- `PA0 / ADC1_IN0` = ADC input
- `PA4` = ADC-validated GPIO status output observed by AEL

Bounded success method:
- firmware drives `PA1`
- firmware samples `PA0`
- firmware mirrors ADC-validated phase result onto `PA4`
- AEL verifies the resulting `PA4` waveform through the existing GPIO capture path

Runtime evidence:
- clean pass:
  - `runs/2026-03-12_20-48-42_stm32f103_stm32f103_adc_banner`
- repeat health:
  - `5/5 PASS`
- repeated observed verify metrics:
  - `edges=25`

What this proves:
- the generated STM32 ADC loopback path runs successfully on real hardware
- the `PA1 -> PA0` loopback wiring works for this bounded test
- ADC result can be exported into a machine-checkable GPIO status signal and verified by AEL

What this does not prove:
- direct ADC sample/value verification by an external analog instrument
- broad ADC framework support
- broad generated-example execution readiness beyond this bounded path

Operational note:
- the observed GPIO frequency should be treated as a coarse verification band, not a precision measurement
