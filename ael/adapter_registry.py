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
    check_mailbox_verify,
    control_reset_serial,
    flash_bmda_gdbmi,
    flash_idf,
    instrument_aip_http,
    instrument_sim_http,
    observe_log,
    observe_gpio_pin,
    preflight,
)
from ael import run_manager
from ael import evidence as ael_evidence
from ael import failure_recovery
from ael import check_eval
from ael.instruments import native_api_dispatch
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
        from ael.instruments.backends.esp32_meter.backend import Esp32MeterBackend

        self._impl = esp32s3_dev_c_meter_tcp
        self._backend_cls = Esp32MeterBackend

    def _backend(self, cfg):
        return self._backend_cls(
            host=str(cfg.get("host") or "192.168.4.1"),
            port=int(cfg.get("port") or 9000),
            timeout_s=float(cfg.get("timeout_s") or 3.0),
        )

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
        result = self._backend(cfg).execute(
            "gpio_measure",
            {"channels": list(pins), "duration_ms": int(duration_ms)},
        )
        if result.get("status") != "success":
            raise RuntimeError(str(((result.get("error") or {}) if isinstance(result.get("error"), dict) else {}).get("message") or "meter gpio_measure failed"))
        raw = ((result.get("data") or {}) if isinstance(result.get("data"), dict) else {}).get("raw")
        if out_path and isinstance(raw, dict):
            _write_json(out_path, raw)
        return raw if isinstance(raw, dict) else {}

    def measure_voltage(self, cfg, gpio, avg, out_path):
        result = self._backend(cfg).execute(
            "voltage_read",
            {"gpio": int(gpio), "avg": int(avg)},
        )
        if result.get("status") != "success":
            raise RuntimeError(str(((result.get("error") or {}) if isinstance(result.get("error"), dict) else {}).get("message") or "meter voltage_read failed"))
        data = (result.get("data") or {}) if isinstance(result.get("data"), dict) else {}
        raw = data.get("raw")
        if out_path and isinstance(raw, dict):
            _write_json(out_path, raw)
        return {"voltage_v": data.get("voltage_v")}


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
    run_manager.ensure_thread_output_proxies()
    tee, f = run_manager.open_tee(Path(log_path), output_mode, console=run_manager.base_stdout())
    try:
        with run_manager.route_thread_output(tee):
            yield
    finally:
        try:
            tee.flush()
        except Exception:
            pass
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
        def _run_preflight_native():
            payload = native_api_dispatch.preflight_probe(probe_cfg)
            if payload.get("status") == "ok":
                return True, payload.get("data", {})
            details = payload.get("error", {}).get("details", {})
            info = details.get("preflight", {}) if isinstance(details, dict) else {}
            return False, info if isinstance(info, dict) else {}

        if log_path:
            with _tee_output(log_path, output_mode):
                ok, info = _run_preflight_native()
        else:
            ok, info = _run_preflight_native()
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
        if log_path and self.method == "idf_esptool":
            with _tee_output(log_path, output_mode):
                ok = flash_idf.run(probe_cfg, firmware_path, flash_cfg=flash_cfg, flash_json_path=flash_json_path)
        else:
            if self.method == "idf_esptool":
                ok = flash_idf.run(probe_cfg, firmware_path, flash_cfg=flash_cfg, flash_json_path=flash_json_path)
            else:
                payload = native_api_dispatch.program_firmware(
                    probe_cfg,
                    firmware_path=firmware_path,
                    flash_cfg=flash_cfg,
                    flash_json_path=flash_json_path,
                )
                ok = payload.get("status") == "ok"
        if not ok:
            error = payload.get("error", {}) if isinstance(payload, dict) else {}
            details = error.get("details", {}) if isinstance(error, dict) else {}
            result = {
                "ok": False,
                "error_summary": str(error.get("message") or "load failed"),
            }
            if "retryable" in error:
                result["retryable"] = bool(error.get("retryable"))
            if isinstance(details, dict) and details:
                result["details"] = details
            return result
        settle_s = 0.0
        try:
            settle_s = max(0.0, float(flash_cfg.get("post_load_settle_s", 0.0)))
        except Exception:
            settle_s = 0.0
        stage_execution = plan.get("stage_execution", {}) if isinstance(plan, dict) and isinstance(plan.get("stage_execution"), dict) else {}
        if str(stage_execution.get("requested_until") or "").strip().lower() == "run-exit":
            settle_s = 0.0
        if settle_s > 0.0:
            print(f"Flash: settling {settle_s:.2f}s before next stage")
            time.sleep(settle_s)
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
        recovery_demo = cfg.get("recovery_demo", {}) if isinstance(cfg.get("recovery_demo"), dict) else {}
        if bool(recovery_demo.get("fail_first")):
            state = _load_runtime_state(ctx)
            key = f"recovery_demo_fail_first_done:{step.get('name', 'check_uart')}"
            if not bool(state.get(key)):
                state[key] = True
                _save_runtime_state(ctx, state)
                injected = {
                    "ok": False,
                    "bytes": 0,
                    "lines": 0,
                    "download_mode_detected": True,
                    "error_summary": "recovery demo injected uart fail-first",
                }
                _write_json(out_json, injected)
                recovery_hint = failure_recovery.make_recovery_hint(
                    kind=failure_recovery.FAILURE_VERIFICATION_MISS,
                    recoverable=True,
                    preferred_action=str(recovery_demo.get("action_type") or "reset.serial"),
                    reason="recovery_demo_uart_fail_first",
                    params=(dict(recovery_demo.get("params", {})) if isinstance(recovery_demo.get("params"), dict) else {}),
                )
                evidence_item = ael_evidence.make_item(
                    kind="uart.verify",
                    source="check.uart_log",
                    ok=False,
                    summary="recovery demo injected first-attempt UART failure",
                    facts={
                        "failure_kind": failure_recovery.FAILURE_VERIFICATION_MISS,
                        "recovery_hint": recovery_hint,
                        "injected_fail_first": True,
                    },
                    artifacts={"uart_observe_json": out_json, "uart_raw_log": raw_log_path},
                )
                return {
                    "ok": False,
                    "error_summary": "recovery demo injected uart fail-first",
                    "failure_kind": failure_recovery.FAILURE_VERIFICATION_MISS,
                    "result": injected,
                    "evidence": [evidence_item],
                    "recovery_hint": recovery_hint,
                }
        if not cfg.get("port") and flash_json_path:
            try:
                flash_payload = json.loads(Path(flash_json_path).read_text(encoding="utf-8"))
                if flash_payload.get("port"):
                    cfg["port"] = flash_payload.get("port")
            except Exception:
                pass
        if log_path:
            with _tee_output(log_path, output_mode):
                uart_result = observe_log.run_serial_log(cfg, raw_log_path=raw_log_path)
        else:
            uart_result = observe_log.run_serial_log(cfg, raw_log_path=raw_log_path)
        _write_json(out_json, uart_result)
        uart_facts = {
            "ok": bool(uart_result.get("ok", False)),
            "bytes": int(uart_result.get("bytes") or 0),
            "lines": int(uart_result.get("lines") or 0),
            "port": uart_result.get("port"),
            "baud": uart_result.get("baud"),
            "crash_detected": bool(uart_result.get("crash_detected", False)),
            "reboot_loop_suspected": bool(uart_result.get("reboot_loop_suspected", False)),
            "missing_expect": uart_result.get("missing_expect", []),
            "forbid_matched": uart_result.get("forbid_matched", []),
            "matched_expect": (
                ((uart_result.get("matched") or {}).get("expect"))
                if isinstance(uart_result.get("matched"), dict)
                else {}
            ),
            "matched_boot": (
                ((uart_result.get("matched") or {}).get("boot"))
                if isinstance(uart_result.get("matched"), dict)
                else {}
            ),
            "firmware_ready_seen": not bool(uart_result.get("missing_expect", [])),
            "download_mode_detected": bool(uart_result.get("download_mode_detected", False)),
            "error_summary": uart_result.get("error_summary") or "uart observe failed",
        }
        verdict = check_eval.evaluate_uart_facts(uart_facts, cfg)
        failure_kind = verdict.get("failure_kind", "")
        recovery_hint = verdict.get("recovery_hint")
        error_summary = verdict.get("error_summary") or "uart observe failed"
        evidence_item = ael_evidence.make_item(
            kind="uart.verify",
            source="check.uart_log",
            ok=verdict.get("ok", False),
            summary=(uart_result.get("error_summary") or "uart capture validated"),
            facts={
                **uart_facts,
                "verify_substage": verdict.get("verify_substage", "uart.verify"),
                "failure_kind": failure_kind if not bool(verdict.get("ok", False)) else "",
                "failure_class": verdict.get("failure_class", "") if not bool(verdict.get("ok", False)) else "",
                "missing_expected_patterns": list(uart_facts.get("missing_expect", []) or []),
                "recovery_hint": recovery_hint if isinstance(recovery_hint, dict) else {},
            },
            artifacts={
                "uart_observe_json": out_json,
                "uart_raw_log": raw_log_path,
            },
        )
        if not bool(verdict.get("ok", False)):
            return {
                "ok": False,
                "error_summary": error_summary,
                "failure_kind": failure_kind,
                "failure_class": verdict.get("failure_class", ""),
                "verify_substage": verdict.get("verify_substage", "uart.verify"),
                "result": uart_result,
                "facts": uart_facts,
                "evidence": [evidence_item],
                "recovery_hint": recovery_hint,
            }
        return {"ok": True, "result": uart_result, "facts": uart_facts, "evidence": [evidence_item]}


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

    def _backend_exception_result(self, instrument_id, cfg, verify_out, digital_out, analog_out, exc):
        text = str(exc or "").strip()
        lowered = text.lower()
        if "timed out" in lowered or "timeout" in lowered:
            failure_class = "instrument_backend_timeout"
        else:
            failure_class = "instrument_backend_error"
        verify_payload = {
            "ok": False,
            "type": "instrument_digital_verify",
            "instrument_id": instrument_id,
            "host": cfg.get("host"),
            "port": cfg.get("port"),
            "checks": [],
            "analog_checks": [],
            "mismatches": [],
            "error_summary": text or "instrument backend error",
        }
        if verify_out:
            _write_json(verify_out, verify_payload)
        evidence_item = ael_evidence.make_item(
            kind="instrument.signature",
            source="check.instrument_signature",
            ok=False,
            summary=text or "instrument backend error",
            facts={
                "instrument_id": instrument_id,
                "verify_substage": "instrument.signature",
                "failure_kind": failure_recovery.FAILURE_TRANSPORT_ERROR,
                "failure_class": failure_class,
                "backend_ready": False,
                "mismatch_count": 0,
                "mismatch_reasons": [],
            },
            artifacts={
                "verify_result_json": verify_out,
                "instrument_digital_json": digital_out,
                "instrument_voltage_json": analog_out,
            },
        )
        return {
            "ok": False,
            "error_summary": text or "instrument backend error",
            "failure_kind": failure_recovery.FAILURE_TRANSPORT_ERROR,
            "failure_class": failure_class,
            "verify_substage": "instrument.signature",
            "result": verify_payload,
            "facts": {"backend_ready": False, "mismatch_count": 0},
            "evidence": [evidence_item],
        }

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

        manifest = {"id": instrument_id, "communication": {"endpoint": f"{cfg.get('host')}:{cfg.get('port')}"}} if instrument_id else {}
        native_digital = native_api_dispatch.measure_digital(
            manifest,
            pins=pins,
            duration_ms=duration_ms,
            host=cfg.get("host"),
            port=cfg.get("port"),
        )
        if native_digital.get("status") == "ok":
            meas = native_digital.get("data", {})
        elif native_digital.get("error", {}).get("code") != "native_measure_digital_unsupported":
            err = native_digital.get("error", {})
            return self._backend_exception_result(
                instrument_id,
                cfg,
                verify_out,
                digital_out,
                analog_out,
                RuntimeError(str(err.get("message") or "instrument native digital measurement failed")),
            )
        else:
            try:
                backend = self._backend_registry.resolve(instrument_id, "measure.digital")
            except KeyError as exc:
                sig_facts = {"backend_ready": False, "mismatch_count": 0, "error_summary": str(exc)}
                verdict = check_eval.evaluate_instrument_signature_facts(sig_facts)
                return {
                    "ok": False,
                    "error_summary": verdict.get("error_summary") or str(exc),
                    "failure_kind": verdict.get("failure_kind", failure_recovery.FAILURE_INSTRUMENT_NOT_READY),
                    "facts": sig_facts,
                }
            try:
                meas = backend.measure_digital(cfg=cfg, pins=pins, duration_ms=duration_ms, out_path=digital_out)
            except Exception as exc:
                return self._backend_exception_result(instrument_id, cfg, verify_out, digital_out, analog_out, exc)
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

            native_voltage = native_api_dispatch.measure_voltage(
                manifest,
                gpio=adc_gpio,
                avg=avg,
                host=cfg.get("host"),
                port=cfg.get("port"),
            )
            if native_voltage.get("status") == "ok":
                meas_v = native_voltage.get("data", {})
            elif native_voltage.get("error", {}).get("code") != "native_measure_voltage_unsupported":
                err = native_voltage.get("error", {})
                return self._backend_exception_result(
                    instrument_id,
                    cfg,
                    verify_out,
                    digital_out,
                    analog_out,
                    RuntimeError(str(err.get("message") or "instrument native voltage measurement failed")),
                )
            else:
                try:
                    analog_backend = self._backend_registry.resolve(instrument_id, "measure.voltage")
                except KeyError as exc:
                    return {"ok": False, "error_summary": str(exc)}
                try:
                    meas_v = analog_backend.measure_voltage(cfg=cfg, gpio=adc_gpio, avg=avg, out_path=None)
                except Exception as exc:
                    return self._backend_exception_result(instrument_id, cfg, verify_out, digital_out, analog_out, exc)
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

        sig_facts = {
            "backend_ready": True,
            "mismatch_count": len(mismatches),
            "digital_check_count": len(checks),
            "analog_check_count": len(analog_checks),
            "digital_mismatch_count": sum(1 for item in mismatches if isinstance(item, dict) and item.get("inst_gpio") is not None),
            "analog_mismatch_count": sum(1 for item in mismatches if isinstance(item, dict) and item.get("inst_adc_gpio") is not None),
            "mismatch_reasons": [item.get("reason") for item in mismatches if isinstance(item, dict) and item.get("reason")],
            "missing_expected_channels": [
                item.get("inst_gpio")
                for item in mismatches
                if isinstance(item, dict) and item.get("reason") == "missing_measurement" and item.get("inst_gpio") is not None
            ],
            "analog_range_failures": [
                item.get("inst_adc_gpio")
                for item in mismatches
                if isinstance(item, dict) and str(item.get("reason") or "").startswith("voltage_") and item.get("inst_adc_gpio") is not None
            ],
        }
        verdict = check_eval.evaluate_instrument_signature_facts(sig_facts)
        ok = bool(verdict.get("ok", False))
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
                "verify_substage": verdict.get("verify_substage", "instrument.signature"),
                "duration_ms": duration_ms,
                "digital_checks": len(checks),
                "analog_checks": len(analog_checks),
                "mismatch_count": len(mismatches),
                "digital_mismatch_count": sig_facts.get("digital_mismatch_count"),
                "analog_mismatch_count": sig_facts.get("analog_mismatch_count"),
                "mismatch_reasons": sig_facts.get("mismatch_reasons", []),
                "missing_expected_channels": sig_facts.get("missing_expected_channels", []),
                "analog_range_failures": sig_facts.get("analog_range_failures", []),
                "failure_class": (verdict.get("failure_class", "") if not ok else ""),
                "failure_kind": (verdict.get("failure_kind", "") if not ok else ""),
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
                "error_summary": verdict.get("error_summary") or "instrument digital verification failed",
                "failure_kind": verdict.get("failure_kind", failure_recovery.FAILURE_VERIFICATION_MISMATCH),
                "failure_class": verdict.get("failure_class", ""),
                "verify_substage": verdict.get("verify_substage", "instrument.signature"),
                "result": verify_payload,
                "facts": sig_facts,
                "evidence": [evidence_item],
            }
        return {"ok": True, "result": verify_payload, "facts": sig_facts, "evidence": [evidence_item]}


class _SignalVerifyAdapter:
    def execute(self, step, plan, ctx):
        inputs = step.get("inputs", {}) if isinstance(step, dict) else {}
        probe_cfg = dict(inputs.get("probe_cfg", {}))
        pin_value = inputs.get("pin")
        duration_s = float(inputs.get("duration_s", 3.0))
        expected_hz = float(inputs.get("expected_hz", 1.0))
        min_edges = int(inputs.get("min_edges", 2))
        max_edges = int(inputs.get("max_edges", 6))
        raw_signal_checks = inputs.get("signal_checks", [])
        signal_checks = [item for item in raw_signal_checks if isinstance(item, dict)]
        signal_relations = [item for item in inputs.get("signal_relations", []) if isinstance(item, dict)]
        log_path = inputs.get("log_path")
        output_mode = inputs.get("output_mode", "normal")
        measure_path = inputs.get("measure_path")
        test_limits = inputs.get("test_limits", {})
        verify_prep = inputs.get("verify_prep", {}) if isinstance(inputs.get("verify_prep"), dict) else {}
        led_observe_cfg = inputs.get("led_observe_cfg", {}) if isinstance(inputs.get("led_observe_cfg"), dict) else {}
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
            if bool(recovery_demo.get("fail_after_recovery")):
                injected = {"ok": False, "metrics": {}, "reasons": ["recovery_demo_fail_after_recovery"]}
                if measure_path:
                    _write_json(measure_path, injected)
                evidence_item = ael_evidence.make_item(
                    kind="gpio.signal",
                    source="check.signal_verify",
                    ok=False,
                    summary="recovery demo forced failure after recovery attempt",
                    facts={
                        "injected_fail_after_recovery": True,
                        "pin": pin_value,
                        "failure_kind": failure_recovery.FAILURE_NON_RECOVERABLE,
                    },
                    artifacts={"measure_json": measure_path, "observe_log": log_path},
                )
                return {
                    "ok": False,
                    "error_summary": "recovery demo forced fail after recovery",
                    "failure_kind": failure_recovery.FAILURE_NON_RECOVERABLE,
                    "result": injected,
                    "evidence": [evidence_item],
                }

        def _capture_once(local_capture):
            capture_pins = [str(item.get("resolved_pin") or item.get("pin") or "") for item in signal_checks if str(item.get("resolved_pin") or item.get("pin") or "").strip()]
            native_capture = native_api_dispatch.capture_signature(
                probe_cfg,
                pin=pin_value,
                pins=capture_pins,
                duration_s=duration_s,
                expected_hz=expected_hz,
                min_edges=min_edges,
                max_edges=max_edges,
            )
            if native_capture.get("status") != "ok":
                return False
            payload = native_capture.get("data", {})
            if isinstance(payload, dict):
                local_capture.update(payload)
            return True

        def _analyze_signal_measure(capture_payload, check_cfg):
            pin_bits = capture_payload.get("pin_bits", {}) if isinstance(capture_payload.get("pin_bits"), dict) else {}
            resolved_pin = str(check_cfg.get("resolved_pin") or check_cfg.get("pin") or pin_value)
            bit = pin_bits.get(resolved_pin, capture_payload.get("bit", 0))
            measure_payload = la_verify.analyze_capture_bytes(
                capture_payload.get("blob"),
                int(capture_payload.get("sample_rate_hz", 0)),
                int(bit),
                min_edges=int(check_cfg.get("min_edges", min_edges)),
            )
            ok_local = bool(measure_payload.get("ok"))
            metrics_local = measure_payload.get("metrics", {})
            min_f = check_cfg.get("min_freq_hz")
            max_f = check_cfg.get("max_freq_hz")
            duty_min = check_cfg.get("duty_min")
            duty_max = check_cfg.get("duty_max")
            if min_f is not None and metrics_local.get("freq_hz", 0.0) < float(min_f):
                measure_payload.setdefault("reasons", []).append("freq_below_min")
                ok_local = False
            if max_f is not None and metrics_local.get("freq_hz", 0.0) > float(max_f):
                measure_payload.setdefault("reasons", []).append("freq_above_max")
                ok_local = False
            if duty_min is not None and metrics_local.get("duty", 0.0) < float(duty_min):
                measure_payload.setdefault("reasons", []).append("duty_below_min")
                ok_local = False
            if duty_max is not None and metrics_local.get("duty", 0.0) > float(duty_max):
                measure_payload.setdefault("reasons", []).append("duty_above_max")
                ok_local = False
            measure_payload["ok"] = bool(ok_local)
            measure_payload["pin"] = resolved_pin
            measure_payload["name"] = str(check_cfg.get("name") or resolved_pin)
            return measure_payload

        def _evaluate_signal_relations(check_measures):
            relation_results = []
            ok_local = True
            index = {str(item.get("name") or ""): item for item in check_measures}
            for relation in signal_relations:
                if str(relation.get("type") or "") != "frequency_ratio":
                    continue
                numerator = str(relation.get("numerator") or "")
                denominator = str(relation.get("denominator") or "")
                left = index.get(numerator)
                right = index.get(denominator)
                result = dict(relation)
                ratio = None
                relation_ok = False
                if left and right:
                    left_freq = float(((left.get("metrics") or {}).get("freq_hz")) or 0.0)
                    right_freq = float(((right.get("metrics") or {}).get("freq_hz")) or 0.0)
                    if right_freq > 0.0:
                        ratio = left_freq / right_freq
                        relation_ok = True
                        if relation.get("min_ratio") is not None and ratio < float(relation.get("min_ratio")):
                            relation_ok = False
                        if relation.get("max_ratio") is not None and ratio > float(relation.get("max_ratio")):
                            relation_ok = False
                result["ok"] = relation_ok
                if ratio is not None:
                    result["ratio"] = ratio
                if not relation_ok:
                    ok_local = False
                relation_results.append(result)
            return ok_local, relation_results

        def _led_level_poll():
            attempts = max(1, int(led_observe_cfg.get("max_attempts", 10)))
            sleep_s = max(0.0, float(led_observe_cfg.get("sleep_s", 0.5)))
            seen_levels = set()
            samples = []
            first_capture = None
            for attempt in range(1, attempts + 1):
                local_capture = {}
                ok_local = _capture_once(local_capture)
                if not ok_local or not local_capture.get("blob"):
                    return False, {"ok": False, "metrics": {"attempts": attempt}, "reasons": ["led_capture_failed"], "samples": samples}, first_capture
                if first_capture is None:
                    first_capture = dict(local_capture)
                high = int(local_capture.get("high", 0))
                low = int(local_capture.get("low", 0))
                level = 1 if high >= low else 0
                seen_levels.add(level)
                samples.append({"attempt": attempt, "level": level, "high": high, "low": low})
                print(f"Verify: LED poll attempt {attempt}/{attempts} level={level} high={high} low={low}")
                if len(seen_levels) >= 2:
                    return True, {"ok": True, "metrics": {"attempts": attempt, "levels_seen": sorted(seen_levels)}, "reasons": [], "samples": samples}, first_capture
                if attempt < attempts:
                    time.sleep(sleep_s)
            return False, {"ok": False, "metrics": {"attempts": attempts, "levels_seen": sorted(seen_levels)}, "reasons": ["led_level_never_changed"], "samples": samples}, first_capture

        capture = {}
        prep_delay_s = 0.0
        try:
            prep_delay_s = max(0.0, float(verify_prep.get("delay_s", 0.0)))
        except Exception:
            prep_delay_s = 0.0
        prep_message = str(verify_prep.get("message") or "").strip()
        if log_path:
            with _tee_output(log_path, output_mode):
                if prep_message:
                    print(prep_message)
                if prep_delay_s > 0.0:
                    time.sleep(prep_delay_s)
                if led_observe_cfg.get("enabled"):
                    ok_obs, measure, first_capture = _led_level_poll()
                    if isinstance(first_capture, dict):
                        capture.update(first_capture)
                else:
                    ok_obs = _capture_once(capture)
                    measure = None
        else:
            if prep_message:
                print(prep_message)
            if prep_delay_s > 0.0:
                time.sleep(prep_delay_s)
            if led_observe_cfg.get("enabled"):
                ok_obs, measure, first_capture = _led_level_poll()
                if isinstance(first_capture, dict):
                    capture.update(first_capture)
            else:
                ok_obs = _capture_once(capture)
                measure = None
        signal_facts = {"observe_ok": bool(ok_obs), "has_capture": False, "measure_ok": False}
        if not ok_obs:
            if led_observe_cfg.get("enabled") and measure_path and isinstance(measure, dict):
                _write_json(measure_path, measure)
                signal_facts.update({"has_capture": True, "measure_ok": False, "reasons": measure.get("reasons", []), "metrics": measure.get("metrics", {}), "pin": pin_value, "expected_hz": expected_hz, "duration_s": duration_s})
            verdict = check_eval.evaluate_signal_facts(signal_facts)
            return {
                "ok": False,
                "error_summary": verdict.get("error_summary") or "observe failed",
                "failure_kind": verdict.get("failure_kind", failure_recovery.FAILURE_TRANSPORT_ERROR),
                "result": measure if led_observe_cfg.get("enabled") else None,
                "facts": signal_facts,
            }

        if not capture.get("blob"):
            measure = {"ok": False, "metrics": {}, "reasons": ["no_capture"]}
            if measure_path:
                _write_json(measure_path, measure)
            signal_facts.update({"has_capture": False, "measure_ok": False, "reasons": measure.get("reasons", [])})
            verdict = check_eval.evaluate_signal_facts(signal_facts)
            return {
                "ok": False,
                "error_summary": verdict.get("error_summary") or "verify failed",
                "failure_kind": verdict.get("failure_kind", failure_recovery.FAILURE_VERIFICATION_MISS),
                "result": measure,
                "facts": signal_facts,
            }

        if not led_observe_cfg.get("enabled"):
            if signal_checks:
                check_measures = [_analyze_signal_measure(capture, item) for item in signal_checks]
                relations_ok, relation_results = _evaluate_signal_relations(check_measures)
                ok = all(bool(item.get("ok")) for item in check_measures) and relations_ok
                reasons = []
                for item in check_measures:
                    for reason in item.get("reasons", []):
                        reasons.append(f"{item.get('name')}:{reason}")
                for relation in relation_results:
                    if not relation.get("ok", False):
                        reasons.append(
                            "relation_failed:"
                            f"{relation.get('numerator')}:{relation.get('denominator')}"
                        )
                primary = check_measures[0] if check_measures else {"metrics": {}}
                measure = {
                    "ok": bool(ok),
                    "metrics": dict(primary.get("metrics", {})),
                    "reasons": reasons,
                    "checks": check_measures,
                    "relations": relation_results,
                }
            else:
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
        signal_facts.update(
            {
                "has_capture": True,
                "measure_ok": bool(ok),
                "reasons": measure.get("reasons", []),
                "metrics": measure.get("metrics", {}),
                "pin": pin_value,
                "expected_hz": expected_hz,
                "duration_s": duration_s,
            }
        )
        if signal_checks:
            signal_facts["signal_checks"] = measure.get("checks", [])
            signal_facts["signal_relations"] = measure.get("relations", [])
        verdict = check_eval.evaluate_signal_facts(signal_facts)
        evidence_item = ael_evidence.make_item(
            kind="gpio.signal",
            source="check.signal_verify",
            ok=verdict.get("ok", False),
            summary=("signal verify passed" if ok else "signal verify failed"),
            facts={
                **signal_facts,
                "failure_kind": (verdict.get("failure_kind", "") if not bool(verdict.get("ok", False)) else ""),
            },
            artifacts={
                "measure_json": measure_path,
                "observe_log": log_path,
            },
        )
        if not bool(verdict.get("ok", False)):
            return {
                "ok": False,
                "error_summary": verdict.get("error_summary") or "verify failed",
                "failure_kind": verdict.get("failure_kind", failure_recovery.FAILURE_VERIFICATION_MISMATCH),
                "result": measure,
                "facts": signal_facts,
                "evidence": [evidence_item],
            }
        return {"ok": True, "result": measure, "facts": signal_facts, "evidence": [evidence_item]}


class _NoopRecoveryAdapter:
    def execute(self, action, plan, ctx):
        return {"ok": False, "error_summary": "recovery action not implemented"}


class _SerialResetRecoveryAdapter:
    def execute(self, action, plan, ctx):
        params = action.get("params", {}) if isinstance(action, dict) and isinstance(action.get("params"), dict) else {}
        action_type = str(action.get("type") or "reset.serial").strip()
        out = control_reset_serial.run(params, action_type=action_type)
        if out.get("ok"):
            return out
        msg = str(out.get("error_summary") or "")
        if action_type == "reset.serial":
            msg = msg.replace("control.reset.serial", "reset.serial")
            out["error_summary"] = msg
        return out


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


class _MailboxVerifyAdapter:
    def execute(self, step, plan, ctx):
        return check_mailbox_verify.execute(step, plan, ctx)


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
            "check.mailbox_verify": _MailboxVerifyAdapter(),
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
            "control.reset.serial": _SerialResetRecoveryAdapter(),
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
