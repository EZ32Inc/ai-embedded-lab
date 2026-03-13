# STM32F103 SPI Self-Check v0.1

Purpose:
- define the next bounded capability demo on the unified `stm32f103` fixture
- add one real SPI execution proof without changing family, instrument roles, or external observe method

## Design verdict

The current unified STM32F103 fixture is sufficient for a bounded SPI self-check.

The intended model is:
- `PA5 = SPI1_SCK`
- `PA7 = SPI1_MOSI`
- `PA6 = SPI1_MISO`
- loopback:
  - `PA7 -> PA6`
- firmware performs the SPI self-check internally
- firmware exports SPI pass/fail onto `PA4`
- AEL verifies `PA4` through the existing external observe path

This keeps:
- the current control instrument unchanged:
  - `esp32jtag_stm32_golden @ 192.168.2.98:4242`
- the current external observe path unchanged:
  - `PA4 -> P0.0`
- the current board/family unchanged:
  - `stm32f103`

## Accepted fixture assumptions

### Existing preserved wiring
- `PA4 -> P0.0`
- optional:
  - `PA5 -> P0.1`
- `PA1 -> PA0`
- `PA9 -> PA10`
- `PA8 -> PB8`
- `PC13 -> LED`
- `GND -> probe GND`

### New wiring required for this SPI demo
- `PA7 -> PA6`

### Important wiring rule
- `PA5/PA6/PA7` are treated as SPI-internal self-check wiring only
- `PA4` remains the only required external machine-checkable result line
- `PA5 -> P0.1` may be kept only as an auxiliary observe point, not as the main pass/fail proof

## Bounded success method

Firmware should:
1. configure SPI1 in a bounded master-loopback mode
2. clock a small fixed byte pattern out on `PA7`
3. read it back on `PA6`
4. decide pass/fail internally
5. encode pass/fail on `PA4`

Recommended bounded encoding:
- SPI-good:
  - `PA4` emits a stable square-wave status pattern in a known good band
- SPI-bad:
  - `PA4` stays low or emits a clearly distinct bad pattern

The exact waveform can be chosen during implementation, but it must be:
- machine-checkable
- distinct from the current ADC-good pattern
- stable enough for the existing external capture path

## Likely failure modes
- `PA7 -> PA6` loopback missing or loose
- wrong SPI pin configuration
- CPOL/CPHA mismatch from overcomplicated setup
- firmware passes data incorrectly but still toggles `PA4` if pass/fail encoding is careless
- hidden interference if SPI implementation tries to treat `PA5/PA6/PA7` as external proof pins rather than internal self-check pins

## New execution value

This path adds:
- first bounded STM32 SPI execution proof
- third distinct generated capability proof on the STM32 anchor after:
  - UART
  - ADC

It does so with:
- no new family setup
- no new instrument role
- minimal additional wiring

## Regression framing

- change class:
  - Class 3: bounded path-specific runtime change
- affected anchor:
  - primary sample-board capability anchor (`stm32f103`)
- minimum regression tier:
  - Tier 4: sample-board capability baseline

## Exact validation commands

Formal pre-checks:
```bash
python3 -m ael inventory describe-test --board stm32f103 --test tests/plans/stm32f103_spi_banner.json
python3 -m ael explain-stage --board stm32f103 --test tests/plans/stm32f103_spi_banner.json --stage plan
```

Build/path validation:
```bash
PYTHONPATH=. pytest tests/test_inventory.py tests/test_connection_metadata.py
```

Bounded live proof:
```bash
python3 -m ael run --board stm32f103 --test tests/plans/stm32f103_spi_banner.json
```

Only if shared runtime/default-verification code is touched:
```bash
python3 -m ael verify-default run
```

## Non-goals

This bounded SPI demo should not:
- become a general SPI framework
- add protocol analysis features
- add a new family
- broaden into general multi-instrument support
- make `PA5/PA6/PA7` direct external proof lines

## Batch 1 outcome

Batch 1 is complete when:
- the unified fixture assumptions are correct
- the SPI loopback wiring is explicit
- the bounded success method is explicit
- the regression framing is explicit
- the next implementation batch can proceed without reopening connection design
