#!/usr/bin/env python3
"""
ESP32JTAG — Port D (P3) → Port A (P0) Loopback Self-Test
=========================================================

Physical wiring required (4 wires, set once):
  P3 pin0 ──── P0 pin0
  P3 pin1 ──── P0 pin1
  P3 pin2 ──── P0 pin2
  P3 pin3 ──── P0 pin3

Board configuration required:
  - Port D: Logic Analyzer (NOT XVC)   ← default
  - Port A: Logic Analyzer             ← default

The test drives signals on Port D and captures them on Port A channels 0–3
via the on-board Logic Analyzer.  No external instruments needed.

Usage
-----
  python experiments/esp32jtag/port_d_loopback.py --ip 192.168.2.62
  python experiments/esp32jtag/port_d_loopback.py --ip 192.168.2.62 --verbose
  python experiments/esp32jtag/port_d_loopback.py --ip 192.168.2.62 --user admin --pass mypass
  python experiments/esp32jtag/port_d_loopback.py --ip 192.168.2.62 --config configs/esp32jtag.yaml

Or via AEL:
  ael run --test tests/plans/esp32jtag_port_d_loopback.json --probe configs/esp32jtag.yaml

Exit codes
----------
  0 — all tests passed
  1 — one or more tests failed
  2 — device unreachable / setup error
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

# Add this script's directory to path for board-specific imports
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from la_loopback_validation import (
    LALoopbackValidator,
    LoopbackResult,
)


# ── Test case definitions ─────────────────────────────────────────────────────

#  GPIO Direct mode (data_reg_1 outsig_sel=11, [3:0]=value)
MODE_TRISTATE    = 0
MODE_COUNTER_LO  = 1
MODE_COUNTER_HI  = 2
MODE_GPIO_DIRECT = 3

#  LA channels: Port A pin0-3 → LA channels 0-3
CHANNELS = [0, 1, 2, 3]

#  Test suite definition
TEST_CASES = [
    # ── Phase 1: Static GPIO ──────────────────────────────────────────────────
    {
        "type": "gpio", "mode": MODE_GPIO_DIRECT, "value": 0b0000,
        "description": "GPIO: all LOW  (0000)",
    },
    {
        "type": "gpio", "mode": MODE_GPIO_DIRECT, "value": 0b1111,
        "description": "GPIO: all HIGH (1111)",
    },
    {
        "type": "gpio", "mode": MODE_GPIO_DIRECT, "value": 0b0101,
        "description": "GPIO: checkerboard A  CH0+CH2 HIGH (0101)",
    },
    {
        "type": "gpio", "mode": MODE_GPIO_DIRECT, "value": 0b1010,
        "description": "GPIO: checkerboard B  CH1+CH3 HIGH (1010)",
    },
    {
        "type": "gpio", "mode": MODE_GPIO_DIRECT, "value": 0b0001,
        "description": "GPIO: CH0 only HIGH (0001)",
    },
    {
        "type": "gpio", "mode": MODE_GPIO_DIRECT, "value": 0b1000,
        "description": "GPIO: CH3 only HIGH (1000)",
    },
    # ── Phase 2: Counter modes ────────────────────────────────────────────────
    {
        "type": "counter", "mode": MODE_COUNTER_LO,
        "description": "Counter Lo  — bits[3:0] of 132 MHz free-counter",
        "duty_range": [0.35, 0.65],
        "check_freq_order": True,
    },
    {
        "type": "counter", "mode": MODE_COUNTER_HI,
        "description": "Counter Hi  — bits[7:4] of 132 MHz free-counter",
        "duty_range": [0.40, 0.60],   # higher bits → more balanced duty at any sample rate
        "check_freq_order": True,
    },
]


# ── ESP32JTAG HTTP helpers ────────────────────────────────────────────────────

class ESP32JTAGClient:
    """Thin HTTP client for ESP32JTAG firmware API."""

    def __init__(
        self,
        ip:       str,
        user:     str = "admin",
        password: str = "admin",
        scheme:   str = "https",
        port:     int = 443,
        timeout:  float = 15.0,
        verbose:  bool = False,
    ) -> None:
        self.base    = f"{scheme}://{ip}:{port}"
        self.auth    = HTTPBasicAuth(user, password)
        self.timeout = timeout
        self.verbose = verbose
        self._sess   = requests.Session()
        self._sess.auth    = self.auth
        self._sess.verify  = False   # self-signed cert
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    def get_version(self) -> dict:
        r = self._sess.get(f"{self.base}/api/version", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def set_portd_output(self, mode: int, value: int = 0) -> dict:
        r = self._sess.post(
            f"{self.base}/api/portd_output",
            json={"mode": mode, "value": value},
            timeout=self.timeout,
        )
        r.raise_for_status()
        j = r.json()
        if j.get("status") != "ok":
            raise RuntimeError(f"portd_output error: {j.get('message')}")
        return j

    def instant_capture(self) -> bytes:
        r = self._sess.get(f"{self.base}/instant_capture", timeout=self.timeout)
        r.raise_for_status()
        return r.content

    def restore_tristate(self) -> None:
        """Best-effort: restore Port D to tristate (LA input) after test."""
        try:
            self.set_portd_output(MODE_TRISTATE, 0)
        except Exception:
            pass


# ── Output and capture callables for LALoopbackValidator ─────────────────────

def _make_driver(client: ESP32JTAGClient):
    def drive(mode: int, value: int = 0) -> None:
        client.set_portd_output(mode, value)
    return drive


def _make_capture(client: ESP32JTAGClient):
    def capture() -> bytes:
        return client.instant_capture()
    return capture


# ── Main test runner ──────────────────────────────────────────────────────────

def run_test(
    ip:      str,
    user:    str  = "admin",
    password: str = "admin",
    scheme:  str  = "https",
    port:    int  = 443,
    verbose: bool = False,
) -> LoopbackResult:
    """
    Connect to the board at ``ip``, run the full Port D loopback suite,
    restore Port D to tristate, and return the LoopbackResult.

    Raises SystemExit(2) on device unreachable / setup errors.
    """
    client = ESP32JTAGClient(
        ip=ip, user=user, password=password,
        scheme=scheme, port=port, verbose=verbose,
    )

    # ── Phase 0: Device discovery ─────────────────────────────────────────────
    print(f"[setup] Connecting to ESP32JTAG at {client.base} …")
    try:
        ver = client.get_version()
        fw  = ver.get("firmware_version", "?")
        hw  = ver.get("hardware_version",  "?")
        git = ver.get("main_git_commit",   "?")
        print(f"[setup] Firmware {fw}  HW {hw}  commit {git}")
    except requests.exceptions.ConnectionError as exc:
        print(f"[error] Cannot reach device at {ip}: {exc}")
        sys.exit(2)
    except requests.exceptions.HTTPError as exc:
        print(f"[error] HTTP error: {exc}")
        sys.exit(2)
    except Exception as exc:
        print(f"[error] Unexpected error: {exc}")
        sys.exit(2)

    # ── Run suite ─────────────────────────────────────────────────────────────
    validator = LALoopbackValidator(
        output_fn  = _make_driver(client),
        capture_fn = _make_capture(client),
        channels   = CHANNELS,
        test_name  = "Port D (P3) → Port A (P0) Loopback",
        settle_ms  = 30,
        verbose    = verbose,
    )

    print(f"[run]   Running {len(TEST_CASES)} test cases …\n")
    result = validator.run_suite(TEST_CASES)

    # ── Cleanup ───────────────────────────────────────────────────────────────
    client.restore_tristate()
    print("[cleanup] Port D restored to tristate (LA input mode)")

    return result


def _load_probe_config(config_path: str) -> dict:
    """Load IP / credentials from an AEL probe YAML config file."""
    try:
        import yaml  # type: ignore
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
        conn    = cfg.get("connection") or {}
        probe   = cfg.get("probe")    or {}
        ip      = conn.get("ip")      or ""
        user    = probe.get("web_user",  "admin")
        password = probe.get("web_pass", "admin")
        scheme  = probe.get("web_scheme",  "https")
        port    = int(probe.get("web_port",  443))
        return {"ip": ip, "user": user, "password": password,
                "scheme": scheme, "port": port}
    except Exception as exc:
        print(f"[warn] Could not load config {config_path!r}: {exc}")
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ESP32JTAG Port D → Port A loopback self-test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--ip",     default="",     help="Board IP address")
    parser.add_argument("--user",   default="admin", help="Web username (default: admin)")
    parser.add_argument("--pass",   dest="password",
                        default="admin", help="Web password (default: admin)")
    parser.add_argument("--scheme", default="https", help="http or https (default: https)")
    parser.add_argument("--port",   type=int, default=443, help="Web port (default: 443)")
    parser.add_argument("--config", default="",
                        help="AEL probe YAML config (overrides --ip/--user/--pass)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print per-sample diagnostic lines")
    parser.add_argument("--json", dest="output_json", action="store_true",
                        help="Print result as JSON (in addition to human summary)")
    args = parser.parse_args()

    # Resolve connection parameters
    conn: dict = {}
    if args.config:
        conn = _load_probe_config(args.config)
    ip       = args.ip       or conn.get("ip",       "")
    user     = args.user     or conn.get("user",     "admin")
    password = args.password or conn.get("password", "admin")
    scheme   = args.scheme   or conn.get("scheme",   "https")
    port     = args.port     or conn.get("port",     443)

    if not ip:
        parser.error(
            "Board IP is required.  "
            "Provide --ip 192.168.x.x  or  --config configs/esp32jtag.yaml"
        )

    # Run
    result = run_test(
        ip=ip, user=user, password=password,
        scheme=scheme, port=port,
        verbose=args.verbose,
    )

    # Report
    print()
    print(result.summary())

    if args.output_json:
        print()
        print(json.dumps(result.to_dict(), indent=2))

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
