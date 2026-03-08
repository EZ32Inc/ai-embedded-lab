# AI Behavior Cases

Current v0.1 usage:

```bash
python3 tools/run_ai_behavior_case.py tests/ai_behavior_cases/organic_cases.yaml inventory_current_duts_001
python3 tools/run_ai_behavior_case.py tests/ai_behavior_cases/organic_cases.yaml describe_test_stm32f401_001 --print-answer-prompt
python3 tools/run_ai_behavior_case.py tests/ai_behavior_cases/organic_cases.yaml describe_test_stm32f401_001 --print-judge-prompt --answer-text "<candidate answer>"
```

This runner is intentionally prompt-assisted in v0.1.
It executes the formal retrieval path and emits reusable answer/judge prompts.
