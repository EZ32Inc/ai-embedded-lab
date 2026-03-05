# AEL Core v0.1 Boundary Check: Core Contamination Scan

## Scope
Scanned Core-adjacent files:
- `ael/orchestrator.py`
- `ael/__main__.py`
- `ael/adapter_registry.py`
- `ael/run_manager.py`
- `ael/instruments/*`

Keywords (case-insensitive):
- tool names: `idf.py`, `esptool`, `openocd`, `stlink`, `wchlink`, `gdb`, `bmda`
- board/family names: `esp32`, `stm32`, `rp2040`, `pico`, `ch32v`
- hard-coded pin naming (`PA*`, `PB*`, `PC*`, `GPIO*`) in Core paths

## Findings (Current)

| File | Area | Current status | Risk | Recommendation |
|---|---|---|---|---|
| `ael/orchestrator.py` | concrete adapter imports | **Resolved** | Low | Keep orchestration via runner + adapter step types only. |
| `ael/orchestrator.py` | meter selftest/verify direct calls | **Resolved** | Low | Keep instrument ops in adapter layer (`check.instrument_*`). |
| `ael/orchestrator.py` | hard-coded instrument id in verify payload | **Resolved** | Low | Keep runtime instrument id from resolved context. |
| `ael/orchestrator.py` | flash method branch (`idf_esptool` vs `gdbmi`) | Remaining | Medium | Move strategy selection fully to board/flash adapter policy (config-driven dispatch only). |
| `ael/__main__.py` | board/probe defaults (`esp32jtag`, `rp2040_pico`) | Remaining | Medium | Shift defaults into resolver policy and make CLI defaults generic/empty where possible. |
| `ael/adapter_registry.py` | concrete instrument adapter (`esp32s3_dev_c_meter_tcp`) | Remaining | High | Introduce capability plugin registry for instrument adapters. |
| `ael/adapter_registry.py` | concrete build/flash adapter modules | Remaining | Medium | Keep board `build.type`/`flash.method` config-driven and move module mapping to plugin table. |
| `ael/run_manager.py` | board/tool-specific logic | None found | Low | No action required. |
| `ael/instruments/*` | board/tool-specific logic | None found | Low | No action required. |

## GPIO Hard-Coded Pattern Result
- No hard-coded `PA*`, `PB*`, `PC*`, `GPIOxx` symbols found in core paths.
- Numeric default pins for instrument selftest are now sourced through instrument selftest inputs/manifests in adapter flow.

## Delta Since Previous Report
- Removed from `ael/orchestrator.py`:
  - concrete `esp32s3_dev_c_meter_tcp` execution paths
  - large meter/selftest imperative block
  - hard-coded verify payload instrument id
- Added adapter-layer artifact hint helper:
  - `ael/adapters/build_artifacts.py`
- Remaining highest-risk leakage is now concentrated in `ael/adapter_registry.py` (capability dispatch still concrete-module based).

## Top Priorities (Next)
1. Capability plugin dispatch in `ael/adapter_registry.py` for instrument operations.
2. Move flash/build method-to-module mapping behind registry/config plugin table.
3. Reduce `ael/__main__.py` board/probe defaults by resolver policy.

## Overall Recommendation
Core orchestration is significantly cleaner now. The next boundary win is to make adapter dispatch capability-driven in `ael/adapter_registry.py` so concrete instrument modules are no longer hardwired.
