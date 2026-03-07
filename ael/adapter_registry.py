from __future__ import annotations

import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Tuple

from ael.adapters import (
    build_cmake,
    build_idf,
    build_stm32,
    flash_bmda_gdbmi,
    flash_idf,
    instrument_aip_http,
    instrument_sim_http,
    observe_gpio_pin,
    observe_uart_log,
    preflight,
)
from ael import run_manager
from ael import evidence as ael_evidence
from ael import failure_recovery
from ael.verification import la_verify


class _InstrumentBackend:
    capabilities = frozenset()

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities

    def selftest(self, cfg, params, out_path):
        raise NotImplementedError

    def measure_digital(self, cfg, pins, duration_ms, out_path):
        raise NotImplementedError

    def measure_voltage(self, cfg, gpio, avg, out_path):
        raise NotImplementedError


class _Esp32MeterTcpBackend(_InstrumentBackend):
    capabilities = frozenset({"selftest", "measure.digital", "measure.voltage"})

    def __init__(self):
        from ael.adapters import esp32s3_dev_c_meter_tcp

        self._impl = esp32s3_dev_c_meter_tcp

    def selftest(self, cfg, params, out_path):
        return self._impl.selftest(
            cfg,
            out_gpio=int(params.get("out_gpio", 15)),
            in_gpio=int(params.get("in_gpio", 11)),
            adc_out=int(params.get("adc_out", 16)),
            adc_in=int(params.get("adc_in", 4)),
            dur_ms=int(params.get("dur_ms", 200)),
            freq_hz=int(params.get("freq_hz", 1000)),
            avg=int(params.get("avg", 16)),
            settle_ms=int(params.get("settle_ms", 20)),
            out_path=out_path,
        )

    def measure_digital(self, cfg, pins, duration_ms, out_path):
        return self._impl.measure_digital(cfg, pins=pins, duration_ms=duration_ms, out_path=out_path)

    def measure_voltage(self, cfg, gpio, avg, out_path):
        return self._impl.measure_voltage(cfg, gpio=gpio, avg=avg, out_path=out_path)


class _InstrumentBackendRegistry:
    def __init__(self):
        meter_backend = _Esp32MeterTcpBackend()
        self._default_backend = meter_backend
        self._by_id = {
            "esp32s3_dev_c_meter": meter_backend,
        }

    def resolve(self, instrument_id: str | None, capability: str):
        key = str(instrument_id or "").strip()
        if key:
            backend = self._by_id.get(key)
            if backend is None:
                raise KeyError(f"instrument backend not found for id: {key}")
            if not backend.supports(capability):
                raise KeyError(f"instrument backend for {key} does not support capability: {capability}")
            return backend
        # Temporary compatibility fallback for legacy plans that omit instrument_id.
        if not self._default_backend.supports(capability):
            raise KeyError(f"default instrument backend does not support capability: {capability}")
        return self._default_backend


@contextmanager
def _tee_output(log_path: str, output_mode: str):
    tee, f = run_manager.open_tee(Path(log_path), output_mode)
    import sys

    orig_out = sys.stdout
    orig_err = sys.stderr
    sys.stdout = tee
    sys.stderr = tee
    try:
        yield
    finally:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        sys.stdout = orig_out
        sys.stderr = orig_err
        f.close()


def _write_json(path: str, payload: Dict[str, Any]):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _runtime_state_path(ctx) -> Path:
    return Path(ctx.artifacts_dir) / "runtime_state.json"


def _load_runtime_state(ctx) -> Dict[str, Any]:
    p = _runtime_state_path(ctx)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_runtime_state(ctx, data: Dict[str, Any]) -> None:
    p = _runtime_state_path(ctx)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _extract_voltage_v(payload):
    if not isinstance(payload, dict):
        return None
    for key in ("voltage_v", "v", "value_v", "voltage", "value"):
        val = payload.get(key)
        if isinstance(val, (int, float)):
            f = float(val)
            if f > 10.0:
                return f / 1000.0
            return f
    mv = payload.get("mv")
    if isinstance(mv, (int, float)):
        return float(mv) / 1000.0
    nested = payload.get("result")
    if isinstance(nested, dict):
        return _extract_voltage_v(nested)
    return None


class _PreflightAdapter:
    def execute(self, step, plan, ctx):
        inputs = step.get("inputs", {}) if isinstance(step, dict) else {}
        probe_cfg = inputs.get("probe_cfg", {})
        out_json = inputs.get("out_json")
        output_mode = inputs.get("output_mode", "normal")
        log_path = inputs.get("log_path")
        if log_path:
            with _tee_output(log_path, output_mode):
                ok, info = preflight.run(probe_cfg)
        else:
            ok, info = preflight.run(probe_cfg)
        if out_json:
            _write_json(out_json, info or {})
        if not ok:
            return {"ok": False, "error_summary": "preflight failed", "result": info or {}}
        return {"ok": True, "result": info or {}}


class _BuildAdapter:
    def __init__(self, kind: str):
        self.kind = kind

    def execute(self, step, plan, ctx):
        inputs = step.get("inputs", {}) if isinstance(step, dict) else {}
        board_cfg = inputs.get("board_cfg", {})
        output_mode = inputs.get("output_mode", "normal")
        log_path = inputs.get("log_path")
        if log_path:
            with _tee_output(log_path, output_mode):
                if self.kind == "idf":
                    firmware_path = build_idf.run(board_cfg)
                elif self.kind == "arm_debug":
                    firmware_path = build_stm32.run(board_cfg)
                else:
                    firmware_path = build_cmake.run(board_cfg)
        else:
            if self.kind == "idf":
                firmware_path = build_idf.run(board_cfg)
            elif self.kind == "arm_debug":
                firmware_path = build_stm32.run(board_cfg)
            else:
                firmware_path = build_cmake.run(board_cfg)
        if not firmware_path:
            return {"ok": False, "error_summary": "build failed"}
        state = _load_runtime_state(ctx)
        state["firmware_path"] = str(firmware_path)
        _save_runtime_state(ctx, state)
        return {"ok": True, "firmware_path": str(firmware_path)}


class _LoadAdapter:
    def __init__(self, method: str):
        self.method = method

    def execute(self, step, plan, ctx):
        inputs = step.get("inputs", {}) if isinstance(step, dict) else {}
        probe_cfg = inputs.get("probe_cfg", {})
        firmware_path = inputs.get("firmware_path")
        flash_cfg = inputs.get("flash_cfg", {})
        flash_json_path = inputs.get("flash_json_path")
        output_mode = inputs.get("output_mode", "normal")
        log_path = inputs.get("log_path")
        if not firmware_path:
            state = _load_runtime_state(ctx)
            firmware_path = state.get("firmware_path")
        if not firmware_path:
            return {"ok": False, "error_summary": "missing firmware path"}
        if log_path:
            with _tee_output(log_path, output_mode):
                if self.method == "idf_esptool":
                    ok = flash_idf.run(probe_cfg, firmware_path, flash_cfg=flash_cfg, flash_json_path=flash_json_path)
                else:
                    ok = flash_bmda_gdbmi.run(probe_cfg, firmware_path, flash_cfg=flash_cfg, flash_json_path=flash_json_path)
        else:
            if self.method == "idf_esptool":
                ok = flash_idf.run(probe_cfg, firmware_path, flash_cfg=flash_cfg, flash_json_path=flash_json_path)
            else:
                ok = flash_bmda_gdbmi.run(probe_cfg, firmware_path, flash_cfg=flash_cfg, flash_json_path=flash_json_path)
        if not ok:
            return {"ok": False, "error_summary": "load failed"}
        return {"ok": True}


class _UartCheckAdapter:
    def execute(self, step, plan, ctx):
        inputs = step.get("inputs", {}) if isinstance(step, dict) else {}
        cfg = dict(inputs.get("observe_uart_cfg", {}))
        raw_log_path = inputs.get("raw_log_path")
        out_json = inputs.get("out_json")
        flash_json_path = inputs.get("flash_json_path")
        output_mode = inputs.get("output_mode", "normal")
        log_path = inputs.get("log_path")
        if not raw_log_path or not out_json:
            return {"ok": False, "error_summary": "uart output paths missing"}
        if not cfg.get("port") and flash_json_path:
            try:
                flash_payload = json.loads(Path(flash_json_path).read_text(encoding="utf-8"))
                if flash_payload.get("port"):
                    cfg["port"] = flash_payload.get("port")
            except Exception:
                pass
        if log_path:
            with _tee_output(log_path, output_mode):
                uart_result = observe_uart_log.run(cfg, raw_log_path=raw_log_path)
        else:
            uart_result = observe_uart_log.run(cfg, raw_log_path=raw_log_path)
        _write_json(out_json, uart_result)
        error_summary = uart_result.get("error_summary") or "uart observe failed"
        err_l = str(error_summary).lower()
        if any(t in err_l for t in ("permission", "port not found", "failed to open", "cannot open", "could not open")):
            failure_kind = failure_recovery.FAILURE_TRANSPORT_ERROR
        elif bool(uart_result.get("download_mode_detected")):
            failure_kind = failure_recovery.FAILURE_VERIFICATION_MISS
        else:
            failure_kind = failure_recovery.FAILURE_VERIFICATION_MISMATCH
        recovery_hint = None
        if bool(uart_result.get("download_mode_detected")):
            recovery_hint = failure_recovery.make_recovery_hint(
                kind=failure_kind,
                recoverable=True,
                preferred_action="reset.serial",
                reason="uart download mode detected",
                params={"port": cfg.get("port"), "baud": cfg.get("baud", 115200)},
            )
        evidence_item = ael_evidence.make_item(
            kind="uart.verify",
            source="check.uart_log",
            ok=uart_result.get("ok", False),
            summary=(uart_result.get("error_summary") or "uart capture validated"),
            facts={
                "bytes": uart_result.get("bytes"),
                "lines": uart_result.get("lines"),
                "crash_detected": uart_result.get("crash_detected"),
                "missing_expect": uart_result.get("missing_expect", []),
                "forbid_matched": uart_result.get("forbid_matched", []),
                "failure_kind": failure_kind if not bool(uart_result.get("ok", False)) else "",
                "recovery_hint": recovery_hint if isinstance(recovery_hint, dict) else {},
            },
            artifacts={
                "uart_observe_json": out_json,
                "uart_raw_log": raw_log_path,
            },
        )
        if not bool(uart_result.get("ok", False)):
            return {
                "ok": False,
                "error_summary": error_summary,
                "failure_kind": failure_kind,
                "result": uart_result,
                "evidence": [evidence_item],
                "recovery_hint": recovery_hint,
            }
        return {"ok": True, "result": uart_result, "evidence": [evidence_item]}


class _InstrumentSelftestAdapter:
    def __init__(self, backend_registry: _InstrumentBackendRegistry):
        self._backend_registry = backend_registry

    def execute(self, step, plan, ctx):
        inputs = step.get("inputs", {}) if isinstance(step, dict) else {}
        instrument_id = inputs.get("instrument_id")
        cfg = inputs.get("cfg", {})
        params = inputs.get("params", {})
        out_path = inputs.get("out_path")
        if not out_path:
            return {"ok": False, "error_summary": "selftest output path missing"}
        try:
            backend = self._backend_registry.resolve(instrument_id, "selftest")
            payload = backend.selftest(cfg=cfg, params=params, out_path=out_path)
        except KeyError as exc:
            return {"ok": False, "error_summary": str(exc)}
        except Exception as exc:
            return {"ok": False, "error_summary": str(exc)}
        evidence_item = ael_evidence.make_item(
            kind="instrument.selftest",
            source="check.instrument_selftest",
            ok=payload.get("pass", False),
            summary=(payload.get("error") or "instrument selftest passed"),
            facts={
                "instrument_id": instrument_id,
                "host": cfg.get("host"),
                "port": cfg.get("port"),
                "pass": payload.get("pass", False),
            },
            artifacts={"instrument_selftest_json": out_path},
        )
        if not bool(payload.get("pass", False)):
            return {
                "ok": False,
                "error_summary": payload.get("error", "instrument selftest failed"),
                "evidence": [evidence_item],
            }
        return {"ok": True, "result": payload, "evidence": [evidence_item]}


class _InstrumentSignatureAdapter:
    def __init__(self, backend_registry: _InstrumentBackendRegistry):
        self._backend_registry = backend_registry

    def execute(self, step, plan, ctx):
        inputs = step.get("inputs", {}) if isinstance(step, dict) else {}
        instrument_id = inputs.get("instrument_id")
        cfg = inputs.get("cfg", {})
        links = inputs.get("links", [])
        analog_links = inputs.get("analog_links", [])
        duration_ms = int(inputs.get("duration_ms", 500))
        digital_out = inputs.get("digital_out")
        verify_out = inputs.get("verify_out")
        analog_out = inputs.get("analog_out")
        if not digital_out or not verify_out:
            return {"ok": False, "error_summary": "instrument output paths missing"}

        pins = []
        expected_by_gpio = {}
        for item in links if isinstance(links, list) else []:
            if not isinstance(item, dict) or item.get("inst_gpio") is None:
                continue
            inst_gpio = int(item.get("inst_gpio"))
            expect = str(item.get("expect", "")).strip().lower()
            pins.append(inst_gpio)
            expected_by_gpio[inst_gpio] = {
                "expect": expect,
                "dut_gpio": item.get("dut_gpio"),
                "freq_hz": item.get("freq_hz"),
            }
        if not pins:
            return {"ok": False, "error_summary": "no instrument pins configured"}

        try:
            backend = self._backend_registry.resolve(instrument_id, "measure.digital")
        except KeyError as exc:
            return {
                "ok": False,
                "error_summary": str(exc),
                "failure_kind": failure_recovery.FAILURE_INSTRUMENT_NOT_READY,
            }
        meas = backend.measure_digital(cfg=cfg, pins=pins, duration_ms=duration_ms, out_path=digital_out)
        pin_rows = meas.get("pins", []) if isinstance(meas, dict) else []
        actual_by_gpio = {}
        for row in pin_rows:
            if isinstance(row, dict) and row.get("gpio") is not None:
                actual_by_gpio[int(row.get("gpio"))] = row

        mismatches = []
        checks = []
        for gpio, exp in expected_by_gpio.items():
            row = actual_by_gpio.get(gpio)
            if not row:
                mismatches.append({"inst_gpio": gpio, "reason": "missing_measurement"})
                continue
            actual_state = str(row.get("state", "")).strip().lower()
            expect_state = exp.get("expect", "")
            check = {
                "inst_gpio": gpio,
                "dut_gpio": exp.get("dut_gpio"),
                "expect": expect_state,
                "actual": actual_state,
                "samples": row.get("samples"),
                "ones": row.get("ones"),
                "zeros": row.get("zeros"),
                "transitions": row.get("transitions"),
            }
            checks.append(check)
            if actual_state != expect_state:
                mismatches.append({"inst_gpio": gpio, "reason": "state_mismatch", "expect": expect_state, "actual": actual_state})
                continue
            if expect_state == "toggle" and int(row.get("transitions", 0)) <= 0:
                mismatches.append({"inst_gpio": gpio, "reason": "toggle_no_transitions", "transitions": int(row.get("transitions", 0))})

        analog_checks = []
        analog_measurements = []
        for item in analog_links if isinstance(analog_links, list) else []:
            if not isinstance(item, dict) or item.get("inst_adc_gpio") is None:
                continue
            adc_gpio = int(item.get("inst_adc_gpio"))
            avg = int(item.get("avg", 16))
            min_v = float(item.get("expect_v_min")) if item.get("expect_v_min") is not None else None
            max_v = float(item.get("expect_v_max")) if item.get("expect_v_max") is not None else None
            if min_v is None and max_v is None and item.get("expect_v") is not None:
                center = float(item.get("expect_v"))
                tol = float(item.get("tolerance_v", 0.2))
                min_v = center - tol
                max_v = center + tol

            try:
                analog_backend = self._backend_registry.resolve(instrument_id, "measure.voltage")
            except KeyError as exc:
                return {"ok": False, "error_summary": str(exc)}
            meas_v = analog_backend.measure_voltage(cfg=cfg, gpio=adc_gpio, avg=avg, out_path=None)
            analog_measurements.append({"inst_adc_gpio": adc_gpio, "avg": avg, "response": meas_v})
            measured_v = _extract_voltage_v(meas_v)
            check = {
                "inst_adc_gpio": adc_gpio,
                "dut_signal": item.get("dut_signal"),
                "expect_v_min": min_v,
                "expect_v_max": max_v,
                "measured_v": measured_v,
                "avg": avg,
            }
            analog_checks.append(check)
            if measured_v is None:
                mismatches.append({"inst_adc_gpio": adc_gpio, "reason": "voltage_missing"})
                continue
            if min_v is not None and measured_v < min_v:
                mismatches.append({"inst_adc_gpio": adc_gpio, "reason": "voltage_below_min", "expect_v_min": min_v, "measured_v": measured_v})
            if max_v is not None and measured_v > max_v:
                mismatches.append({"inst_adc_gpio": adc_gpio, "reason": "voltage_above_max", "expect_v_max": max_v, "measured_v": measured_v})

        if analog_out and analog_measurements:
            _write_json(analog_out, {"ok": True, "measurements": analog_measurements})

        ok = len(mismatches) == 0
        verify_payload = {
            "ok": ok,
            "type": "instrument_digital_verify",
            "duration_ms": duration_ms,
            "instrument_id": inputs.get("instrument_id"),
            "host": cfg.get("host"),
            "port": cfg.get("port"),
            "checks": checks,
            "analog_checks": analog_checks,
            "mismatches": mismatches,
        }
        _write_json(verify_out, verify_payload)
        evidence_item = ael_evidence.make_item(
            kind="instrument.signature",
            source="check.instrument_signature",
            ok=ok,
            summary=("instrument signature matched" if ok else "instrument signature mismatch"),
            facts={
                "instrument_id": inputs.get("instrument_id"),
                "duration_ms": duration_ms,
                "digital_checks": len(checks),
                "analog_checks": len(analog_checks),
                "mismatch_count": len(mismatches),
                "failure_kind": (failure_recovery.FAILURE_VERIFICATION_MISMATCH if not ok else ""),
            },
            artifacts={
                "verify_result_json": verify_out,
                "instrument_digital_json": digital_out,
                "instrument_voltage_json": analog_out,
            },
        )
        if not ok:
            return {
                "ok": False,
                "error_summary": "instrument digital verification failed",
                "failure_kind": failure_recovery.FAILURE_VERIFICATION_MISMATCH,
                "result": verify_payload,
                "evidence": [evidence_item],
            }
        return {"ok": True, "result": verify_payload, "evidence": [evidence_item]}


class _SignalVerifyAdapter:
    def execute(self, step, plan, ctx):
        inputs = step.get("inputs", {}) if isinstance(step, dict) else {}
        probe_cfg = dict(inputs.get("probe_cfg", {}))
        pin_value = inputs.get("pin")
        duration_s = float(inputs.get("duration_s", 3.0))
        expected_hz = float(inputs.get("expected_hz", 1.0))
        min_edges = int(inputs.get("min_edges", 2))
        max_edges = int(inputs.get("max_edges", 6))
        log_path = inputs.get("log_path")
        output_mode = inputs.get("output_mode", "normal")
        measure_path = inputs.get("measure_path")
        test_limits = inputs.get("test_limits", {})
        recovery_demo = inputs.get("recovery_demo", {}) if isinstance(inputs.get("recovery_demo"), dict) else {}

        if bool(recovery_demo.get("fail_first")):
            state = _load_runtime_state(ctx)
            key = f"recovery_demo_fail_first_done:{step.get('name', 'check_signal')}"
            if not bool(state.get(key)):
                state[key] = True
                _save_runtime_state(ctx, state)
                injected = {"ok": False, "metrics": {}, "reasons": ["recovery_demo_fail_first_injected"]}
                if measure_path:
                    _write_json(measure_path, injected)
                evidence_item = ael_evidence.make_item(
                    kind="gpio.signal",
                    source="check.signal_verify",
                    ok=False,
                    summary="recovery demo injected first-attempt failure",
                    facts={
                        "injected_fail_first": True,
                        "pin": pin_value,
                        "failure_kind": failure_recovery.FAILURE_VERIFICATION_MISS,
                    },
                    artifacts={"measure_json": measure_path, "observe_log": log_path},
                )
                recovery_hint = failure_recovery.make_recovery_hint(
                    kind=failure_recovery.FAILURE_VERIFICATION_MISS,
                    recoverable=True,
                    preferred_action=str(recovery_demo.get("action_type") or "reset.serial"),
                    reason="recovery_demo_fail_first",
                    params=(dict(recovery_demo.get("params", {})) if isinstance(recovery_demo.get("params"), dict) else {}),
                )
                return {
                    "ok": False,
                    "error_summary": "recovery demo injected fail-first",
                    "failure_kind": failure_recovery.FAILURE_VERIFICATION_MISS,
                    "result": injected,
                    "evidence": [evidence_item],
                    "recovery_hint": recovery_hint,
                }

        capture = {}
        if log_path:
            with _tee_output(log_path, output_mode):
                ok_obs = observe_gpio_pin.run(
                    probe_cfg,
                    pin=pin_value,
                    duration_s=duration_s,
                    expected_hz=expected_hz,
                    min_edges=min_edges,
                    max_edges=max_edges,
                    capture_out=capture,
                    verify_edges=False,
                )
        else:
            ok_obs = observe_gpio_pin.run(
                probe_cfg,
                pin=pin_value,
                duration_s=duration_s,
                expected_hz=expected_hz,
                min_edges=min_edges,
                max_edges=max_edges,
                capture_out=capture,
                verify_edges=False,
            )
        if not ok_obs:
            return {
                "ok": False,
                "error_summary": "observe failed",
                "failure_kind": failure_recovery.FAILURE_TRANSPORT_ERROR,
            }

        if not capture.get("blob"):
            measure = {"ok": False, "metrics": {}, "reasons": ["no_capture"]}
            if measure_path:
                _write_json(measure_path, measure)
            return {
                "ok": False,
                "error_summary": "verify failed",
                "failure_kind": failure_recovery.FAILURE_VERIFICATION_MISS,
                "result": measure,
            }

        measure = la_verify.analyze_capture_bytes(
            capture.get("blob"),
            int(capture.get("sample_rate_hz", 0)),
            int(capture.get("bit", 0)),
            min_edges=min_edges,
        )
        ok = bool(measure.get("ok"))
        metrics = measure.get("metrics", {})
        min_f = test_limits.get("min_freq_hz")
        max_f = test_limits.get("max_freq_hz")
        duty_min = test_limits.get("duty_min")
        duty_max = test_limits.get("duty_max")
        if min_f is not None and metrics.get("freq_hz", 0.0) < float(min_f):
            measure.setdefault("reasons", []).append("freq_below_min")
            ok = False
        if max_f is not None and metrics.get("freq_hz", 0.0) > float(max_f):
            measure.setdefault("reasons", []).append("freq_above_max")
            ok = False
        if duty_min is not None and metrics.get("duty", 0.0) < float(duty_min):
            measure.setdefault("reasons", []).append("duty_below_min")
            ok = False
        if duty_max is not None and metrics.get("duty", 0.0) > float(duty_max):
            measure.setdefault("reasons", []).append("duty_above_max")
            ok = False

        measure["ok"] = bool(ok)
        if measure_path:
            _write_json(measure_path, measure)
        evidence_item = ael_evidence.make_item(
            kind="gpio.signal",
            source="check.signal_verify",
            ok=ok,
            summary=("signal verify passed" if ok else "signal verify failed"),
            facts={
                "pin": pin_value,
                "expected_hz": expected_hz,
                "metrics": measure.get("metrics", {}),
                "reasons": measure.get("reasons", []),
                "duration_s": duration_s,
                "failure_kind": (failure_recovery.FAILURE_VERIFICATION_MISMATCH if not ok else ""),
            },
            artifacts={
                "measure_json": measure_path,
                "observe_log": log_path,
            },
        )
        if not ok:
            return {
                "ok": False,
                "error_summary": "verify failed",
                "failure_kind": failure_recovery.FAILURE_VERIFICATION_MISMATCH,
                "result": measure,
                "evidence": [evidence_item],
            }
        return {"ok": True, "result": measure, "evidence": [evidence_item]}


class _NoopRecoveryAdapter:
    def execute(self, action, plan, ctx):
        return {"ok": False, "error_summary": "recovery action not implemented"}


class _SerialResetRecoveryAdapter:
    def execute(self, action, plan, ctx):
        params = action.get("params", {}) if isinstance(action, dict) and isinstance(action.get("params"), dict) else {}
        port = str(params.get("port") or "").strip()
        if not port:
            return {"ok": False, "error_summary": "reset.serial requires params.port"}
        baud = int(params.get("baud", 115200))
        pulse_ms = max(20, int(params.get("pulse_ms", 120)))
        settle_ms = max(50, int(params.get("settle_ms", 350)))
        try:
            import serial  # type: ignore
        except Exception as exc:
            return {"ok": False, "error_summary": f"reset.serial requires pyserial: {exc}"}
        try:
            ser = serial.Serial(
                port,
                baudrate=baud,
                timeout=0.1,
                rtscts=False,
                dsrdtr=False,
            )
            try:
                try:
                    ser.dtr = False
                except Exception:
                    pass
                ser.rts = True
                time.sleep(pulse_ms / 1000.0)
                ser.rts = False
                time.sleep(settle_ms / 1000.0)
            finally:
                try:
                    ser.close()
                except Exception:
                    pass
        except Exception as exc:
            return {"ok": False, "error_summary": f"reset.serial failed on {port}: {exc}"}
        return {
            "ok": True,
            "action_type": "reset.serial",
            "port": port,
            "baud": baud,
            "pulse_ms": pulse_ms,
            "settle_ms": settle_ms,
        }


class _NoopCheckAdapter:
    def execute(self, step, plan, ctx):
        inputs = step.get("inputs", {}) if isinstance(step, dict) else {}
        out_json = inputs.get("out_json")
        payload = {
            "ok": True,
            "name": step.get("name", ""),
            "type": step.get("type", ""),
            "note": inputs.get("note", "noop"),
        }
        if out_json:
            _write_json(out_json, payload)
        return {"ok": True, "result": payload}


class _InstrumentAipHttpAdapter:
    def __init__(self, capability: str | None = None):
        self._capability = capability

    def execute(self, step, plan, ctx):
        step_obj = dict(step) if isinstance(step, dict) else {}
        inputs = dict(step_obj.get("inputs", {})) if isinstance(step_obj.get("inputs"), dict) else {}
        if self._capability and not inputs.get("capability"):
            inputs["capability"] = self._capability
        step_obj["inputs"] = inputs
        return instrument_aip_http.execute(step_obj, plan, ctx)


class _InstrumentSimHttpAdapter:
    def __init__(self, capability: str | None = None):
        self._capability = capability

    def execute(self, step, plan, ctx):
        step_obj = dict(step) if isinstance(step, dict) else {}
        inputs = dict(step_obj.get("inputs", {})) if isinstance(step_obj.get("inputs"), dict) else {}
        if self._capability and not inputs.get("capability"):
            inputs["capability"] = self._capability
        step_obj["inputs"] = inputs
        return instrument_sim_http.execute(step_obj, plan, ctx)


class AdapterRegistry:
    def __init__(self):
        self._instrument_backends = _InstrumentBackendRegistry()
        self._capability_map = {
            "measure.voltage": _InstrumentAipHttpAdapter("measure.voltage"),
            "measure.digital": _InstrumentAipHttpAdapter("measure.digital"),
            "selftest": _InstrumentAipHttpAdapter("selftest"),
            "control.reset_target": _InstrumentAipHttpAdapter("control.reset_target"),
        }
        self._sim_capability_map = {
            "measure.voltage": _InstrumentSimHttpAdapter("measure.voltage"),
            "measure.digital": _InstrumentSimHttpAdapter("measure.digital"),
            "uart_log": _InstrumentSimHttpAdapter("uart_log"),
        }
        self._adapters = {
            "preflight.probe": _PreflightAdapter(),
            "build.idf": _BuildAdapter("idf"),
            "build.arm_debug": _BuildAdapter("arm_debug"),
            "build.cmake": _BuildAdapter("cmake"),
            "load.idf_esptool": _LoadAdapter("idf_esptool"),
            "load.gdbmi": _LoadAdapter("gdbmi"),
            "check.uart_log": _UartCheckAdapter(),
            "check.instrument_signature": _InstrumentSignatureAdapter(self._instrument_backends),
            "check.signal_verify": _SignalVerifyAdapter(),
            "check.instrument_selftest": _InstrumentSelftestAdapter(self._instrument_backends),
            "check.noop": _NoopCheckAdapter(),
            "instrument.aip_http": _InstrumentAipHttpAdapter(),
            "instrument.aip_http.measure.voltage": self._capability_map["measure.voltage"],
            "instrument.aip_http.measure.digital": self._capability_map["measure.digital"],
            "instrument.aip_http.selftest": self._capability_map["selftest"],
            "instrument.aip_http.control.reset_target": self._capability_map["control.reset_target"],
            "instrument.sim_http": _InstrumentSimHttpAdapter(),
            "instrument.sim_http.measure.voltage": self._sim_capability_map["measure.voltage"],
            "instrument.sim_http.measure.digital": self._sim_capability_map["measure.digital"],
            "instrument.sim_http.uart_log": self._sim_capability_map["uart_log"],
        }
        self._recovery = {
            "reset.serial": _SerialResetRecoveryAdapter(),
        }

    def get(self, step_type: str):
        if step_type not in self._adapters:
            raise KeyError(f"adapter not found for step type: {step_type}")
        return self._adapters[step_type]

    def recovery(self, action_type: str):
        if action_type not in self._recovery:
            raise KeyError(f"recovery adapter not found: {action_type}")
        return self._recovery[action_type]

    def get_for_capability(self, capability: str):
        if capability not in self._capability_map:
            raise KeyError(f"instrument capability not mapped: {capability}")
        return self._capability_map[capability]
