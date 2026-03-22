"""Core data models for the AEL compatibility system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, FrozenSet


@dataclass
class DUTSpec:
    """Compatibility-relevant view of a DUT, extracted from DUTConfig."""

    kind: str                              # bare_mcu | soc | board | module | fpga_target | mixed_system
    features: FrozenSet[str]               # e.g. frozenset({"programmable_via_swd", "has_gpio"})
    board_id: str = ""

    @classmethod
    def from_dut_config(cls, dut_cfg: Any) -> "DUTSpec":
        """Build a DUTSpec from a DUTConfig (or any object with .kind/.features)."""
        if hasattr(dut_cfg, "kind") and hasattr(dut_cfg, "features"):
            return cls(
                kind=str(dut_cfg.kind or "board"),
                features=frozenset(dut_cfg.features or []),
                board_id=str(getattr(dut_cfg, "board_id", "") or ""),
            )
        if isinstance(dut_cfg, dict):
            return cls(
                kind=str(dut_cfg.get("kind") or "board"),
                features=frozenset(dut_cfg.get("features") or []),
                board_id=str(dut_cfg.get("board_id") or ""),
            )
        return cls(kind="board", features=frozenset())


@dataclass
class TestApplicabilitySpec:
    """Applicability constraints declared by a test plan."""

    applies_to: FrozenSet[str]             # DUT kinds this test applies to (empty = all)
    requires_dut_features: FrozenSet[str]  # DUT features that must be present
    excludes_tags: FrozenSet[str]          # DUT features/tags that exclude this test

    @classmethod
    def from_test_raw(cls, test_raw: Any) -> "TestApplicabilitySpec":
        """Build a TestApplicabilitySpec from a test plan dict."""
        if not isinstance(test_raw, dict):
            return cls(applies_to=frozenset(), requires_dut_features=frozenset(), excludes_tags=frozenset())
        raw_applies = test_raw.get("applies_to") or []
        raw_requires = test_raw.get("requires_dut_features") or []
        raw_excludes = test_raw.get("excludes_tags") or []
        return cls(
            applies_to=frozenset(str(x) for x in raw_applies if str(x).strip()),
            requires_dut_features=frozenset(str(x) for x in raw_requires if str(x).strip()),
            excludes_tags=frozenset(str(x) for x in raw_excludes if str(x).strip()),
        )


@dataclass
class DUTTestCompatibilityResult:
    """Result of checking whether a test applies to a given DUT."""

    applicable: bool
    reasons: List[str] = field(default_factory=list)
    missing_features: List[str] = field(default_factory=list)
    excluded_by: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.applicable


@dataclass
class Capability:
    """A capability that an instrument provides or a DUT exposes."""

    type: str
    params: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        if self.params:
            return f"Capability({self.type!r}, {self.params!r})"
        return f"Capability({self.type!r})"


@dataclass
class Requirement:
    """A capability requirement declared by a test."""

    type: str
    count: int = 1
    params: Dict[str, Any] = field(default_factory=dict)
    optional: bool = False

    def __repr__(self) -> str:
        suffix = " [optional]" if self.optional else ""
        return f"Requirement({self.type!r}, count={self.count}){suffix}"


@dataclass
class CompatibilityResult:
    """Result of checking whether an instrument satisfies a test's requirements."""

    compatible: bool
    score: int  # 0–100; 100 = full match, lower = partial or mismatch
    reasons: List[str] = field(default_factory=list)
    missing_capabilities: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.compatible


@dataclass
class ExecutionPlan:
    """Result of resolving which instruments to use for a given test."""

    executable: bool
    selected_instruments: List[str] = field(default_factory=list)
    matched_requirements: List[str] = field(default_factory=list)
    missing_requirements: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    suggested_alternatives: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.executable
