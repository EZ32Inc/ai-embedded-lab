"""Core data models for the AEL compatibility system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


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
