from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from urllib import error, request


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _artifacts_dir(step: Dict[str, Any], ctx: Any) -> Path:
    inputs = step.get("inputs", {}) if isinstance(step, dict) else {}
    run_dir = inputs.get("run_dir")
    if run_dir:
        return Path(run_dir) / "artifacts"
    if ctx is not None and getattr(ctx, "artifacts_dir", None):
        return Path(ctx.artifacts_dir)
    return Path("run") / "artifacts"


def _default_evidence_name(capability: str) -> str:
    mapping = {
        "measure.voltage": "instrument_voltage.json",
        "measure.digital": "instrument_digital.json",
        "selftest": "instrument_selftest.json",
        "control.reset_target": "instrument_reset_target.json",
    }
    return mapping.get(str(capability), "instrument_response.json")


def _endpoint(cfg: Dict[str, Any]) -> str:
    if cfg.get("url"):
        return str(cfg.get("url")).rstrip("/")
    scheme = str(cfg.get("scheme", "http"))
    host = str(cfg.get("host", "127.0.0.1"))
    port = int(cfg.get("port", 9000))
    return f"{scheme}://{host}:{port}"


def _post_json(url: str, payload: Dict[str, Any], timeout_s: float) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise RuntimeError("AIP response must be a JSON object")
    return data


def execute(step: Dict[str, Any], plan: Dict[str, Any], ctx: Any) -> Dict[str, Any]:
    inputs = step.get("inputs", {}) if isinstance(step, dict) else {}
    instrument_cfg = inputs.get("instrument", {}) if isinstance(inputs.get("instrument"), dict) else {}

    capability = str(inputs.get("capability", "")).strip()
    if not capability:
        return {"ok": False, "error_summary": "capability not set"}

    call_payload = {
        "capability": capability,
        "params": inputs.get("params", {}),
        "context": {
            "plan_id": (plan or {}).get("plan_id", ""),
            "step": step.get("name", ""),
        },
    }

    timeout_s = float(inputs.get("timeout_s", instrument_cfg.get("timeout_s", 5.0)))
    url = _endpoint(instrument_cfg) + "/aip/v0.1/call"

    try:
        response = _post_json(url, call_payload, timeout_s)
    except error.HTTPError as exc:
        return {"ok": False, "error_summary": f"AIP HTTP error: {exc.code}"}
    except error.URLError as exc:
        return {"ok": False, "error_summary": f"AIP connection error: {exc.reason}"}
    except Exception as exc:
        return {"ok": False, "error_summary": f"AIP request failed: {exc}"}

    artifacts_dir = _artifacts_dir(step, ctx)

    evidence_files = inputs.get("evidence_files", {}) if isinstance(inputs.get("evidence_files"), dict) else {}
    written = []

    evidence_payload = response.get("evidence") if isinstance(response.get("evidence"), dict) else None
    if evidence_payload:
        for name, payload in evidence_payload.items():
            file_name = str(name).strip() or _default_evidence_name(capability)
            out_path = artifacts_dir / file_name
            _write_json(out_path, payload if isinstance(payload, dict) else {"value": payload})
            written.append(str(out_path))

    if not written:
        file_name = str(evidence_files.get(capability, _default_evidence_name(capability)))
        out_path = artifacts_dir / file_name
        _write_json(out_path, response)
        written.append(str(out_path))

    ok = bool(response.get("ok", True))
    if not ok:
        return {
            "ok": False,
            "error_summary": str(response.get("error_summary", "instrument call failed")),
            "result": response,
            "artifacts": written,
        }

    return {"ok": True, "result": response, "artifacts": written}
