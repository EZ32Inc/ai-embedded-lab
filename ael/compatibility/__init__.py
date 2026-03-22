"""Compatibility resolution module for AEL.

Phase 1: Test ↔ Instrument capability matching.
Phase 2: DUT ↔ Test applicability (planned).
Phase 3: DUT ↔ Instrument (planned).
"""

from ael.compatibility.model import (
    Capability,
    CompatibilityResult,
    DUTInstrumentCompatibilityResult,
    DUTSpec,
    DUTTestCompatibilityResult,
    ExecutionPlan,
    Requirement,
    TestApplicabilitySpec,
)
from ael.compatibility.resolver import (
    resolve_dut_instrument,
    resolve_dut_test,
    resolve_execution_plan,
    resolve_test_instrument,
)

__all__ = [
    "Capability",
    "CompatibilityResult",
    "DUTInstrumentCompatibilityResult",
    "DUTSpec",
    "DUTTestCompatibilityResult",
    "ExecutionPlan",
    "Requirement",
    "TestApplicabilitySpec",
    "resolve_dut_instrument",
    "resolve_dut_test",
    "resolve_execution_plan",
    "resolve_test_instrument",
]
