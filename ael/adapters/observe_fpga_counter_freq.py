"""
observe_fpga_counter_freq.py — Multi-channel frequency measurement for FPGA counter probe outputs.

Captures N LA channels simultaneously, computes per-channel frequency and duty cycle,
then verifies:
  - Each channel's measured frequency vs expected_hz (within freq_tol)
  - Duty cycle ~50% (within duty_tol)
  - Adjacent-channel ratios match expected_ratios list (default: all 2.0)

Pin mapping (S3JTAG PA group):
  PA0 → LA bit 0,  PA1 → LA bit 1,  PA2 → LA bit 2,  PA3 → LA bit 3

Usage from experiment script:
  from ael.adapters import observe_fpga_counter_freq
  result = observe_fpga_counter_freq.run(probe_cfg, channels=[...])
"""

from __future__ import annotations

from typing import Any

import requests
from requests.auth import HTTPBasicAuth

_SAMPLE_RATE_HZ = 264_000_000   # max S3JTAG LA rate

_PIN_BIT_MAP = {
    "PA0": 0, "PA1": 1, "PA2": 2, "PA3": 3,
    "PA4": 4, "PA5": 5, "PA6": 6, "PA7": 7,
    "PB0": 8, "PB1": 9, "PB2": 10, "PB3": 11,
}


def _pin_to_bit(pin: str) -> int:
    p = pin.strip().upper()
    if p in _PIN_BIT_MAP:
        return _PIN_BIT_MAP[p]
    if p.isdigit():
        return int(p)
    if "." in p:
        return int(p.split(".")[-1])
    raise ValueError(f"Unknown LA pin: {pin!r}")


def _disable_ssl_warnings() -> None:
    try:
        import urllib3
        from urllib3.exceptions import InsecureRequestWarning
        urllib3.disable_warnings(InsecureRequestWarning)
    except Exception:
        pass


def _configure_la(base_url: str, auth, verify_ssl: bool, bits: list[int]) -> None:
    channels = ["disabled"] * 16
    for b in bits:
        if 0 <= b < 16:
            channels[b] = "enabled"
    payload = {
        "sampleRate": _SAMPLE_RATE_HZ,
        "triggerPosition": 50,
        "triggerEnabled": False,
        "triggerModeOR": True,
        "captureInternalTestSignal": False,
        "channels": channels,
    }
    r = requests.post(
        f"{base_url}/la_configure",
        json=payload,
        headers={"Content-Type": "application/json"},
        auth=auth,
        timeout=5,
        verify=verify_ssl,
    )
    r.raise_for_status()


def _instant_capture(base_url: str, auth, verify_ssl: bool) -> bytes:
    r = requests.get(f"{base_url}/instant_capture", auth=auth, timeout=10, verify=verify_ssl)
    r.raise_for_status()
    return r.content


def _parse_samples(blob: bytes) -> list[int]:
    """Decode raw LA blob into list of 16-bit sample words."""
    data = list(blob)
    words: list[int] = []
    for n in range(0, len(data) - 4, 2):
        low  = data[n + 2]
        high = data[n + 1]
        words.append((high << 8) | low)
    return words


def _measure_channel(words: list[int], bit: int, sample_rate_hz: int) -> dict[str, Any]:
    """Compute frequency, duty cycle, and edge count for one channel bit."""
    if not words:
        return {"freq_hz": 0.0, "duty": 0.0, "edges": 0, "window_s": 0.0}

    bits_seq = [(w >> bit) & 1 for w in words]
    edges = sum(1 for i in range(1, len(bits_seq)) if bits_seq[i] != bits_seq[i - 1])
    high = bits_seq.count(1)
    total = len(bits_seq)
    window_s = total / sample_rate_hz
    freq_hz = edges / (2.0 * window_s) if window_s > 0 else 0.0
    duty = high / total if total > 0 else 0.0
    return {
        "freq_hz": freq_hz,
        "duty": duty,
        "edges": edges,
        "window_s": window_s,
        "high": high,
        "low": total - high,
        "total_samples": total,
    }


def run(
    probe_cfg: dict[str, Any],
    channels: list[dict[str, Any]],
    freq_tol: float = 0.005,      # 0.5% frequency tolerance
    duty_tol: float = 0.02,       # ±2% duty cycle tolerance around 50%
    expected_ratios: list[float] | None = None,  # ratio between adjacent channels; default all 2.0
    ratio_tol: float = 0.005,     # 0.5% ratio tolerance
) -> dict[str, Any]:
    """
    Capture and verify FPGA counter frequency outputs.

    channels: list of dicts, each:
      { "pin": "PA0", "expected_hz": 25_000_000, "label": "cnt[1]" }

    Returns dict with keys:
      ok, channels (per-channel results), ratios, errors
    """
    ip          = probe_cfg.get("ip")
    scheme      = probe_cfg.get("web_scheme", "https")
    port        = int(probe_cfg.get("web_port", 443))
    user        = probe_cfg.get("web_user", "admin")
    password    = probe_cfg.get("web_pass", "admin")
    verify_ssl  = bool(probe_cfg.get("web_verify_ssl", False))

    _disable_ssl_warnings()

    base_url = f"{scheme}://{ip}:{port}"
    auth     = HTTPBasicAuth(user, password)

    bits = [_pin_to_bit(ch["pin"]) for ch in channels]

    # --- Configure and capture ---
    try:
        _configure_la(base_url, auth, verify_ssl, bits)
    except Exception as exc:
        return {"ok": False, "errors": [f"la_configure failed: {exc}"], "channels": [], "ratios": []}

    try:
        blob = _instant_capture(base_url, auth, verify_ssl)
    except Exception as exc:
        return {"ok": False, "errors": [f"instant_capture failed: {exc}"], "channels": [], "ratios": []}

    if len(blob) < 10:
        return {"ok": False, "errors": ["capture returned too few bytes"], "channels": [], "ratios": []}

    words = _parse_samples(blob)
    if not words:
        return {"ok": False, "errors": ["no samples decoded"], "channels": [], "ratios": []}

    # --- Measure each channel ---
    channel_results: list[dict[str, Any]] = []
    errors: list[str] = []

    for i, ch in enumerate(channels):
        bit        = bits[i]
        label      = ch.get("label", ch["pin"])
        expected   = float(ch.get("expected_hz", 0))
        m          = _measure_channel(words, bit, _SAMPLE_RATE_HZ)

        measured   = m["freq_hz"]
        duty       = m["duty"]

        # frequency check
        if expected > 0 and measured > 0:
            rel_err = abs(measured - expected) / expected
            freq_ok = rel_err <= freq_tol
        else:
            freq_ok = m["edges"] > 0
            rel_err = float("nan")

        # duty cycle check
        duty_ok = abs(duty - 0.5) <= duty_tol

        ch_result = {
            "pin":        ch["pin"],
            "bit":        bit,
            "label":      label,
            "expected_hz": expected,
            "measured_hz": round(measured, 1),
            "rel_err_pct": round(rel_err * 100, 4) if not (rel_err != rel_err) else None,
            "freq_ok":    freq_ok,
            "duty":       round(duty, 4),
            "duty_ok":    duty_ok,
            "edges":      m["edges"],
            "window_s":   round(m["window_s"], 6),
        }
        channel_results.append(ch_result)

        if not freq_ok:
            errors.append(
                f"CH{i} {label}: freq={measured:.0f} Hz expected={expected:.0f} Hz "
                f"err={rel_err*100:.3f}% (tol={freq_tol*100:.1f}%)"
            )
        if not duty_ok:
            errors.append(
                f"CH{i} {label}: duty={duty:.3f} expected=0.500 (tol=±{duty_tol:.3f})"
            )

        print(
            f"  CH{i} {label:12s}  bit={bit}  "
            f"measured={measured/1e6:8.4f} MHz  expected={expected/1e6:.4f} MHz  "
            f"err={rel_err*100:+.3f}%  duty={duty:.3f}  edges={m['edges']}"
        )

    # --- Ratio checks between adjacent channels ---
    if expected_ratios is None:
        expected_ratios = [2.0] * (len(channels) - 1)

    ratio_results: list[dict[str, Any]] = []
    for i in range(len(channels) - 1):
        f_hi = channel_results[i]["measured_hz"]
        f_lo = channel_results[i + 1]["measured_hz"]
        exp_r = expected_ratios[i] if i < len(expected_ratios) else 2.0
        if f_lo > 0:
            actual_r = f_hi / f_lo
            r_err = abs(actual_r - exp_r) / exp_r
            ratio_ok = r_err <= ratio_tol
        else:
            actual_r = 0.0
            r_err = float("nan")
            ratio_ok = False

        ratio_result = {
            "ch_hi": i,
            "ch_lo": i + 1,
            "expected_ratio": exp_r,
            "actual_ratio":   round(actual_r, 6),
            "rel_err_pct":    round(r_err * 100, 4) if not (r_err != r_err) else None,
            "ratio_ok":       ratio_ok,
        }
        ratio_results.append(ratio_result)

        if not ratio_ok:
            errors.append(
                f"Ratio CH{i}/CH{i+1}: {actual_r:.6f} expected={exp_r:.1f} "
                f"err={r_err*100:.3f}% (tol={ratio_tol*100:.1f}%)"
            )
        print(
            f"  Ratio CH{i}/CH{i+1}: {actual_r:.6f}  expected={exp_r:.1f}  "
            f"err={r_err*100:+.4f}%  {'OK' if ratio_ok else 'FAIL'}"
        )

    ok = len(errors) == 0
    return {
        "ok":       ok,
        "channels": channel_results,
        "ratios":   ratio_results,
        "errors":   errors,
        "sample_rate_hz": _SAMPLE_RATE_HZ,
        "total_samples":  len(words),
    }
