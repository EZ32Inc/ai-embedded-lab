# AEL Agent v0.7 Nightly

## What nightly does

`ael nightly` runs a bounded autonomous loop for backlog plans and creates one markdown report per day.

- collects backlog tasks (default `queue/inbox`)
- isolates each plan execution in its own git branch
- executes tasks through agent internals
- commits eligible code/doc/tool changes locally (no push)
- writes `reports/nightly_<YYYY-MM-DD>.md`

## Usage

Dry run:

```bash
python3 -m ael nightly --dry-run --allow-on-master
```

Real run:

```bash
python3 -m ael nightly --max-plans 3 --allow-on-master
```

Options:

- `--max-plans N`
- `--allow-on-master`
- `--no-stash`
- `--dry-run`
- `--queue <path>`
- `--report-root <path>`
- `--verbose`

## Safety rules

- Refuses to run on `master/main` unless `--allow-on-master` or `--dry-run` is set.
- Branch pattern: `agent/<YYYYMMDD>/<slug>`
- Leaves created branches for manual review.
- Never pushes remotes in v0.7.

## Reports and artifacts

- nightly summary: `reports/nightly_<YYYY-MM-DD>.md`
- per-plan report from agent: `reports/plan_<task_id>.md`
- detailed task artifacts: run directories referenced in report

## Promote changes manually

1. Review nightly report and run artifacts.
2. Inspect nightly branch commits.
3. Merge selected branch manually into your integration branch.
