# Default Verification Parallel Execution Assessment v0.1

This note evaluates how close the current AEL codebase is to true parallel test
execution for the default verification suite.

Scope:

- current `verify-default` execution path
- underlying `run_pipeline` / `run_plan` behavior
- practical blockers to safe concurrent board execution

This is an engineering assessment of the current repo, not a redesign proposal.

## Files inspected

- [ael/default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
- [ael/pipeline.py](/nvme1t/work/codex/ai-embedded-lab/ael/pipeline.py)
- [ael/runner.py](/nvme1t/work/codex/ai-embedded-lab/ael/runner.py)
- [ael/run_manager.py](/nvme1t/work/codex/ai-embedded-lab/ael/run_manager.py)
- [ael/adapter_registry.py](/nvme1t/work/codex/ai-embedded-lab/ael/adapter_registry.py)
- [ael/workflow_archive.py](/nvme1t/work/codex/ai-embedded-lab/ael/workflow_archive.py)
- [configs/default_verification_setting.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/default_verification_setting.yaml)
- [tests/test_default_verification.py](/nvme1t/work/codex/ai-embedded-lab/tests/test_default_verification.py)

## Part 1: Current execution model

### What the 3 verification tasks do today

Today the default verification suite is no longer one pure serial loop.

Current behavior:

- `verify-default run` loads the suite definition from
  [default_verification_setting.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/default_verification_setting.yaml)
- `ael/default_verification.py:run_default_setting` interprets the `steps` list
  as a suite
- the current default `execution_policy.kind` is `parallel`
- one worker thread is created per board step using `ThreadPoolExecutor`
- each worker calls the existing single-run path:
  - `_run_step_action()`
  - `_run_single()`
  - `run_pipeline()`

So the suite layer is now parallel, but each board run is still internally
serial.

### Actual current behavior

- top-level suite dispatch: parallel
- per-board execution: serial
- per-board iteration loop in `repeat-until-fail`: independent per worker
- reporting:
  - suite start/done lines are interleaved safely through a log lock
  - pipeline-level logs still come from the existing serial run path and are not
    fully concurrency-safe

### Current orchestration model

There are two layers now:

1. Suite orchestration
- `ael/default_verification.py`
- owns:
  - suite definition
  - execution policy
  - worker iteration loops
  - final aggregation

2. Board run orchestration
- `ael/pipeline.py:run_pipeline`
- builds one run plan
- calls `ael/runner.py:run_plan`
- `run_plan` executes that board's steps in a serial state-machine loop

So the current model is:
- parallel suite of serial board pipelines

### Current execution units

- suite-level function:
  - `run_default_setting`
- worker/job function:
  - `_run_worker_iterations`
- per-iteration board action:
  - `_run_step_action`
  - `_run_single`
- actual board-run engine:
  - `run_pipeline`
  - `run_plan`

There is no separate worker class hierarchy. The execution units are plain
functions plus one shared per-board pipeline path.

## Part 2: Blockers to true parallel execution

### 1. Global stdout redirection

Where:

- [ael/pipeline.py](/nvme1t/work/codex/ai-embedded-lab/ael/pipeline.py)
- [ael/adapter_registry.py](/nvme1t/work/codex/ai-embedded-lab/ael/adapter_registry.py)

Problem:

- both modules temporarily replace `sys.stdout` / `sys.stderr` with tee objects
- this is process-global, not thread-local
- concurrent pipelines can overwrite each other's stdout routing

Effect:

- mixed logs
- lines going to the wrong run log
- hard-to-debug races

Difficulty:

- `significant`

### 2. Unsynchronized workflow archive appends

Where:

- [ael/workflow_archive.py](/nvme1t/work/codex/ai-embedded-lab/ael/workflow_archive.py)

Problem:

- JSONL appends are plain file appends with no explicit lock
- multiple concurrent runs can append to the same global archive file

Effect:

- possible line interleaving or ordering ambiguity
- per-run files are safer because they are distinct, global archive is shared

Difficulty:

- `medium`

### 3. Run ID generation uses second-resolution timestamps

Where:

- [ael/run_manager.py](/nvme1t/work/codex/ai-embedded-lab/ael/run_manager.py)

Problem:

- run IDs are generated with `%Y-%m-%d_%H-%M-%S`
- same board/test started twice inside the same second can collide

Effect:

- artifact directory reuse
- one run overwriting another
- especially risky for fast repeated worker iterations

Difficulty:

- `easy`

### 4. Underlying pipeline assumes one active run controls console output

Where:

- [ael/pipeline.py](/nvme1t/work/codex/ai-embedded-lab/ael/pipeline.py)

Problem:

- `run_pipeline` prints banners, status lines, hints, summaries directly
- those prints are not structured as per-worker events
- they assume one active foreground run

Effect:

- readable enough for one run
- noisy and interleaved under concurrent runs

Difficulty:

- `medium`

### 5. Shared hardware endpoints are not locked

Where:

- probe endpoints in board/probe configs
- flash and observe adapters:
  - [ael/adapters/flash_bmda_gdbmi.py](/nvme1t/work/codex/ai-embedded-lab/ael/adapters/flash_bmda_gdbmi.py)
  - [ael/adapters/observe_gpio_pin.py](/nvme1t/work/codex/ai-embedded-lab/ael/adapters/observe_gpio_pin.py)
  - [ael/adapters/preflight.py](/nvme1t/work/codex/ai-embedded-lab/ael/adapters/preflight.py)
  - [ael/adapters/flash_idf.py](/nvme1t/work/codex/ai-embedded-lab/ael/adapters/flash_idf.py)
  - [ael/adapters/observe_uart_log.py](/nvme1t/work/codex/ai-embedded-lab/ael/adapters/observe_uart_log.py)

Problem:

- no general resource lock layer exists for:
  - GDB remote endpoint
  - LA web API endpoint
  - serial flash port
  - UART capture port
  - meter TCP endpoint

Effect:

- true parallel execution is only safe when each worker uses disjoint hardware
- the current default suite mostly does, but the software does not enforce that

Difficulty:

- `significant`

### 6. Single-pipeline runner model

Where:

- [ael/runner.py](/nvme1t/work/codex/ai-embedded-lab/ael/runner.py)

Problem:

- `run_plan` is a single serial loop over steps for one run
- retries, rewind anchors, recovery actions, and timeout handling are per-run and
  stateful

Effect:

- good per-board engine
- not itself a blocker to multiple parallel runs, but it is not designed as a
  re-entrant concurrent scheduler layer

Difficulty:

- `medium`

### 7. Recovery and reset actions assume local ownership of the device path

Where:

- `failure_recovery` flow via runner
- serial reset helpers
- UART observe helpers

Problem:

- recovery actions do not coordinate with other active runs
- a reset meant for one run could interfere with another if hardware resources
  overlap

Effect:

- safe only when resource separation is already guaranteed externally

Difficulty:

- `medium`

### 8. Shared config file is not a runtime blocker, but mutation would be
unsafe if done concurrently

Where:

- [ael/default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
- [configs/default_verification_setting.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/default_verification_setting.yaml)

Problem:

- `verify-default run` only reads the config, which is fine
- `verify-default set` mutates the same file

Effect:

- not a blocker for current suite execution
- would need coordination if config writes and runs happen concurrently

Difficulty:

- `easy`

## Part 3: What true parallel test execution would mean here

In this repo, true parallel execution would mean:

- one worker per board/test task
- each worker owns:
  - plan creation
  - run directory
  - flash/build/check lifecycle
  - iteration counter
  - result reporting
- workers do not wait for each other between iterations
- resource ownership is explicit:
  - probe endpoint
  - serial port
  - meter endpoint
  - log path
  - archive writes
- each worker can flash, verify, and report without assuming it is the only
  active pipeline in the process

Concretely in this codebase, that means:

- `default_verification.py` can remain the suite orchestrator
- `run_pipeline()` must become safe to call concurrently
- logging and archive writes must stop using unsafe process-global side effects
- hardware resources must be locked or proven disjoint

So true parallel execution here is not “just use threads.”
It means “multiple concurrent `run_pipeline()` calls are safe and isolated.”

## Part 4: Small-step roadmap

### Step 1: Stabilize worker boundaries and result schema

Status:

- mostly done in [ael/default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)

Next:

- keep suite definition, policy, and worker result schema explicit
- avoid adding more behavior until lower layers are made concurrency-safe

### Step 2: Fix run identity and per-run isolation

Do next:

- make run IDs collision-resistant
  - add milliseconds, monotonic counter, or random suffix
- ensure all run outputs stay under unique per-run roots

Why:

- easy improvement
- removes one real concurrency hazard immediately

### Step 3: Remove process-global stdout swapping

Do next:

- replace `sys.stdout` redirection in pipeline/adapter paths with explicit
  logger/stream objects passed down per run
- keep console rendering as a top-level concern

Why:

- this is the biggest software blocker to safe in-process parallelism

### Step 4: Add explicit hardware resource locking

Do next:

- introduce a small lock layer keyed by resource identity, for example:
  - `probe:gdb:192.168.2.98:4242`
  - `probe:web:192.168.2.98:443`
  - `serial:/dev/ttyACM0`
  - `meter:192.168.4.1:9000`

Why:

- prevents unsafe overlaps
- makes “parallel where safe” enforceable

### Step 5: Make workflow archive writes atomic or serialized

Do next:

- add a process-local lock around global archive appends
- optionally add a safer append helper if cross-process integrity matters later

Why:

- low effort compared with stdout refactor
- removes another shared-write race

### Step 6: Add an experimental true-parallel mode

Do next:

- once Steps 2 through 5 are done, keep the current suite worker model but mark
  a mode as true-parallel-safe
- start with the default suite only
- keep serial mode available

Why:

- smallest path to real concurrency without redesigning runner/pipeline

### Step 7: Expand coverage

After the default suite is stable:

- extend the same model to other suite-style orchestrations
- only after the safety boundaries prove out

## Part 5: What is already parallel today

There is already some real parallelism today, but only at the suite layer.

### Already parallel

- `verify-default run`
  - board workers are launched in parallel threads
- `verify-default repeat-until-fail`
  - each worker iterates independently
- hardware itself is naturally parallel-capable when resources are disjoint

### Partially parallel / overlapping

- subprocesses invoked by each run may continue independently once launched
- network I/O to distinct probes/meters can overlap
- hardware-side flashing/verification on different boards can overlap in
  practice

### Still serial by design

- each board pipeline internally
  - one plan
  - one runner loop
  - one recovery state machine
  - one set of stage steps executed serially

## Judgment call

Current state:

- not fully serial anymore
- not truly parallel-safe yet
- best description:
  - `partially parallel-ready`

More specifically:

- suite orchestration is parallel-capable now
- lower execution layers are still serial-run oriented
- the codebase is close enough to justify incremental hardening
- it is not yet safe to claim robust true parallel execution in the general case

Short summary:

- top-level suite: parallel-capable
- per-board pipeline: serial-by-design
- infrastructure safety: incomplete
- recommended next step:
  - fix run ID uniqueness
  - remove process-global stdout swapping
  - add resource locks
