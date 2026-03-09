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
python3 tools/run_ai_behavior_suite.py tests/ai_behavior_cases/baselines/v1.yaml --mode stub
python3 tools/run_ai_behavior_suite.py tests/ai_behavior_cases/organic_cases.yaml --answer-cmd "<CMD>" --judge-cmd "<CMD>"
python3 tools/run_ai_behavior_suite.py tests/ai_behavior_cases/organic_cases.yaml --mode stub --rerun-from-summary artifacts/ai_behavior_results/<timestamp>/summary.json
python3 tools/review_ai_behavior_suite.py artifacts/ai_behavior_results/<timestamp>/
python3 tools/ai_behavior_reference.py draft tests/ai_behavior_cases/organic_cases.yaml inventory_current_duts_001 --answer-file review_answer.txt
python3 tools/ai_behavior_reference.py approve --draft-json artifacts/ai_behavior_references/<timestamp>/inventory_current_duts_001.draft.json
python3 tools/ai_behavior_reference.py compare tests/ai_behavior_cases/organic_cases.yaml inventory_current_duts_001 --answer-file fresh_answer.txt --judge-cmd "<CMD>"
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
- `ai_behavior_reference.py`: manage reviewable Q&A references with `draft`, `approve`, and `compare`

Baseline manifests:
- the suite runner also accepts a lightweight baseline manifest instead of a raw case list
- a baseline manifest points at a source case file plus an ordered `include_case_ids` list
- current example:
  - `python3 tools/run_ai_behavior_suite.py tests/ai_behavior_cases/baselines/v1.yaml`

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

Approved-reference flow:
- `draft`: create a reviewable Q&A draft JSON and Markdown file
- human reviews and edits the answer if needed
- `approve`: store the approved reference under `tests/ai_behavior_cases/references/approved/`
- `compare`: compare a fresh answer against the approved reference

Reference comparison is AI-native by default when `--judge-cmd` is provided:
A built-in deterministic judge is available for approved-reference workflows:
```bash
python3 tools/ai_behavior_reference.py compare tests/ai_behavior_cases/organic_cases.yaml inventory_current_duts_001 --answer-file fresh_answer.txt --judge-cmd "python3 tools/reference_semantic_judge.py"
```

- compare sends one structured semantic-judge JSON payload to the judge command on `stdin`
- the judge should return structured JSON with:
  - `verdict`
  - `reason`
  - `semantic_match`
  - `grounded_in_retrieval`
  - `required_elements_satisfied`
  - `forbidden_failures_present`
  - optional `strengths` / `weaknesses`

Fallback:
- if `--judge-cmd` is omitted, compare falls back to the older mechanical comparison path
- that fallback remains only as a temporary fallback, not the intended primary mode

This loop is intentionally lightweight.
It automates retrieval and persistence now, while keeping answer/judge invocation simple and pluggable.
