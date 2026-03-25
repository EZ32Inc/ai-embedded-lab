#!/usr/bin/env python3
"""
ESP32JTAG — Port B SRESET Signal Validation
============================================

Physical wiring required:
  Port B pin3 ──── Port A pin3   (SRESET → LA CH3)

Board configuration:
  - Port A: Logic Analyzer  (default)
  - Port B: Vtarget + UART + SReset  ← auto-configured by this script

The test:
  1. Ensure Port B is in Vtarget+UART+SReset mode (saves NVS + reboots if needed)
  2. Configure LA at 260 kHz, CH3 crossing trigger, trigger_position=60
     (100.5 ms pre-trigger + 151.6 ms post-trigger = 252 ms window)
  3. Arm triggered capture (GET /la_start_capture) — fast, non-blocking
  4. Fire reset on same HTTP connection (POST /api/reset_target — 100 ms pulse)
  5. Wait for FPGA to finish post-trigger sampling (300 ms)
  6. Fetch /capture_data, reorder ring buffer by wr_addr_stop_position
  7. Measure pulse width: expect 100 ms ± 20% (80–120 ms)

Notes
-----
- SRESET idle level is LOW (bit=0 → pin driven LOW by FPGA).
  Reset pulse drives pin HIGH for 100 ms.
- Serial HTTP requests on the same session avoid the 600 ms HTTPS
  re-handshake penalty that would occur if a second concurrent
  connection were needed.
- trigger_position=60 → trigger_pos_in_samples=39410 (firmware formula).

Usage
-----
  python experiments/esp32jtag/portb_reset_test.py --ip 192.168.2.62
  python experiments/esp32jtag/portb_reset_test.py --ip 192.168.2.62 --verbose

Exit codes
----------
  0 — test passed
  1 — test failed
  2 — setup / connectivity error
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings

import requests
from requests.auth import HTTPBasicAuth

# ── constants ────────────────────────────────────────────────────────────────

SAMPLE_RATE_LOW  = 260_000          # Hz — 252 ms capture window
SAMPLE_RATE_HIGH = 264_000_000      # Hz — restored after test

RESET_PULSE_MS     = 100
PULSE_MS_TOLERANCE = 0.20           # ±20 %
PULSE_MS_MIN       = RESET_PULSE_MS * (1 - PULSE_MS_TOLERANCE)
PULSE_MS_MAX       = RESET_PULSE_MS * (1 + PULSE_MS_TOLERANCE)

CH_RESET          = 3               # Port A pin3 — wired to Port B pin3
TRIGGER_POSITION  = 60              # %: 100.5 ms pre / 151.6 ms post-trigger
POST_TRIGGER_WAIT = 0.30            # s — extra margin after reset completes


# ── HTTP client ───────────────────────────────────────────────────────────────

class ESP32JTAGClient:
    def __init__(self, ip, user="admin", password="admin",
                 scheme="https", port=443, timeout=20.0, verbose=False):
        self.base    = f"{scheme}://{ip}:{port}"
        self.auth    = HTTPBasicAuth(user, password)
        self.timeout = timeout
        self.verbose = verbose
        self._sess   = requests.Session()
        self._sess.auth   = self.auth
        self._sess.verify = False
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    def _get(self, path):
        r = self._sess.get(f"{self.base}{path}", timeout=self.timeout)
        r.raise_for_status()
        return r

    def _post(self, path, payload):
        r = self._sess.post(f"{self.base}{path}", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r

    def get_version(self):
        return self._get("/api/version").json()

    def get_portb_mode(self):
        try:
            return int(self._get("/get_credentials").json().get("pbcfg", -1))
        except Exception:
            return -1

    def save_portb_uart_mode(self):
        try:
            self._post("/set_credentials", {"pbcfg": "1"})
        except Exception:
            pass    # device may reboot before responding

    def la_configure(self, *, sample_rate=None, trigger_enabled=None,
                     channels=None, trigger_position=None):
        payload = {}
        if sample_rate      is not None: payload["sampleRate"]      = sample_rate
        if trigger_enabled  is not None: payload["triggerEnabled"]  = trigger_enabled
        if channels         is not None: payload["channels"]        = channels
        if trigger_position is not None: payload["triggerPosition"] = trigger_position
        r = self._post("/la_configure", payload)
        assert r.json().get("status") == "ok"

    def la_start_capture(self):
        return self._get("/la_start_capture").json()

    def la_status(self):
        return self._get("/la_status").json()

    def reset_target(self):
        j = self._post("/api/reset_target", {}).json()
        if j.get("status") != "ok":
            raise RuntimeError(f"reset_target: {j.get('message')}")
        return j

    def capture_data(self) -> bytes:
        return self._get("/capture_data").content


# ── ring-buffer helpers ───────────────────────────────────────────────────────

def _reorder_ringbuf(raw: bytes, wr_stop: int, ch: int) -> list[int]:
    """
    Return chronologically ordered bit-list for channel `ch`.
    Ring buffer: oldest sample at physical address wr_stop,
                 newest at wr_stop-1 (wraps mod n_samples).
    """
    n       = len(raw) // 2
    byte_i  = ch // 8
    bit_m   = 1 << (ch % 8)
    order   = list(range(wr_stop, n)) + list(range(0, wr_stop))
    return [1 if (raw[i * 2 + byte_i] & bit_m) else 0 for i in order]


def _find_transitions(bits: list[int]) -> list[tuple]:
    """Return list of (sample_idx, from_level, to_level, time_ms)."""
    sr = SAMPLE_RATE_LOW
    out = []
    for i in range(1, len(bits)):
        if bits[i] != bits[i-1]:
            out.append((i, bits[i-1], bits[i], i / sr * 1000.0))
    return out


# ── main test logic ──────────────────────────────────────────────────────────

def run_test(ip, user="admin", password="admin",
             scheme="https", port=443, verbose=False) -> bool:

    client = ESP32JTAGClient(ip=ip, user=user, password=password,
                             scheme=scheme, port=port, verbose=verbose)

    # ── Phase 0: connectivity ─────────────────────────────────────────────────
    print(f"[setup] Connecting to {client.base} …")
    try:
        ver = client.get_version()
        print(f"[setup] Firmware {ver.get('firmware_version')}  "
              f"build {ver.get('build_date')}  commit {ver.get('main_git_commit')}")
    except requests.exceptions.ConnectionError as exc:
        print(f"[error] Cannot reach device: {exc}")
        sys.exit(2)
    except Exception as exc:
        print(f"[error] {exc}")
        sys.exit(2)

    # ── Phase 1: ensure Port B is in UART+SReset mode ────────────────────────
    pb_mode = client.get_portb_mode()
    if verbose:
        print(f"[setup] Port B mode: {pb_mode}")

    if pb_mode != 1:
        print(f"[setup] Port B mode={pb_mode}, need 1 (UART+SReset). Saving + rebooting …")
        client.save_portb_uart_mode()
        print("[setup] Waiting for reboot …", end="", flush=True)
        time.sleep(6)
        for _ in range(30):
            try:
                client.get_version()
                print(" online.")
                break
            except Exception:
                print(".", end="", flush=True)
                time.sleep(1)
        else:
            print("\n[error] Device did not come back after reboot.")
            sys.exit(2)

    print("[setup] Port B = Vtarget+UART+SReset ✓")

    # ── Phase 2: configure LA ────────────────────────────────────────────────
    # trigger_position=60 → 100.5 ms pre-trigger, 151.6 ms post-trigger at 260 kHz
    channels_cfg = ["disabled"] * 16
    channels_cfg[CH_RESET] = "crossing"     # any edge (signal is idle-LOW, pulse-HIGH)

    try:
        client.la_configure(
            sample_rate      = SAMPLE_RATE_LOW,
            trigger_enabled  = True,
            trigger_position = TRIGGER_POSITION,
            channels         = channels_cfg,
        )
        print(f"[setup] LA @ {SAMPLE_RATE_LOW/1000:.0f} kHz, "
              f"CH{CH_RESET}=crossing, triggerPosition={TRIGGER_POSITION}")

        # ── Phase 3: arm capture (non-blocking) ──────────────────────────────
        arm = client.la_start_capture()
        if verbose:
            print(f"[test]  Capture armed: {arm}")

        # ── Phase 4: fire reset (serial on same connection) ──────────────────
        # Uses keep-alive connection → no TLS re-handshake → RTT ≈ 157 ms
        print("[test]  Firing SRESET pulse …")
        t_reset = time.monotonic()
        client.reset_target()
        rtt_ms = (time.monotonic() - t_reset) * 1000
        print(f"[test]  Reset complete (RTT {rtt_ms:.0f} ms)")

        # ── Phase 5: wait for FPGA post-trigger fill ─────────────────────────
        time.sleep(POST_TRIGGER_WAIT)
        st = client.la_status()
        if verbose:
            print(f"[test]  la_status: {st}")

        if not st.get("triggered"):
            print("[error] Capture never triggered — SRESET edge not detected.")
            return False

        # ── Phase 6: retrieve capture data ───────────────────────────────────
        raw      = client.capture_data()
        wr_stop  = st["wr_addr_stop_position"]
        post_trig = st["trigger_position"]      # post-trigger sample count
        n_samples = len(raw) // 2

        if verbose:
            print(f"[test]  Received {len(raw)} bytes, "
                  f"wr_stop={wr_stop}, post_trig={post_trig}")

    finally:
        client.la_configure(
            sample_rate     = SAMPLE_RATE_HIGH,
            trigger_enabled = True,
            channels        = ["disabled"] * 16,
        )
        if verbose:
            print(f"[setup] LA restored to {SAMPLE_RATE_HIGH//1_000_000} MHz")

    # ── Phase 7: analyse ──────────────────────────────────────────────────────
    bits        = _reorder_ringbuf(raw, wr_stop, CH_RESET)
    transitions = _find_transitions(bits)
    window_ms   = n_samples / SAMPLE_RATE_LOW * 1000.0
    pre_ms      = (n_samples - post_trig) / SAMPLE_RATE_LOW * 1000.0

    if verbose:
        low_pct = bits.count(0) / len(bits) * 100
        print(f"\n  CH{CH_RESET}: {n_samples} samples, window={window_ms:.1f} ms, "
              f"LOW={low_pct:.1f}%")
        print(f"  Trigger at chronological sample "
              f"{n_samples - post_trig} = {pre_ms:.1f} ms")
        print(f"  All transitions:")
        for idx, frm, to, ms in transitions:
            mark = " ← trigger" if abs(idx - (n_samples - post_trig)) < 50 else ""
            print(f"    {idx:6d} = {ms:7.2f} ms  {frm}→{to}{mark}")

    print()

    # Need exactly 2 transitions (rising + falling or falling + rising)
    if len(transitions) < 2:
        print(f"FAIL — fewer than 2 transitions detected ({len(transitions)} found)")
        print(f"       Check wiring: Port B pin3 → Port A pin3")
        return False

    t_start_ms = transitions[0][3]
    t_end_ms   = transitions[1][3]
    pulse_ms   = t_end_ms - t_start_ms
    idle_level = transitions[0][1]
    active_level = transitions[0][2]

    in_range = PULSE_MS_MIN <= pulse_ms <= PULSE_MS_MAX
    verdict  = "PASS" if in_range else "FAIL"

    print(f"{'='*54}")
    print(f"  Port B SRESET pulse test")
    print(f"{'='*54}")
    print(f"  Signal: idle={'HIGH' if idle_level else 'LOW'} → "
          f"pulse={'HIGH' if active_level else 'LOW'}")
    print(f"  Expected : {RESET_PULSE_MS} ms "
          f"(±{PULSE_MS_TOLERANCE*100:.0f}%: {PULSE_MS_MIN:.0f}–{PULSE_MS_MAX:.0f} ms)")
    print(f"  Measured : {pulse_ms:.2f} ms")
    print(f"  Pulse start (ms) : {t_start_ms:.2f}")
    print(f"  Pulse end   (ms) : {t_end_ms:.2f}")
    print(f"  Capture window   : {window_ms:.1f} ms")
    print(f"{'='*54}")
    print(f"  Result: {verdict}")
    print(f"{'='*54}")

    return in_range


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ESP32JTAG Port B SRESET pulse validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--ip",      required=True,  help="Board IP address")
    parser.add_argument("--user",    default="admin", help="Web username")
    parser.add_argument("--pass",    dest="password", default="admin")
    parser.add_argument("--scheme",  default="https")
    parser.add_argument("--port",    type=int, default=443)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    passed = run_test(
        ip=args.ip, user=args.user, password=args.password,
        scheme=args.scheme, port=args.port, verbose=args.verbose,
    )
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
