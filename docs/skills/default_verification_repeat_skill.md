# Default Verification Repeat Skill

## Purpose

Guide correct usage of the `verify-default repeat` command when the user
asks to run default verification multiple times in a row.

---

## Trigger

Use this skill whenever the user asks to:

- "run default verification N times"
- "run it continuously for N times"
- "repeat default verification"
- "run it in a loop"

---

## Correct Command

Always use the built-in AEL repeat subcommand:

```bash
python3 -m ael verify-default repeat --limit <N>
```

Optional flags:
- `--limit N` — number of repetitions (required when a count is given)
- `--skip-if-docs-only` — skip run if only doc files changed
- `--file FILE` — write results to a file

To run until first failure (no limit):
```bash
python3 -m ael verify-default repeat-until-fail
```

---

## What NOT to do

Do NOT use a shell loop as a substitute:

```bash
# WRONG — do not do this
for i in $(seq 1 10); do
  python3 -m ael verify-default run
done
```

The built-in `repeat` command:
- handles result aggregation correctly
- respects AEL state and stop policies
- produces a single structured summary
- is the intended interface for this operation

---

## Example

User: "run default verification 10 times"

```bash
python3 -m ael verify-default repeat --limit 10
```

User: "run until it fails"

```bash
python3 -m ael verify-default repeat-until-fail
```
