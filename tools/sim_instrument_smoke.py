#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ael.adapter_registry import AdapterRegistry
from ael.runner import run_plan


def main() -> int:
    run_dir = Path("/tmp/ael_sim_instrument_smoke_run")
    if run_dir.exists():
        shutil.rmtree(run_dir)

    plan = {
        "version": "runplan/0.1",
        "plan_id": "sim-instrument-smoke",
        "steps": [
            {
                "name": "digital_signature",
                "type": "instrument.sim_http.measure.digital",
                "inputs": {
                    "params": {"pins": [4, 5, 6, 7]},
                    "evidence_file": "instrument_digital.json",
                },
            },
            {
                "name": "voltage_measure",
                "type": "instrument.sim_http.measure.voltage",
                "inputs": {
                    "params": {"channel": "ad0"},
                    "instrument": {"seed": 12345, "noise_v": 0.002},
                    "evidence_file": "instrument_voltage.json",
                },
            },
            {
                "name": "uart_capture",
                "type": "instrument.sim_http.uart_log",
                "inputs": {
                    "params": {"ready_count": 4},
                    "evidence_file": "uart_log.json",
                },
            },
        ],
    }

    result = run_plan(plan, run_dir, AdapterRegistry())
    artifacts = run_dir / "artifacts"
    assert result.get("ok") is True, "runner result not ok"
    assert (artifacts / "run_plan.json").exists(), "missing run_plan.json"
    assert (artifacts / "result.json").exists(), "missing result.json"
    assert (artifacts / "instrument_digital.json").exists(), "missing digital evidence"
    assert (artifacts / "instrument_voltage.json").exists(), "missing voltage evidence"
    assert (artifacts / "uart_log.json").exists(), "missing uart evidence"

    print("[SIM_INSTRUMENT_SMOKE] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
