# AEL Core v0.1 Boundary Check: Core Contamination Scan

## Scope
Scanned Core files only:
- `orchestrator.py`
- `ael/__main__.py`
- `ael/run_manager.py`
- `ael/instruments/*`

Keywords (case-insensitive):
- `idf.py`, `esptool`, `openocd`, `stlink`, `wchlink`, `gdb`, `bmda`
- `esp32`, `stm32`, `rp2040`, `pico`, `ch32v`
- GPIO pin names (`PA*`, `PB*`, `PC*`, `GPIO*`) when hard-coded in Core

## Findings

| File | Line(s) | Matched keyword | Snippet | Risk | Recommendation |
|---|---:|---|---|---|---|
| `ael/__main__.py` | 27 | `esp32` | `--probe` default `configs/esp32jtag.yaml` | High | Move default probe selection to board config / pack config policy layer. |
| `ael/__main__.py` | 35 | `esp32` | doctor default probe `configs/esp32jtag.yaml` | High | Make doctor require explicit probe or resolve from board profile. |
| `ael/__main__.py` | 36 | `rp2040`, `pico` | doctor default board `configs/boards/rp2040_pico.yaml` | High | Remove board-specific default from Core CLI; resolve from test/pack metadata. |
| `ael/__main__.py` | 69-70 | `esp32` | `probe_default=esp32jtag.yaml`, `notify_probe=esp32jtag_notify.yaml` | High | Externalize probe policy into configs. |
| `ael/__main__.py` | 136-139 | `esp32` | special-case `board_id == "esp32s3_devkit"` to switch probe file | High | Move board-special routing into adapter/profile config. |
| `ael/__main__.py` | 513-514 | `esp32` | pack defaults `esp32jtag_notify.yaml` and `esp32jtag.yaml` | High | Replace with board capability mapping in config. |
| `ael/__main__.py` | 564-565 | `esp32` | pack special-case `pack_board == "esp32s3_devkit"` | High | Move into board manifest/policy resolver. |
| `orchestrator.py` | 11-20 | `stm32`, `bmda`, `esp32` | imports concrete adapters: `build_stm32`, `flash_bmda_gdbmi`, `esp32s3_dev_c_meter_tcp` | High | Introduce adapter registry/interface; avoid concrete board/tool module imports in Core. |
| `orchestrator.py` | 98 | `gdb` | fallback `cfg["gdb_cmd"] = "gdb-multiarch"` | Medium | Put tool defaults in probe config, not Core. |
| `orchestrator.py` | 166-168 | `stm32`, `pico` | `_default_firmware_path`: `stm32f103_app.elf` else `pico_blink.elf` | High | Move artifact naming/path logic into board build adapters. |
| `orchestrator.py` | 216-218 | `gdb`, `esp32` | preflight hints mention `ESP32JTAG GDB server` | Medium | Generalize hints or move probe-specific hints to probe adapter. |
| `orchestrator.py` | 223 | `pico` | build hint: `check pico-sdk path` | Medium | Move board/tool-specific triage messages to adapters. |
| `orchestrator.py` | 293-299 | `esp32` | `_is_meter_digital_verify_test` hard-codes `esp32s3_dev_c_meter` | High | Use capability-based dispatch (`measure.digital`) via instrument registry. |
| `orchestrator.py` | 307-309 | `esp32` | rejects non-`esp32s3_dev_c_meter` for meter verify | High | Replace with generic instrument capability resolution. |
| `orchestrator.py` | 349 | `esp32` | direct call `esp32s3_dev_c_meter_tcp.measure_digital` | High | Route through generic instrument adapter interface. |
| `orchestrator.py` | 445 | `esp32` | direct call `esp32s3_dev_c_meter_tcp.measure_voltage` | High | Same as above: abstract to capability call. |
| `orchestrator.py` | 494 | `esp32` | verify payload `instrument_id: "esp32s3_dev_c_meter"` | Medium | Emit runtime-selected instrument id, not hard-coded value. |
| `orchestrator.py` | 526-527 | `esp32` | selftest path gated by `instrument_id != "esp32s3_dev_c_meter"` | High | Use manifest `selftest` capability regardless of concrete id. |
| `orchestrator.py` | 547-553 | `GPIO*` (hard-coded pin semantics) | selftest defaults: `out_gpio=15`, `in_gpio=11`, `adc_out=16`, `adc_in=4` | High | Move pin defaults fully to instrument manifest/config; Core should not own pin numbers. |
| `orchestrator.py` | 846-847 | `stm32` | build branch `target.startswith("stm32")` -> `build_stm32.run` | High | Replace with adapter selection from board `build.type` only. |
| `orchestrator.py` | 896 | `esptool` | branch `method == "idf_esptool"` | Medium | Keep method selection config-driven; avoid tool-name constants in Core logic. |
| `orchestrator.py` | 913 | `bmda`, `gdb` | direct fallback `flash_bmda_gdbmi.run(...)` | High | Flash strategy should be adapter-registered by board/probe profile. |
| `ael/__main__.py` | 377 | `gdb` | doctor checks `arm-none-eabi-gdb` directly | Medium | Move tool checks to probe/board-specific health checks. |

## Core Files With No Contamination Hits
- `ael/run_manager.py`: no board/tool-specific strings found.
- `ael/instruments/discovery.py`, `ael/instruments/manifest.py`, `ael/instruments/registry.py`: no board-specific leakage found; these are generic registry/manifest utilities.

## GPIO Hard-Coded Pattern Result
- No hard-coded `PA*`, `PB*`, `PC*`, or explicit `GPIOxx` identifiers were found in Core.
- However, numeric GPIO defaults are hard-coded in Core selftest logic (`orchestrator.py:547-553`), which is still boundary leakage.

## Top 10 Highest-Risk Leaks (Ranked)
1. `orchestrator.py:11-20` concrete adapter imports (`build_stm32`, `flash_bmda_gdbmi`, `esp32s3_dev_c_meter_tcp`)  
   Recommendation: move to adapter registry/plugin mapping.
2. `orchestrator.py:293-309` hard-coded instrument id `esp32s3_dev_c_meter` in test type detection and dispatch  
   Recommendation: capability-based routing via manifest.
3. `orchestrator.py:349,445` direct concrete meter adapter calls  
   Recommendation: abstract behind `measure.digital` / `measure.voltage` adapter interface.
4. `orchestrator.py:526-527` selftest limited to one instrument id  
   Recommendation: use manifest selftest capability across instruments.
5. `orchestrator.py:547-553` hard-coded instrument pin defaults in Core  
   Recommendation: move to instrument manifest/config only.
6. `orchestrator.py:166-168` board-specific fallback firmware path (`stm32f103_app.elf`, `pico_blink.elf`)  
   Recommendation: build adapter returns artifact path; no Core fallback names.
7. `orchestrator.py:846-847` target-prefix branch for STM32 build path  
   Recommendation: resolve builder from `board.build.type` only.
8. `orchestrator.py:913` BMDA/GDBMI flash fallback hardwired in Core  
   Recommendation: flash adapter selected by config/registry.
9. `ael/__main__.py:136-139,564-565` explicit `esp32s3_devkit` CLI special-casing  
   Recommendation: move to board/probe profile rules.
10. `ael/__main__.py:27,35,69-70,513-514` esp32jtag probe defaults in Core CLI  
    Recommendation: move defaults to config resolver and require explicit profile selection.

## Overall Recommendation
**Core is currently contaminated with board/tool/instrument specifics (especially in `orchestrator.py` and `ael/__main__.py`).**

Suggested boundary cleanup direction:
- Keep Core limited to: run state machine, artifact bookkeeping, generic capability dispatch.
- Move board/tool specifics to: `configs/boards/*`, `configs/probes/*`, `adapters/*`, and instrument manifests.
- Introduce adapter registries for build/flash/observe/instrument capabilities to remove direct imports and string-based board/tool switches from Core.
