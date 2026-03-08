# AI Behavior Cases

Current usage:

```bash
python3 tools/run_ai_behavior_case.py tests/ai_behavior_cases/organic_cases.yaml inventory_current_duts_001
python3 tools/run_ai_behavior_case.py tests/ai_behavior_cases/organic_cases.yaml --list-cases
python3 tools/run_ai_behavior_case.py tests/ai_behavior_cases/organic_cases.yaml describe_test_stm32f401_001 --mode stub
python3 tools/run_ai_behavior_case.py tests/ai_behavior_cases/organic_cases.yaml inventory_current_duts_001 --answer-cmd "<CMD>" --judge-cmd "<CMD>"
python3 tools/run_ai_behavior_case.py tests/ai_behavior_cases/organic_cases.yaml describe_test_stm32f401_001 --print-answer-prompt
python3 tools/run_ai_behavior_case.py tests/ai_behavior_cases/organic_cases.yaml describe_test_stm32f401_001 --print-judge-prompt --answer-text "<candidate answer>"
python3 tools/run_ai_behavior_suite.py tests/ai_behavior_cases/organic_cases.yaml --mode stub
python3 tools/run_ai_behavior_suite.py tests/ai_behavior_cases/organic_cases.yaml --answer-cmd "<CMD>" --judge-cmd "<CMD>"
python3 tools/run_ai_behavior_suite.py tests/ai_behavior_cases/organic_cases.yaml --mode stub --rerun-from-summary artifacts/ai_behavior_results/<timestamp>/summary.json
python3 tools/review_ai_behavior_suite.py artifacts/ai_behavior_results/<timestamp>/
```

Results are stored under:

```text
artifacts/ai_behavior_results/<timestamp>/
```

Typical files:
- `summary.json`
- `summary.md`
- `<case_id>.json`

Useful helpers:
- `--list-cases`: print the available case ids with intent and question
- `--rerun-from-summary <summary.json>`: rerun only the prior suite's `FAIL` or `ERROR` cases
- `review_ai_behavior_suite.py`: print a concise human-facing digest from one suite result directory

Current modes:
- `prompt-only`: execute retrieval and generate answer/judge prompts
- `stub`: execute retrieval and emit a lightweight provisional verdict for suite review
- `external-command`: enabled by passing `--answer-cmd` and/or `--judge-cmd`

External-command protocol:
- the runner sends one JSON payload to the external command on `stdin`
- the answer command should print the final answer text to `stdout`
- the judge command should print either:
  - JSON like `{"verdict":"PASS","reason":"..."}`; or
  - plain text with the first line equal to one of `PASS`, `WEAK_PASS`, `FAIL`, `ERROR`

The payload includes the current stage plus the relevant case, retrieval, prompt, and answer context.

This loop is intentionally lightweight.
It automates retrieval and persistence now, while keeping answer/judge invocation simple and pluggable.
