## STM32F103 ADC Loopback Health Note

Date:
- 2026-03-12

Test:
- `stm32f103_adc_banner`

Setup:
- board: `stm32f103`
- control instrument: `esp32jtag_stm32_golden @ 192.168.2.98:4242`
- loopback wiring:
  - `PA1 -> PA0`
  - `PA0 = ADC1_IN0`
  - `PA1 = ADC loopback source`

Verification shape:
- firmware drives `PA1`
- firmware samples `PA0`
- firmware mirrors ADC-validated phase result onto `PA4`
- AEL verifies the resulting `PA4` waveform through the existing GPIO capture path

Repeat result:
- `5/5 PASS`

Observed verify metrics:
- Run 1: `edges=25`, `high=32962`, `low=32570`
- Run 2: `edges=25`, `high=33716`, `low=31816`
- Run 3: `edges=25`, `high=33928`, `low=31604`
- Run 4: `edges=25`, `high=32422`, `low=33110`
- Run 5: `edges=25`, `high=32139`, `low=33393`

Interpretation:
- the bounded STM32 ADC loopback path is repeatably runnable
- `PA4` is stable enough as a machine-checkable GPIO-only ADC-derived status signal
- the observed PA4 frequency should be treated as a coarse band, not a precision measurement

What this proves:
- the firmware-side ADC loopback logic is stable enough for bounded repeated execution
- AEL can verify the ADC-derived status signal automatically through the control instrument

What this does not prove:
- direct ADC sample/value verification by an external analog instrument
- broad ADC framework support
