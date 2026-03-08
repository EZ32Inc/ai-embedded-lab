#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from difflib import SequenceMatcher
from typing import Any, Dict, List


def _normalize(text: str) -> str:
    return ' '.join(text.strip().split())


def _missing_required(case: Dict[str, Any], answer: str) -> List[str]:
    lowered = answer.lower()
    missing = []
    for item in case.get('required_output_elements', []) or []:
        token = str(item).strip().lower()
        if token and token not in lowered:
            missing.append(str(item))
    return missing


def main() -> int:
    payload = json.load(sys.stdin)
    if payload.get('stage') != 'reference_compare_judge':
        print(json.dumps({
            'verdict': 'ERROR',
            'reason': 'unexpected stage',
            'semantic_match': False,
            'grounded_in_retrieval': False,
            'required_elements_satisfied': False,
            'forbidden_failures_present': ['unexpected_stage'],
            'strengths': [],
            'weaknesses': ['unexpected stage payload'],
        }))
        return 0

    fresh = str(payload.get('fresh_answer', ''))
    approved = str(payload.get('approved_reference', {}).get('approved_answer', ''))
    retrieval = payload.get('retrieval', []) or []
    retrieval_ok = all(int(item.get('returncode', 1)) == 0 for item in retrieval)
    missing_required = _missing_required(payload.get('case', {}), fresh)
    similarity = SequenceMatcher(None, _normalize(fresh), _normalize(approved)).ratio() if (fresh or approved) else 1.0

    if _normalize(fresh) == _normalize(approved):
        verdict = 'PASS'
        reason = 'fresh answer matches approved reference after normalization'
        semantic_match = True
    elif retrieval_ok and not missing_required:
        verdict = 'WEAK_PASS'
        reason = 'fresh answer differs from approved reference but remains grounded and complete enough'
        semantic_match = similarity >= 0.55
    else:
        verdict = 'FAIL'
        reason = 'fresh answer is not equivalent to the approved reference and misses required case content'
        semantic_match = False

    print(json.dumps({
        'verdict': verdict,
        'reason': reason,
        'semantic_match': semantic_match,
        'grounded_in_retrieval': retrieval_ok,
        'required_elements_satisfied': not missing_required,
        'forbidden_failures_present': [],
        'strengths': ['exact approved-reference match'] if verdict == 'PASS' else ['retrieval completed successfully'] if verdict == 'WEAK_PASS' else [],
        'weaknesses': missing_required,
    }))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
