# AI Behavior Cases

Current v0.2 usage:

```bash
python3 tools/run_ai_behavior_case.py tests/ai_behavior_cases/organic_cases.yaml inventory_current_duts_001
python3 tools/run_ai_behavior_case.py tests/ai_behavior_cases/organic_cases.yaml describe_test_stm32f401_001 --mode stub
python3 tools/run_ai_behavior_case.py tests/ai_behavior_cases/organic_cases.yaml describe_test_stm32f401_001 --print-answer-prompt
python3 tools/run_ai_behavior_case.py tests/ai_behavior_cases/organic_cases.yaml describe_test_stm32f401_001 --print-judge-prompt --answer-text "<candidate answer>"
python3 tools/run_ai_behavior_suite.py tests/ai_behavior_cases/organic_cases.yaml --mode stub
```

Results are stored under:

```text
artifacts/ai_behavior_results/<timestamp>/
```

Typical files:
- `summary.json`
- `summary.md`
- `<case_id>.json`

Current modes:
- `prompt-only`: execute retrieval and generate answer/judge prompts
- `stub`: execute retrieval and emit a lightweight provisional verdict for suite review

This loop is intentionally lightweight.
It automates retrieval and persistence now, while keeping answer/judge invocation simple and pluggable.
