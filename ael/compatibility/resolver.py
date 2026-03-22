"""Compatibility resolver.

Phase 1: Test ↔ Instrument capability matching.
    resolve_test_instrument(required_capabilities, instrument_surfaces)
        → CompatibilityResult
    resolve_execution_plan(required_capabilities, instruments)
        → ExecutionPlan

Phase 2: DUT ↔ Test applicability.
    resolve_dut_test(dut_spec_or_cfg, test_raw)
        → DUTTestCompatibilityResult

Phase 3: DUT ↔ Instrument physical/protocol compatibility.
    resolve_dut_instrument(dut_spec_or_cfg, instrument_surfaces)
        → DUTInstrumentCompatibilityResult
"""

from __future__ import annotations

from typing import Any, Dict, List

from ael.compatibility.model import (
    CompatibilityResult,
    DUTInstrumentCompatibilityResult,
    DUTSpec,
    DUTTestCompatibilityResult,
    ExecutionPlan,
    Requirement,
    TestApplicabilitySpec,
)
from ael.compatibility.registry import (
    DUT_FEATURE_TO_OPTIONAL_SURFACES,
    DUT_FEATURE_TO_REQUIRED_SURFACES,
    provided_capabilities_from_surfaces,
)
from ael.compatibility.rules import check_required_set


def _parse_requirements(raw: List[str | Dict]) -> List[Requirement]:
    """Normalise a list of requirement specs into Requirement objects.

    Each element may be:
    - a plain string (capability type, count=1, required)
    - a dict with keys: type, count (optional), optional (optional)
    """
    reqs: List[Requirement] = []
    for item in raw or []:
        if isinstance(item, str) and item.strip():
            reqs.append(Requirement(type=item.strip()))
        elif isinstance(item, dict):
            cap_type = str(item.get("type") or "").strip()
            if not cap_type:
                continue
            reqs.append(Requirement(
                type=cap_type,
                count=int(item.get("count") or 1),
                params=dict(item.get("params") or {}),
                optional=bool(item.get("optional", False)),
            ))
    return reqs


def resolve_test_instrument(
    required_capabilities: List[str | Dict],
    instrument_surfaces: Dict[str, str],
) -> CompatibilityResult:
    """Check whether a single instrument satisfies a test's capability requirements.

    Args:
        required_capabilities: List of capability type strings (or dicts with
            'type', 'count', 'optional' keys) as declared by the test.
        instrument_surfaces: The instrument's capability_surfaces dict
            (taxonomy_key → surface_name) from its manifest.

    Returns:
        CompatibilityResult describing whether the instrument is compatible.
    """
    reqs = _parse_requirements(required_capabilities)
    provided = provided_capabilities_from_surfaces(instrument_surfaces)

    matched, missing, warnings = check_required_set(reqs, provided)

    compatible = len(missing) == 0
    total = len(reqs)
    required_count = sum(1 for r in reqs if not r.optional)
    required_matched = required_count - len(missing)
    score = int(100 * required_matched / required_count) if required_count else 100

    reasons: List[str] = []
    if compatible:
        reasons.append(
            f"all {required_count} required capabilities satisfied"
            + (f" ({len(warnings)} optional skipped)" if warnings else "")
        )
    else:
        reasons.append(
            f"{len(missing)} required capability(ies) not satisfied: "
            + ", ".join(f"'{m.split()[2]}'" for m in missing
                        if "required capability" in m and "'" in m)
        )

    return CompatibilityResult(
        compatible=compatible,
        score=score,
        reasons=reasons,
        missing_capabilities=[
            m.split("'")[1] for m in missing
            if "required capability" in m and "'" in m
        ],
        warnings=warnings,
    )


def resolve_execution_plan(
    required_capabilities: List[str | Dict],
    instruments: Dict[str, Dict[str, str]],
) -> ExecutionPlan:
    """Find the best instrument (or combination) to execute a test.

    Currently implements single-instrument selection (Phase 1).
    Multi-instrument plans are a Phase 2 / Phase 3 extension.

    Args:
        required_capabilities: Same format as resolve_test_instrument.
        instruments: Mapping of instrument_id → capability_surfaces dict.

    Returns:
        ExecutionPlan describing which instrument to use (or why none works).
    """
    if not instruments:
        reqs = _parse_requirements(required_capabilities)
        required = [r.type for r in reqs if not r.optional]
        return ExecutionPlan(
            executable=False,
            missing_requirements=required,
            reasons=["no instruments provided"],
        )

    best_id: str | None = None
    best_score = -1
    best_result: CompatibilityResult | None = None
    all_results: Dict[str, CompatibilityResult] = {}

    for inst_id, surfaces in instruments.items():
        result = resolve_test_instrument(required_capabilities, surfaces)
        all_results[inst_id] = result
        if result.compatible and result.score > best_score:
            best_score = result.score
            best_id = inst_id
            best_result = result

    if best_id is not None and best_result is not None:
        return ExecutionPlan(
            executable=True,
            selected_instruments=[best_id],
            matched_requirements=best_result.reasons,
            missing_requirements=[],
            warnings=best_result.warnings,
            reasons=[f"selected instrument '{best_id}' (score={best_result.score})"],
        )

    # No single instrument is fully compatible — report the best partial match
    best_partial_id = max(all_results, key=lambda k: all_results[k].score)
    partial = all_results[best_partial_id]
    reqs = _parse_requirements(required_capabilities)
    required = [r.type for r in reqs if not r.optional]

    return ExecutionPlan(
        executable=False,
        selected_instruments=[],
        missing_requirements=partial.missing_capabilities,
        warnings=partial.warnings,
        reasons=[
            f"no instrument fully satisfies requirements; "
            f"best candidate '{best_partial_id}' (score={partial.score}) "
            f"is missing: {', '.join(partial.missing_capabilities)}"
        ],
        suggested_alternatives=[
            f"add an instrument that provides: {', '.join(partial.missing_capabilities)}"
        ],
    )


def resolve_dut_test(
    dut: Any,
    test_raw: Any,
) -> DUTTestCompatibilityResult:
    """Check whether a test plan applies to a given DUT (Phase 2).

    Args:
        dut: A DUTConfig, DUTSpec, or dict describing the DUT.
        test_raw: Test plan dict (may declare applies_to, requires_dut_features,
            excludes_tags).

    Returns:
        DUTTestCompatibilityResult indicating whether the test applies.
    """
    dut_spec = dut if isinstance(dut, DUTSpec) else DUTSpec.from_dut_config(dut)
    test_spec = TestApplicabilitySpec.from_test_raw(test_raw)

    reasons: List[str] = []
    missing_features: List[str] = []
    excluded_by: List[str] = []

    # Check kind applicability (skip if applies_to is empty → test applies to all)
    if test_spec.applies_to and dut_spec.kind not in test_spec.applies_to:
        return DUTTestCompatibilityResult(
            applicable=False,
            reasons=[
                f"DUT kind '{dut_spec.kind}' not in test's applies_to "
                f"{sorted(test_spec.applies_to)}"
            ],
        )

    # Check required DUT features
    for feature in test_spec.requires_dut_features:
        if feature not in dut_spec.features:
            missing_features.append(feature)

    # Check excludes
    for tag in test_spec.excludes_tags:
        if tag in dut_spec.features:
            excluded_by.append(tag)

    if excluded_by:
        return DUTTestCompatibilityResult(
            applicable=False,
            reasons=[f"DUT has excluded tag(s): {', '.join(excluded_by)}"],
            excluded_by=excluded_by,
        )

    if missing_features:
        return DUTTestCompatibilityResult(
            applicable=False,
            reasons=[f"DUT missing required feature(s): {', '.join(missing_features)}"],
            missing_features=missing_features,
        )

    reasons.append(
        f"DUT kind '{dut_spec.kind}' is applicable"
        + (f"; all {len(test_spec.requires_dut_features)} required features present"
           if test_spec.requires_dut_features else "")
    )
    return DUTTestCompatibilityResult(applicable=True, reasons=reasons)


def resolve_dut_instrument(
    dut: Any,
    instrument_surfaces: Dict[str, str],
) -> DUTInstrumentCompatibilityResult:
    """Check whether an instrument can physically/protocol interface with a DUT (Phase 3).

    Examines the DUT's features to determine which instrument surface keys are
    required (hard requirement) or optional (generates a warning if absent).

    Args:
        dut: A DUTConfig, DUTSpec, or dict describing the DUT.
        instrument_surfaces: The instrument's capability_surfaces dict
            (surface_key → surface_name) from its manifest.

    Returns:
        DUTInstrumentCompatibilityResult.
    """
    dut_spec = dut if isinstance(dut, DUTSpec) else DUTSpec.from_dut_config(dut)
    surfaces = instrument_surfaces if isinstance(instrument_surfaces, dict) else {}

    # Surfaces that are actually populated (have a non-empty surface name)
    active_surfaces = frozenset(
        sk for sk, sname in surfaces.items()
        if str(sname or "").strip()
    )

    missing_surfaces: List[str] = []
    warnings: List[str] = []
    reasons: List[str] = []

    # Required surfaces — derived from DUT features
    required: set = set()
    for feature in dut_spec.features:
        req = DUT_FEATURE_TO_REQUIRED_SURFACES.get(feature, frozenset())
        required |= req

    for surface in sorted(required):
        if surface not in active_surfaces:
            missing_surfaces.append(surface)

    # Optional surfaces — generates warnings if absent
    for feature in dut_spec.features:
        opt = DUT_FEATURE_TO_OPTIONAL_SURFACES.get(feature, frozenset())
        for surface in sorted(opt):
            if surface not in active_surfaces and surface not in required:
                warnings.append(
                    f"DUT feature '{feature}' benefits from '{surface}' surface "
                    f"but instrument does not provide it"
                )

    compatible = len(missing_surfaces) == 0

    if compatible:
        reasons.append(
            f"instrument satisfies all required surfaces for DUT '{dut_spec.board_id or dut_spec.kind}'"
            + (f" ({len(warnings)} optional surface(s) absent)" if warnings else "")
        )
    else:
        reasons.append(
            f"instrument missing required surface(s) for DUT "
            f"'{dut_spec.board_id or dut_spec.kind}': {', '.join(missing_surfaces)}"
        )

    return DUTInstrumentCompatibilityResult(
        compatible=compatible,
        reasons=reasons,
        missing_surfaces=missing_surfaces,
        warnings=warnings,
    )
