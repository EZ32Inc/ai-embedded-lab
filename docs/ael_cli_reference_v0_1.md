# AEL CLI Reference v0.1

This reference is for the public `master` branch. Commands are run from the
repository root:

```bash
python3 -m ael <command> ...
```

Use `python3 -m ael --help` and `python3 -m ael <command> --help` for the
runtime source of truth.

---

## Top-Level Commands

Current top-level commands:

```text
run, doctor, pack, instruments, dut, verify-default, inventory, connection,
explain-stage, workflow-archive, hw-check, la-check, status, board, project,
invoke
```

---

## State And Discovery

### `status`

Unified system-domain and user-project overview.

```bash
python3 -m ael status
```

Use this first when resuming work.

### `inventory`

Inspect known DUTs, suites, instrument instances, tests, and connections.

```bash
python3 -m ael inventory list --format text
python3 -m ael inventory suites
python3 -m ael inventory instances
python3 -m ael inventory describe-dut --board <board_id>
python3 -m ael inventory describe-test --board <board_id> --test <test_id>
python3 -m ael inventory describe-connection --board <board_id> --test <test_id>
python3 -m ael inventory diff-connection --board <board_id> --test <test_id>
python3 -m ael inventory audit-test-schema
```

### `board`

Inspect board/capability state.

```bash
python3 -m ael board state <board_id> --format text
```

### `verify-default`

Inspect or run the default verification baseline.

```bash
python3 -m ael verify-default state
python3 -m ael verify-default run
python3 -m ael verify-default review
```

---

## Running Tests

### `run`

Run one test plan against a board/DUT.

```bash
python3 -m ael run --board <board_id> --test <test_id>
python3 -m ael run --board <board_id> --test <test_id> --until-stage plan
python3 -m ael run --board <board_id> --test <test_id> --project <project_id>
```

Common options:

- `--board <board_id>`: board config ID from `configs/boards/`
- `--dut <dut_id>`: DUT ID from assets
- `--controller <instrument>`: control instrument config
- `--probe <instrument>`: legacy alias for `--controller`
- `--until-stage plan|pre-flight|run|run-exit|report`
- `--quiet` / `--verbose`

### `pack`

Run a pack file, optionally filtered by stage.

```bash
python3 -m ael pack --board <board_id> --pack packs/<pack>.json
python3 -m ael pack --board <board_id> --pack packs/<pack>.json --stage 0,1
python3 -m ael pack --board <board_id> --pack packs/<pack>.json --stop-on-fail
```

Common options:

- `--no-build`
- `--no-flash`
- `--verify-only`
- `--stage <stage-list>` for packs with `stages` metadata

---

## Project Workflow

User projects are lightweight working contexts in `projects/<project_id>/`.

```bash
python3 -m ael project list
python3 -m ael project create --target-mcu <mcu>
python3 -m ael project status <project_id>
python3 -m ael project answering-context <project_id>
python3 -m ael project questions <project_id>
python3 -m ael project intake <project_id>
python3 -m ael project run-gate <project_id>
python3 -m ael project update <project_id> --set-status <status>
python3 -m ael project append-note <project_id> --note "..."
python3 -m ael project link-run <project_id> --run-id <run_id> --ok
python3 -m ael project show-cross-domain-links <project_id>
```

Typical flow:

1. Create or select a project.
2. Confirm real board, instrument, wiring, and test intent.
3. Run `project run-gate`.
4. Run one test or pack.
5. Link evidence back to the project.

---

## Instrument And Connection Tools

```bash
python3 -m ael doctor
python3 -m ael instruments list
python3 -m ael instruments describe --id <instrument_id>
python3 -m ael instruments doctor --id <instrument_id>
python3 -m ael connection doctor --board <board_id> --test <test_id>
python3 -m ael explain-stage --board <board_id> --test <test_id> --stage <stage>
```

`doctor` and `connection doctor` are diagnostic aids. They do not prove that a
user's hardware wiring is correct unless the required physical setup has been
confirmed.

---

## Other Commands

| Command | Purpose |
|---|---|
| `dut` | DUT lifecycle and promotion commands |
| `workflow-archive` | Inspect workflow event records |
| `hw-check` | Hardware setup checks |
| `la-check` | Logic-analyzer-oriented checks |
| `invoke` | Invoke a named board capability by natural name or alias |

---

## Source Of Truth

When this document conflicts with runtime behavior, prefer:

1. `python3 -m ael <command> --help`
2. command implementation in `ael/__main__.py`
3. current configs and manifests
4. this document
