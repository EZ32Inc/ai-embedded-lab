# Phase B Strategy Boundary

## 1. Logic moved out of `pipeline.py`
- Control-instrument/board/test strategy normalization:
  - control-instrument config normalization
  - board build override shaping from test inputs
  - wiring merge/default requirement shaping
  - timeout resolution
- Step shaping decisions:
  - preflight step enable/shape
  - instrument selftest step enable/shape
  - build step selection (`build.*`)
  - load step selection (`load.gdbmi` vs `load.idf_esptool`) and flash cfg shaping
  - UART observe step enable/shape
  - verify step selection (`check.signal_verify` vs `check.instrument_signature`)
- Instrument-context and meter-digital detection helpers used by verify shaping.

## 2. New module/object introduced
- New module: `ael/strategy_resolver.py`
- New thin output object:
  - `ResolvedRunStrategy` dataclass containing normalized control-instrument config, board config, wiring config, resolved timeout, and banner-level test/instrument fields.
- The resolver module now owns strategy/policy and step-input shaping; it does not execute steps.

Compatibility note:
- some internal field names still use `probe_cfg` for compatibility, but this should not be treated as the preferred architecture vocabulary.

## 3. What remains intentionally in `pipeline.py`
- Top-level orchestration:
  - ingesting CLI/run-request inputs
  - loading configs and writing effective config/meta/result artifacts
  - creating run paths/log initialization
  - building runplan envelope and calling `runner.run_plan(...)`
  - final result synthesis, triage messaging, notifications, exit code mapping

## 4. What was intentionally not changed
- No runner redesign.
- No adapter redesign.
- No CLI command redesign.
- No run-plan schema redesign.
- No evidence/reporting model redesign.
- No broad file moves or package restructuring.

## 5. Known limitations
- `pipeline.py` still contains some policy-adjacent behavior (for example, local triage/exit-code mapping and no-build early-fail handling) because these are tightly coupled to top-level run UX and compatibility.
- Resolver output is intentionally small and does not yet represent a full typed run-plan model.
- Some strategy policy still depends on current config shape conventions; a future phase can formalize policy schema.
