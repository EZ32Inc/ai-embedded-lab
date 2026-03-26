import time
from typing import List

import requests
from requests.auth import HTTPBasicAuth

SUPPORTED_RATES = [
    264_000_000,
    132_000_000,
    66_000_000,
    33_000_000,
    22_000_000,
    16_500_000,
    11_000_000,
    6_000_000,
    3_000_000,
    2_000_000,
    1_000_000,
    500_000,
    260_000,
]


def _maybe_disable_ssl_warnings(verify_ssl: bool, suppress: bool) -> None:
    if verify_ssl or not suppress:
        return
    try:
        import urllib3
        from urllib3.exceptions import InsecureRequestWarning

        urllib3.disable_warnings(InsecureRequestWarning)
    except Exception:
        pass


def _choose_sample_rate(target_window_s: float, samples_hint: int = 65536) -> int:
    if target_window_s <= 0:
        return 1_000_000
    desired = int(samples_hint / target_window_s)
    return min(SUPPORTED_RATES, key=lambda r: abs(r - desired))


def _parse_samples(buffer: bytes) -> List[int]:
    data = list(buffer)
    words = []
    for n in range(0, len(data) - 4, 2):
        low = data[n + 2]
        high = data[n + 1]
        words.append((high << 8) | low)
    return words


def _count_edges(bits: List[int]) -> int:
    if not bits:
        return 0
    edges = 0
    prev = bits[0]
    for b in bits[1:]:
        if b != prev:
            edges += 1
        prev = b
    return edges


def _extract_bit(words: List[int], bit: int) -> List[int]:
    return [(w >> bit) & 0x1 for w in words]


def _edge_counts_all_bits(words: List[int], bits: int = 16) -> List[int]:
    counts = [0] * bits
    if not words:
        return counts
    prev = [(words[0] >> i) & 0x1 for i in range(bits)]
    for w in words[1:]:
        for i in range(bits):
            b = (w >> i) & 0x1
            if b != prev[i]:
                counts[i] += 1
                prev[i] = b
    return counts


def _configure_la(base_url, auth, verify_ssl, sample_rate_hz, trigger_enabled, trigger_position, trigger_mode_or,
                  capture_internal_test_signal, channels):
    payload = {
        "sampleRate": int(sample_rate_hz),
        "triggerPosition": int(trigger_position),
        "triggerEnabled": bool(trigger_enabled),
        "triggerModeOR": bool(trigger_mode_or),
        "captureInternalTestSignal": bool(capture_internal_test_signal),
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
    return r.json() if r.content else {}


def _instant_capture(base_url, auth, verify_ssl) -> bytes:
    r = requests.get(f"{base_url}/instant_capture", auth=auth, timeout=10, verify=verify_ssl)
    r.raise_for_status()
    return r.content


def _triggered_capture(base_url, auth, verify_ssl, timeout_s=5.0) -> bytes:
    r = requests.get(f"{base_url}/la_start_capture", auth=auth, timeout=5, verify=verify_ssl)
    r.raise_for_status()

    start = time.time()
    while True:
        status = requests.get(f"{base_url}/la_status", auth=auth, timeout=5, verify=verify_ssl).json()
        if status.get("triggered"):
            break
        if time.time() - start > timeout_s:
            raise TimeoutError("LA trigger timeout")
        time.sleep(0.1)

    r = requests.get(f"{base_url}/capture_data", auth=auth, timeout=10, verify=verify_ssl)
    r.raise_for_status()
    return r.content


def _run_targetin_detect(base_url, auth, verify_ssl, pin_name: str, capture_out=None, expected_state: str | None = None,
                         min_edges: int = 1) -> bool:
    start = requests.post(
        f"{base_url}/test/start",
        json={"test_type": "test_targetin_detect"},
        headers={"Content-Type": "application/json"},
        auth=auth,
        timeout=10,
        verify=verify_ssl,
    )
    start.raise_for_status()

    deadline = time.time() + 10.0
    while time.time() < deadline:
        status_resp = requests.get(f"{base_url}/test/status", auth=auth, timeout=10, verify=verify_ssl)
        status_resp.raise_for_status()
        status_payload = status_resp.json() if status_resp.content else {}
        if str(status_payload.get("state") or "").lower() in {"completed", "done", "idle"}:
            break
        time.sleep(0.2)

    result_resp = requests.get(f"{base_url}/test/result", auth=auth, timeout=10, verify=verify_ssl)
    result_resp.raise_for_status()
    result = result_resp.json() if result_resp.content else {}

    if capture_out is not None:
        capture_out["targetin_result"] = dict(result)
        capture_out["pin"] = pin_name
        capture_out["pins"] = [pin_name]
        capture_out["pin_bits"] = {pin_name: 0}
        capture_out["bit"] = 0
        capture_out["sample_rate_hz"] = int(result.get("estimated_hz") or 0) * 2 or 2000
        capture_out["window_s"] = float(result.get("samples") or 0) / 40000.0 if result.get("samples") else 0.25
        capture_out["edges"] = int(result.get("transitions") or 0)
        capture_out["high"] = int(result.get("high") or 0)
        capture_out["low"] = int(result.get("low") or 0)
        capture_out["blob"] = b"TARGETIN"

    state = str(result.get("state") or "").strip().lower()
    transitions = int(result.get("transitions") or 0)
    expected = str(expected_state or "toggle").strip().lower() or "toggle"
    if expected in {"high", "low"}:
        ok = state == expected
    else:
        ok = (
            str(result.get("result") or "").strip().lower() == "pass"
            and state == "toggle"
            and transitions >= int(min_edges)
        )
    if ok:
        print(
            "Verify: TARGETIN detect OK "
            f"state={state} samples={int(result.get('samples') or 0)} transitions={transitions} "
            f"estimated_hz={int(result.get('estimated_hz') or 0)}"
        )
    else:
        print(f"Verify: TARGETIN detect failed ({result})")
    return ok


def _bit_from_pin(pin: str) -> int:
    if not pin:
        return -1
    # Expect formats like "P0.1" or "1"
    if pin.isdigit():
        return int(pin)
    p = pin.strip().upper()
    # Expect PA0..PA7 and PB0..PD3 mapping to bit 0..15
    if len(p) == 3 and p[0] == "P" and p[1] in ("A", "B", "C", "D") and p[2].isdigit():
        idx = int(p[2])
        if p[1] == "A" and 0 <= idx <= 7:
            return idx
        if 0 <= idx <= 3:
            base = {"A": 0, "B": 4, "C": 8, "D": 12}[p[1]]
            return base + idx
    if "." in pin:
        return int(pin.split(".")[-1])
    return -1


def run(probe_cfg, pin, duration_s, expected_hz, min_edges, max_edges, capture_out=None, verify_edges=True, pins=None,
        expected_state: str | None = None):
    ip = probe_cfg.get("ip")
    scheme = probe_cfg.get("web_scheme", "https")
    port = int(probe_cfg.get("web_port", 443))
    user = probe_cfg.get("web_user", "admin")
    password = probe_cfg.get("web_pass", "admin")
    verify_ssl = bool(probe_cfg.get("web_verify_ssl", False))
    suppress_ssl_warnings = bool(probe_cfg.get("web_suppress_ssl_warnings", False))
    sample_rate = int(probe_cfg.get("la_sample_rate", 0)) or _choose_sample_rate(duration_s)

    normalized_pins = []
    seen_pins = set()
    for candidate in [pin, *list(pins or [])]:
        text = str(candidate or "").strip()
        if not text or text in seen_pins:
            continue
        seen_pins.add(text)
        normalized_pins.append(text)

    if not normalized_pins:
        print("Verify: no capture pins configured.")
        return False

    bit_map = {name: _bit_from_pin(name) for name in normalized_pins}
    base_url = f"{scheme}://{ip}:{port}"
    auth = HTTPBasicAuth(user, password)

    _maybe_disable_ssl_warnings(verify_ssl, suppress_ssl_warnings)

    if all(str(name).strip().upper() == "TARGETIN" for name in normalized_pins):
        print(f"Verify: TARGETIN host={base_url} duration~{duration_s:.2f}s")
        return _run_targetin_detect(
            base_url,
            auth,
            verify_ssl,
            normalized_pins[0],
            capture_out=capture_out,
            expected_state=expected_state,
            min_edges=min_edges,
        )

    invalid = [name for name, bit in bit_map.items() if bit < 0 or bit > 15]
    if invalid:
        print(f"Verify: invalid LA bit from pin '{invalid[0]}'. Use P0.x or 0..15.")
        return False
    bit = bit_map[normalized_pins[0]]

    print(
        "Verify: LA host="
        f"{base_url} bits={','.join(str(bit_map[name]) for name in normalized_pins)} "
        f"duration~{duration_s:.2f}s sample_rate={sample_rate}"
    )

    channels = ["disabled"] * 16
    for enabled_bit in bit_map.values():
        if 0 <= enabled_bit < len(channels):
            channels[enabled_bit] = "enabled"

    try:
        _configure_la(
            base_url,
            auth,
            verify_ssl,
            sample_rate_hz=sample_rate,
            trigger_enabled=False,
            trigger_position=50,
            trigger_mode_or=True,
            capture_internal_test_signal=False,
            channels=channels,
        )
    except Exception as exc:
        print(f"Verify: configure failed ({exc})")
        print("Verify: check network/auth or webserver availability.")
        return False

    try:
        blob = _instant_capture(base_url, auth, verify_ssl)
    except Exception as exc:
        print(f"Verify: capture failed ({exc})")
        return False

    if len(blob) < 10:
        print("Verify: capture returned too few bytes")
        return False

    words = _parse_samples(blob)
    if not words:
        print("Verify: no samples decoded")
        return False

    bits = _extract_bit(words, bit)
    edges = _count_edges(bits)
    low = bits.count(0)
    high = bits.count(1)
    window_s = len(words) / float(sample_rate)
    edge_counts = _edge_counts_all_bits(words)

    if capture_out is not None:
        capture_out["blob"] = blob
        capture_out["sample_rate_hz"] = sample_rate
        capture_out["bit"] = bit
        capture_out["pins"] = list(normalized_pins)
        capture_out["pin_bits"] = dict(bit_map)
        capture_out["window_s"] = window_s
        capture_out["edges"] = edges
        capture_out["high"] = high
        capture_out["low"] = low
        capture_out["edge_counts"] = edge_counts

    print(f"Verify: samples={len(words)} window={window_s:.4f}s edges={edges} high={high} low={low}")

    if not verify_edges:
        print("Verify: capture OK (edge checks skipped)")
        return True
    if edges == 0:
        print("Verify: Bit never changes (stuck high/low).")
        counts = _edge_counts_all_bits(words)
        top = sorted(enumerate(counts), key=lambda x: x[1], reverse=True)[:4]
        print("Verify: edge counts by bit (top 4): " + ", ".join([f"bit{b}={c}" for b, c in top]))
        print("Verify: Hint: verify mapping PA0..PD3 -> bit0..15. Try verify=PA0/PA1/PA2/PA3.")
        return False
    if edges < min_edges:
        print("Verify: Only 1 edge or too few edges. Consider lower sample rate or faster blink.")
        return False
    if edges > max_edges:
        print("Verify: Too many edges (unexpected high frequency).")
        return False

    print("Verify: OK")
    return True
