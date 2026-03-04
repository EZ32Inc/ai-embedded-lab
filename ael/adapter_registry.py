from __future__ import annotations

import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Tuple

from adapters import (
    build_cmake,
    build_idf,
    build_stm32,
    esp32s3_dev_c_meter_tcp,
    flash_bmda_gdbmi,
    flash_idf,
    instrument_aip_http,
    observe_gpio_pin,
    observe_uart_log,
    preflight,
)
from ael import run_manager
from tools import la_verify


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
        if not bool(uart_result.get("ok", False)):
            return {"ok": False, "error_summary": uart_result.get("error_summary") or "uart observe failed", "result": uart_result}
        return {"ok": True, "result": uart_result}


class _InstrumentSelftestAdapter:
    def execute(self, step, plan, ctx):
        inputs = step.get("inputs", {}) if isinstance(step, dict) else {}
        cfg = inputs.get("cfg", {})
        params = inputs.get("params", {})
        out_path = inputs.get("out_path")
        if not out_path:
            return {"ok": False, "error_summary": "selftest output path missing"}
        try:
            payload = esp32s3_dev_c_meter_tcp.selftest(
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
        except Exception as exc:
            return {"ok": False, "error_summary": str(exc)}
        if not bool(payload.get("pass", False)):
            return {"ok": False, "error_summary": payload.get("error", "instrument selftest failed")}
        return {"ok": True, "result": payload}


class _InstrumentSignatureAdapter:
    def execute(self, step, plan, ctx):
        inputs = step.get("inputs", {}) if isinstance(step, dict) else {}
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

        meas = esp32s3_dev_c_meter_tcp.measure_digital(cfg, pins=pins, duration_ms=duration_ms, out_path=digital_out)
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

            meas_v = esp32s3_dev_c_meter_tcp.measure_voltage(cfg, gpio=adc_gpio, avg=avg, out_path=None)
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
        if not ok:
            return {"ok": False, "error_summary": "instrument digital verification failed", "result": verify_payload}
        return {"ok": True, "result": verify_payload}


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
            return {"ok": False, "error_summary": "observe failed"}

        if not capture.get("blob"):
            measure = {"ok": False, "metrics": {}, "reasons": ["no_capture"]}
            if measure_path:
                _write_json(measure_path, measure)
            return {"ok": False, "error_summary": "verify failed", "result": measure}

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
        if not ok:
            return {"ok": False, "error_summary": "verify failed", "result": measure}
        return {"ok": True, "result": measure}


class _NoopRecoveryAdapter:
    def execute(self, action, plan, ctx):
        return {"ok": False, "error_summary": "recovery action not implemented"}


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


class AdapterRegistry:
    def __init__(self):
        self._capability_map = {
            "measure.voltage": _InstrumentAipHttpAdapter("measure.voltage"),
            "measure.digital": _InstrumentAipHttpAdapter("measure.digital"),
            "selftest": _InstrumentAipHttpAdapter("selftest"),
            "control.reset_target": _InstrumentAipHttpAdapter("control.reset_target"),
        }
        self._adapters = {
            "preflight.probe": _PreflightAdapter(),
            "build.idf": _BuildAdapter("idf"),
            "build.arm_debug": _BuildAdapter("arm_debug"),
            "build.cmake": _BuildAdapter("cmake"),
            "load.idf_esptool": _LoadAdapter("idf_esptool"),
            "load.gdbmi": _LoadAdapter("gdbmi"),
            "check.uart_log": _UartCheckAdapter(),
            "check.instrument_signature": _InstrumentSignatureAdapter(),
            "check.signal_verify": _SignalVerifyAdapter(),
            "check.instrument_selftest": _InstrumentSelftestAdapter(),
            "instrument.aip_http": _InstrumentAipHttpAdapter(),
            "instrument.aip_http.measure.voltage": self._capability_map["measure.voltage"],
            "instrument.aip_http.measure.digital": self._capability_map["measure.digital"],
            "instrument.aip_http.selftest": self._capability_map["selftest"],
            "instrument.aip_http.control.reset_target": self._capability_map["control.reset_target"],
        }
        self._recovery = {
            "reset.serial": _NoopRecoveryAdapter(),
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
