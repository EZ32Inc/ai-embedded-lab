"""
Tests for ael.adapters.post_flash_verify and ael.post_flash.profiles.

All serial I/O is mocked via a fake serial module so no real hardware is
required.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from typing import Any, List
from unittest.mock import patch

from ael import failure_recovery
from ael.adapters import post_flash_verify
from ael.post_flash import profiles


# ---------------------------------------------------------------------------
# Fake serial helpers
# ---------------------------------------------------------------------------

def _make_fake_serial_cls(lines: List[str], fail_open: bool = False):
    """Return a fake serial.Serial class that feeds *lines* one-by-one via readline.

    readline() returns each line with a trailing newline, then returns b"" to
    signal end-of-data.  The adapter's consecutive-empty-read guard will break
    the capture loop without needing time.monotonic patches.
    """

    class FakeSerial:
        def __init__(self, *args, **kwargs):
            if fail_open:
                raise OSError("fake: cannot open port")
            self._lines = list(lines)
            self._idx = 0
            self.rts = False
            self.dtr = True

        def readline(self):
            if self._idx < len(self._lines):
                line = self._lines[self._idx]
                self._idx += 1
                return line.encode("utf-8") + b"\n"
            return b""

        def close(self):
            pass

    return FakeSerial


# Boot log that satisfies the instrument_ready profile
_GOOD_BOOT_LOG = [
    "rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)",
    "I (0) boot: ESP-IDF v5.1.2",
    "I (500) ael: wifi connecting...",
    "I (2100) ael: wifi connected ssid=AEL_LAB",
    "I (2150) ael: ip=192.168.2.251",
    "I (2200) ael: server ready port=4242",
    "I (2250) ael: AEL S3JTAGboard is OK",
    "I (5000) ael: heartbeat",
    "I (8000) ael: heartbeat",
]

# Boot log with a crash
_CRASH_BOOT_LOG = [
    "rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)",
    "I (500) ael: wifi connecting...",
    "Guru Meditation Error: Core  0 panic'ed (StoreProhibited).",
    "Rebooting...",
]

# Boot log with reboot loop (3+ boot banners)
_REBOOT_LOOP_LOG = [
    "rst:0x1 (POWERON_RESET)",
    "rst:0x3 (SW_RESET)",
    "rst:0x3 (SW_RESET)",
    "I (0) ael: starting...",
]

# Boot log with partial startup (wifi connected but server not ready)
_PARTIAL_BOOT_LOG = [
    "rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)",
    "I (500) ael: wifi connecting...",
    "I (2100) ael: wifi connected ssid=AEL_LAB",
    "I (2150) ael: ip=192.168.2.251",
    # missing: server ready, AEL S3JTAGboard is OK
]

# boot_only profile minimal log
_MINIMAL_BOOT_LOG = [
    "I (0) boot: ESP-IDF v5.1",
    "I (500) app_main running",
    "I (600) ael: something",
]


def _run_with_fake_serial(lines: List[str], cfg: dict, fail_open: bool = False):
    """Run post_flash_verify.run() with a fake serial feeding *lines*.

    The fake serial's readline() exhaust triggers the adapter's consecutive-
    empty-read guard so the capture loop exits quickly without time patches.
    """
    import sys
    FakeSerial = _make_fake_serial_cls(lines, fail_open=fail_open)
    fake_mod = type(sys)("serial")
    fake_mod.Serial = FakeSerial
    sys.modules["serial"] = fake_mod

    with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as f:
        raw_log_path = f.name

    try:
        with patch("os.path.exists", return_value=True), \
             patch("ael.adapters.post_flash_verify.time.sleep", return_value=None):
            result = post_flash_verify.run(cfg, raw_log_path)
    finally:
        sys.modules.pop("serial", None)

    try:
        os.unlink(raw_log_path)
    except Exception:
        pass
    return result


# ---------------------------------------------------------------------------
# Tests: profiles
# ---------------------------------------------------------------------------

class TestProfiles(unittest.TestCase):
    def test_get_instrument_ready(self):
        p = profiles.get_profile("instrument_ready")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "instrument_ready")
        self.assertTrue(len(p.required) >= 4)
        self.assertTrue(len(p.forbidden) > 0)
        self.assertIsNotNone(p.firmware_ready_anchor)
        self.assertIsNotNone(p.heartbeat_pattern)

    def test_get_boot_only(self):
        p = profiles.get_profile("boot_only")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "boot_only")

    def test_get_unknown_returns_none(self):
        self.assertIsNone(profiles.get_profile("does_not_exist"))

    def test_profiles_are_frozen(self):
        p = profiles.get_profile("instrument_ready")
        with self.assertRaises(Exception):
            p.name = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: _evaluate_against_profile (internal)
# ---------------------------------------------------------------------------

class TestEvaluateProfile(unittest.TestCase):
    def _eval(self, lines, profile_name="instrument_ready"):
        p = profiles.get_profile(profile_name)
        return post_flash_verify._evaluate_against_profile(lines, p, [])

    def test_good_log_passes(self):
        result = self._eval(_GOOD_BOOT_LOG)
        self.assertTrue(result["required_all_met"])
        self.assertTrue(result["firmware_ready_seen"])
        self.assertFalse(result["crash_detected"])
        self.assertFalse(result["reboot_loop_suspected"])
        self.assertEqual(result["forbidden_matched"], [])

    def test_crash_log_detected(self):
        result = self._eval(_CRASH_BOOT_LOG)
        self.assertTrue(result["crash_detected"])
        self.assertTrue(len(result["forbidden_matched"]) > 0)
        self.assertFalse(result["required_all_met"])

    def test_reboot_loop_detected(self):
        result = self._eval(_REBOOT_LOOP_LOG)
        self.assertTrue(result["reboot_loop_suspected"])
        self.assertTrue(result["crash_detected"])

    def test_partial_log_missing_patterns(self):
        result = self._eval(_PARTIAL_BOOT_LOG)
        self.assertFalse(result["required_all_met"])
        self.assertFalse(result["firmware_ready_seen"])
        self.assertTrue(len(result["missing_required"]) > 0)

    def test_boot_only_profile_minimal_log(self):
        result = self._eval(_MINIMAL_BOOT_LOG, profile_name="boot_only")
        self.assertTrue(result["required_all_met"])
        self.assertTrue(result["firmware_ready_seen"])

    def test_empty_lines_no_output(self):
        result = self._eval([])
        self.assertFalse(result["has_any_output"])
        self.assertFalse(result["required_all_met"])

    def test_download_mode_detected(self):
        lines = ["waiting for download", "I (0) boot: ..."]
        result = self._eval(lines)
        self.assertTrue(result["download_mode_detected"])


# ---------------------------------------------------------------------------
# Tests: _classify_state (internal)
# ---------------------------------------------------------------------------

class TestClassifyState(unittest.TestCase):
    def _make_eval(self, has_output, crash, reboot, all_met, ready_seen):
        return {
            "has_any_output": has_output,
            "crash_detected": crash,
            "reboot_loop_suspected": reboot,
            "required_all_met": all_met,
            "firmware_ready_seen": ready_seen,
        }

    def test_no_output(self):
        e = self._make_eval(False, False, False, False, False)
        self.assertEqual(post_flash_verify._classify_state(e), "no_output")

    def test_crash(self):
        e = self._make_eval(True, True, False, False, False)
        self.assertEqual(post_flash_verify._classify_state(e), "crash")

    def test_ready(self):
        e = self._make_eval(True, False, False, True, True)
        self.assertEqual(post_flash_verify._classify_state(e), "ready")

    def test_partial(self):
        e = self._make_eval(True, False, False, False, False)
        self.assertEqual(post_flash_verify._classify_state(e), "partial")


# ---------------------------------------------------------------------------
# Tests: failure_recovery constant
# ---------------------------------------------------------------------------

class TestFailureRecoveryConstant(unittest.TestCase):
    def test_runtime_bringup_failed_constant_exists(self):
        self.assertEqual(
            failure_recovery.FAILURE_RUNTIME_BRINGUP_FAILED,
            "runtime_bringup_failed",
        )

    def test_runtime_bringup_failed_in_known_kinds(self):
        self.assertIn(
            failure_recovery.FAILURE_RUNTIME_BRINGUP_FAILED,
            failure_recovery.KNOWN_FAILURE_KINDS,
        )

    def test_normalize_runtime_bringup_failed(self):
        normalized = failure_recovery.normalize_failure_kind("runtime_bringup_failed")
        self.assertEqual(normalized, "runtime_bringup_failed")


# ---------------------------------------------------------------------------
# Tests: run() — port not configured
# ---------------------------------------------------------------------------

class TestRunPortNotConfigured(unittest.TestCase):
    def test_no_port_returns_transport_error(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as f:
            raw_log_path = f.name
        try:
            result = post_flash_verify.run({}, raw_log_path)
        finally:
            os.unlink(raw_log_path)

        self.assertFalse(result["ok"])
        self.assertTrue(result["flash_succeeded"])
        self.assertEqual(result["failure_kind"], failure_recovery.FAILURE_TRANSPORT_ERROR)
        self.assertIn("port not configured", result["error_summary"])

    def test_port_not_found_returns_transport_error(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as f:
            raw_log_path = f.name
        try:
            with patch("os.path.exists", return_value=False):
                result = post_flash_verify.run(
                    {"port": "/dev/ttyFAKE99"},
                    raw_log_path,
                )
        finally:
            os.unlink(raw_log_path)

        self.assertFalse(result["ok"])
        self.assertEqual(result["failure_kind"], failure_recovery.FAILURE_TRANSPORT_ERROR)
        self.assertIn("port not found", result["error_summary"])


# ---------------------------------------------------------------------------
# Integration-style tests: run() with fake serial
# ---------------------------------------------------------------------------

class TestRunWithFakeSerial(unittest.TestCase):
    """Integration-style tests exercising run() with a fake serial module."""

    def setUp(self):
        self._log_path = tempfile.mktemp(suffix=".log")

    def tearDown(self):
        try:
            os.unlink(self._log_path)
        except Exception:
            pass

    def _run(self, boot_lines, extra_cfg=None, fail_open=False):
        import sys
        cfg = {
            "port": "/dev/ttyFAKE0",
            "baud": 115200,
            "profile": "instrument_ready",
            "reset_on_start": False,   # skip RTS pulse in unit tests
            "capture_window_s": 30.0,  # large window; fake serial EOF exits early
            "startup_wait_s": 0.5,
            "heartbeat_confirm_s": 0.0,  # skip heartbeat window in unit tests
            "max_recovery_attempts": 1,
        }
        if extra_cfg:
            cfg.update(extra_cfg)

        FakeSerial = _make_fake_serial_cls(boot_lines, fail_open=fail_open)
        fake_mod = type(sys)("serial")
        fake_mod.Serial = FakeSerial
        sys.modules["serial"] = fake_mod

        try:
            with patch("os.path.exists", return_value=True), \
                 patch("ael.adapters.post_flash_verify.time.sleep", return_value=None):
                result = post_flash_verify.run(cfg, self._log_path)
        finally:
            sys.modules.pop("serial", None)

        return result

    def test_good_boot_succeeds(self):
        result = self._run(_GOOD_BOOT_LOG)
        self.assertTrue(result["ok"], f"Expected ok=True; got: {result}")
        self.assertTrue(result["firmware_ready_seen"])
        self.assertEqual(result["state"], "ready")
        self.assertEqual(result["failure_kind"], "")
        self.assertEqual(result["error_summary"], "")
        self.assertTrue(result["flash_succeeded"])

    def test_crash_returns_runtime_bringup_failed(self):
        result = self._run(_CRASH_BOOT_LOG)
        self.assertFalse(result["ok"])
        self.assertEqual(
            result["failure_kind"],
            failure_recovery.FAILURE_RUNTIME_BRINGUP_FAILED,
        )
        self.assertTrue(result["crash_detected"])
        self.assertTrue(result["flash_succeeded"])
        self.assertIn("crash", result["error_summary"].lower())
        self.assertEqual(result["state"], "crash")

    def test_no_output_returns_runtime_bringup_failed(self):
        result = self._run([])
        self.assertFalse(result["ok"])
        self.assertEqual(
            result["failure_kind"],
            failure_recovery.FAILURE_RUNTIME_BRINGUP_FAILED,
        )
        self.assertEqual(result["state"], "no_output")
        self.assertIn("no UART output", result["error_summary"])

    def test_partial_boot_returns_runtime_bringup_failed(self):
        result = self._run(_PARTIAL_BOOT_LOG)
        self.assertFalse(result["ok"])
        self.assertEqual(
            result["failure_kind"],
            failure_recovery.FAILURE_RUNTIME_BRINGUP_FAILED,
        )
        self.assertEqual(result["state"], "partial")
        self.assertIn("missing patterns", result["error_summary"])
        self.assertTrue(len(result["missing_required"]) > 0)

    def test_reboot_loop_is_not_recoverable(self):
        result = self._run(_REBOOT_LOOP_LOG)
        self.assertFalse(result["ok"])
        # Reboot loop should not produce a retry-able recovery hint
        self.assertIsNone(result.get("recovery_hint"))

    def test_boot_only_profile(self):
        result = self._run(
            _MINIMAL_BOOT_LOG,
            extra_cfg={"profile": "boot_only"},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["state"], "ready")

    def test_custom_profile(self):
        custom_lines = ["MY_CUSTOM_READY_TOKEN present"]
        result = self._run(
            custom_lines,
            extra_cfg={
                "profile": "custom",
                "custom_patterns": ["MY_CUSTOM_READY_TOKEN"],
            },
        )
        self.assertTrue(result["ok"])

    def test_serial_open_failure_returns_transport_error(self):
        result = self._run([], fail_open=True)
        self.assertFalse(result["ok"])
        # After retries exhausted due to open failure: transport_error
        self.assertEqual(result["failure_kind"], failure_recovery.FAILURE_TRANSPORT_ERROR)

    def test_result_always_has_flash_succeeded_true(self):
        """flash_succeeded must always be True — this adapter is only called post-flash."""
        for lines in [_GOOD_BOOT_LOG, _CRASH_BOOT_LOG, []]:
            result = self._run(lines)
            self.assertTrue(
                result["flash_succeeded"],
                f"flash_succeeded must be True, got False for lines={lines[:2]}",
            )

    def test_raw_log_written_on_success(self):
        self._run(_GOOD_BOOT_LOG)
        self.assertTrue(os.path.exists(self._log_path))
        with open(self._log_path, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("AEL S3JTAGboard is OK", content)

    def test_raw_log_written_on_failure(self):
        self._run(_CRASH_BOOT_LOG)
        self.assertTrue(os.path.exists(self._log_path))
        with open(self._log_path, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Guru Meditation", content)


if __name__ == "__main__":
    unittest.main()
