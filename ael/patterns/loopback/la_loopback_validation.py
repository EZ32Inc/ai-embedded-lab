"""
ael.patterns.loopback.la_loopback_validation
=============================================
Reusable pattern for Logic-Analyzer-based loopback validation.

Concept
-------
An output driver writes a known signal (static value or dynamic counter)
on some set of pins.  A physical loopback wire carries that signal to a
Logic Analyzer input.  This module captures the LA data and verifies the
expected pattern – with no external instruments and no human inspection.

This module is intentionally board-agnostic and port-agnostic.
Callers supply two thin callables:

  output_fn(mode: int, value: int = 0) -> None
      Drive the output.  Semantics of mode/value are defined by the
      caller; the pattern does not interpret them.

  capture_fn() -> bytes
      Perform an instant LA capture and return the raw binary buffer
      exactly as the firmware sends it.

The binary buffer format expected by this module:
  byte[0]     skipped (firmware status byte)
  bytes[1,2]  sample 0  (big-endian 16-bit, bit-i = LA channel i)
  bytes[3,4]  sample 1
  ...

This matches the ESP32JTAG firmware's /instant_capture response and the
logic_analyzer.html processCapturedData() decoder.

Usage example
-------------
  from ael.patterns.loopback.la_loopback_validation import LALoopbackValidator

  validator = LALoopbackValidator(
      output_fn=my_drive_fn,
      capture_fn=my_capture_fn,
      channels=[0, 1, 2, 3],       # which LA channels to inspect
  )
  result = validator.run_suite()
  print(result.summary())
  assert result.passed

Validated on
------------
  ESP32JTAG  Port D (P3) → Port A (P0)   8/8 PASS  2026-03-24
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple


# ── Types ─────────────────────────────────────────────────────────────────────

OutputFn  = Callable[[int, int], None]   # (mode, value) -> None
CaptureFn = Callable[[], bytes]           # () -> raw bytes


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_samples(raw: bytes) -> List[int]:
    """Decode raw capture buffer → list of 16-bit channel words."""
    data = raw
    words: List[int] = []
    n = 0
    while n + 2 < len(data):
        high = data[n + 1]
        low  = data[n + 2]
        words.append((high << 8) | low)
        n += 2
    return words


def _nibble(word: int, channels: List[int]) -> int:
    """Extract a bitmask of the requested channels from a 16-bit word."""
    result = 0
    for i, ch in enumerate(channels):
        if (word >> ch) & 1:
            result |= (1 << i)
    return result


def _count_edges(bits: List[int]) -> int:
    if len(bits) < 2:
        return 0
    return sum(1 for a, b in zip(bits, bits[1:]) if a != b)


def _duty(samples: List[int], channel: int) -> float:
    """Return fraction of HIGH samples for one channel (0.0–1.0)."""
    if not samples:
        return 0.0
    highs = sum(1 for s in samples if (s >> channel) & 1)
    return highs / len(samples)


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class CaseResult:
    description: str
    phase: str           # "gpio" | "counter"
    passed: bool
    sample_count: int
    details: dict        # phase-specific diagnostic data
    failure_reason: str = ""


@dataclass
class LoopbackResult:
    test_name: str
    cases: List[CaseResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.cases)

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.cases if c.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.cases if not c.passed)

    def summary(self) -> str:
        lines = [
            "=" * 60,
            f"Loopback Test: {self.test_name}",
            f"Result: {'PASS' if self.passed else 'FAIL'}  "
            f"({self.pass_count}/{len(self.cases)} cases passed)",
            "=" * 60,
        ]
        for c in self.cases:
            icon = "✓" if c.passed else "✗"
            lines.append(f"  {icon} [{c.phase:7s}] {c.description}")
            if not c.passed:
                lines.append(f"           FAIL: {c.failure_reason}")
            if c.phase == "gpio":
                exp = c.details.get("expected")
                rate = c.details.get("match_rate_pct", 0.0)
                lines.append(f"           samples={c.sample_count}  "
                              f"expected={exp:04b}  match={rate:.1f}%")
            elif c.phase == "counter":
                for ch, stats in (c.details.get("channels") or {}).items():
                    duty_pct = stats.get("duty_pct", 0.0)
                    edges    = stats.get("edges", 0)
                    tog      = "✓" if stats.get("toggles") else "✗"
                    lines.append(f"           CH{ch}: duty={duty_pct:.1f}%  "
                                 f"edges={edges}  {tog}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "test_name":  self.test_name,
            "passed":     self.passed,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "cases": [
                {
                    "description":    c.description,
                    "phase":          c.phase,
                    "passed":         c.passed,
                    "sample_count":   c.sample_count,
                    "details":        c.details,
                    "failure_reason": c.failure_reason,
                }
                for c in self.cases
            ],
        }


# ── Core validator ─────────────────────────────────────────────────────────────

class LALoopbackValidator:
    """
    Logic-Analyzer-based loopback validator.

    Parameters
    ----------
    output_fn : OutputFn
        Callable that drives the output.  Signature: ``(mode, value) -> None``.
        Semantics of mode/value are defined by the concrete test; this class
        passes them through unchanged.

    capture_fn : CaptureFn
        Callable that performs one instant LA capture and returns the raw
        binary buffer.  Signature: ``() -> bytes``.

    channels : list[int]
        LA channel indices (0–15) to inspect.  The first channel in the list
        is treated as bit-0 of expected patterns.

    test_name : str
        Human-readable name for this loopback test.

    settle_ms : int
        Milliseconds to wait after calling output_fn before capturing.
    """

    def __init__(
        self,
        output_fn:   OutputFn,
        capture_fn:  CaptureFn,
        channels:    List[int],
        test_name:   str = "la_loopback",
        settle_ms:   int = 50,
        verbose:     bool = False,
    ) -> None:
        if not channels:
            raise ValueError("channels must not be empty")
        if not all(0 <= ch <= 15 for ch in channels):
            raise ValueError("channel indices must be 0–15")
        self.output_fn  = output_fn
        self.capture_fn = capture_fn
        self.channels   = channels
        self.test_name  = test_name
        self.settle_ms  = settle_ms
        self.verbose    = verbose

    # ── Private helpers ────────────────────────────────────────────────────────

    def _drive_and_capture(self, mode: int, value: int = 0) -> List[int]:
        self.output_fn(mode, value)
        if self.settle_ms > 0:
            time.sleep(self.settle_ms / 1000.0)
        raw     = self.capture_fn()
        samples = _parse_samples(raw)
        if self.verbose:
            print(f"  [capture] mode={mode} val={value}  "
                  f"raw={len(raw)}B  samples={len(samples)}")
        return samples

    # ── Public validation methods ──────────────────────────────────────────────

    def validate_static(
        self,
        mode:        int,
        value:       int,
        description: str,
        match_threshold_pct: float = 95.0,
    ) -> CaseResult:
        """
        Drive a static value and verify all captured samples match it.

        The ``value`` is interpreted as a bitmask over ``self.channels``:
        bit-i of ``value`` must match ``channels[i]`` in every sample.

        Parameters
        ----------
        mode : int
            Passed to output_fn.
        value : int
            Expected bitmask (relative to channels list).
        description : str
            Human-readable label for this test case.
        match_threshold_pct : float
            Minimum required match rate.  Default 95% (allows transients).
        """
        samples = self._drive_and_capture(mode, value)

        if not samples:
            return CaseResult(
                description=description, phase="gpio", passed=False,
                sample_count=0,
                details={"expected": value, "match_rate_pct": 0.0},
                failure_reason="no samples captured",
            )

        # Build expected word: for each channel at position i, set bit if (value >> i) & 1
        expected_bits = {ch: (value >> i) & 1 for i, ch in enumerate(self.channels)}

        mismatches = 0
        for s in samples:
            for ch, exp_bit in expected_bits.items():
                if ((s >> ch) & 1) != exp_bit:
                    mismatches += 1
                    break  # count sample-level mismatches

        matched = len(samples) - mismatches
        pct     = 100.0 * matched / len(samples)
        passed  = pct >= match_threshold_pct

        # Collect unique nibbles seen (for diagnostics)
        unique_nibbles = sorted({
            tuple(((s >> ch) & 1) for ch in self.channels)
            for s in samples[:500]
        })

        return CaseResult(
            description=description,
            phase="gpio",
            passed=passed,
            sample_count=len(samples),
            details={
                "expected":        value,
                "expected_bits":   expected_bits,
                "match_rate_pct":  round(pct, 2),
                "mismatches":      mismatches,
                "unique_nibbles":  unique_nibbles[:20],
            },
            failure_reason=(
                "" if passed else
                f"match rate {pct:.1f}% < threshold {match_threshold_pct:.1f}%"
            ),
        )

    def validate_counter(
        self,
        mode:             int,
        description:      str,
        duty_range:       Tuple[float, float] = (0.35, 0.65),
        check_freq_order: bool = True,
    ) -> CaseResult:
        """
        Drive a free-running counter and verify all channels are toggling.

        Parameters
        ----------
        mode : int
            Passed to output_fn (value defaults to 0).
        description : str
            Human-readable label for this test case.
        duty_range : (float, float)
            Acceptable (min, max) duty cycle fraction for each channel.
        check_freq_order : bool
            If True, verify that edge counts decrease monotonically from
            channels[0] to channels[-1] (bit-0 is fastest).
        """
        samples = self._drive_and_capture(mode, 0)

        if not samples:
            return CaseResult(
                description=description, phase="counter", passed=False,
                sample_count=0,
                details={"channels": {}},
                failure_reason="no samples captured",
            )

        ch_stats: dict[str, dict] = {}
        failures: List[str] = []

        edge_counts: List[int] = []

        for ch in self.channels:
            bits   = [(s >> ch) & 1 for s in samples]
            d      = _duty(samples, ch)
            edges  = _count_edges(bits)
            tog    = d > 0.0 and d < 1.0
            in_range = duty_range[0] <= d <= duty_range[1]

            ch_stats[str(ch)] = {
                "duty_pct":  round(d * 100, 1),
                "edges":     edges,
                "toggles":   tog,
                "in_range":  in_range,
            }
            edge_counts.append(edges)

            if not tog:
                failures.append(f"CH{ch} stuck (duty={d*100:.1f}%)")
            elif not in_range:
                failures.append(
                    f"CH{ch} duty {d*100:.1f}% outside "
                    f"[{duty_range[0]*100:.0f}%–{duty_range[1]*100:.0f}%]"
                )

        # Frequency ordering: each successive channel should have ≤ edge count
        if check_freq_order and len(edge_counts) > 1:
            for i in range(len(edge_counts) - 1):
                if edge_counts[i] < edge_counts[i + 1]:
                    failures.append(
                        f"freq order violated: "
                        f"CH{self.channels[i]} ({edge_counts[i]} edges) < "
                        f"CH{self.channels[i+1]} ({edge_counts[i+1]} edges)"
                    )

        passed = len(failures) == 0
        return CaseResult(
            description=description,
            phase="counter",
            passed=passed,
            sample_count=len(samples),
            details={
                "duty_range": duty_range,
                "channels":   ch_stats,
            },
            failure_reason="; ".join(failures) if failures else "",
        )

    # ── Suite runner ───────────────────────────────────────────────────────────

    def run_suite(self, cases: List[dict]) -> LoopbackResult:
        """
        Run all test cases and return a LoopbackResult.

        Each case dict must have:
          type: "gpio" | "counter"
          mode: int
          description: str

        For "gpio" cases:
          value: int                          (required)
          match_threshold_pct: float          (optional, default 95)

        For "counter" cases:
          duty_range: [float, float]          (optional)
          check_freq_order: bool              (optional, default True)
        """
        result = LoopbackResult(test_name=self.test_name)

        for case in cases:
            ctype = str(case.get("type", "gpio"))
            mode  = int(case.get("mode", 0))
            desc  = str(case.get("description", f"case_{len(result.cases)}"))

            if ctype == "gpio":
                cr = self.validate_static(
                    mode=mode,
                    value=int(case.get("value", 0)),
                    description=desc,
                    match_threshold_pct=float(case.get("match_threshold_pct", 95.0)),
                )
            elif ctype == "counter":
                cr = self.validate_counter(
                    mode=mode,
                    description=desc,
                    duty_range=tuple(case.get("duty_range", (0.35, 0.65))),
                    check_freq_order=bool(case.get("check_freq_order", True)),
                )
            else:
                cr = CaseResult(
                    description=desc, phase="unknown", passed=False,
                    sample_count=0, details={},
                    failure_reason=f"unknown case type: {ctype!r}",
                )

            result.cases.append(cr)
            if self.verbose:
                icon = "✓" if cr.passed else "✗"
                print(f"  {icon} {desc}")

        return result
