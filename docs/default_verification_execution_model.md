# Default Verification Execution Model

## 1. Purpose

Default verification began as a simple baseline runner: select a small set of representative board checks and execute them to confirm that AEL still works on real hardware.

That simple serial model stopped being sufficient once the baseline started to include:
- more than one board family
- more than one validation style
- shared and non-shared bench resources
- repeated verification for stability, not just one-shot smoke checks

The newer execution model exists to solve practical engineering problems:
- a purely serial runner underuses the bench when boards are unrelated
- a purely parallel runner is unsafe without explicit resource control
- repeated verification is less meaningful if the whole suite waits for synchronized round boundaries
- concurrent execution exposes logging and artifact-update hazards that did not matter in a single-threaded model
- legacy implicit resource assumptions can serialize work incorrectly and misrepresent the real bench

The purpose of this design is to make default verification behave more like the real bench:
- boards should progress independently when they do not share resources
- only true shared dependencies should serialize execution
- repeated baseline verification should provide meaningful worker-level stability information

## 2. Design Goals

The current model is designed to meet these goals:

- support parallel board progress where possible
- serialize only on real shared resources
- make repeated verification meaningful at worker level
- improve logging safety under concurrency
- preserve reliable archive and evidence updates
- reflect real bench dependencies instead of legacy assumptions
- keep the default baseline operationally simple enough to run often
- preserve deterministic result structure even when execution order varies

## 3. Core Model

The default verification system is structured around three concepts:

### Suite

A suite is the top-level baseline definition.

In current code, a suite:
- has a name
- contains a list of tasks
- carries an execution policy such as `parallel` or `serial`

Operational meaning:
- a suite defines what “the default baseline” currently means
- one invocation of `verify-default run` executes one suite pass

### Task

A task is one named verification unit inside the suite.

A task binds together:
- board identity
- action type, usually `single_run`
- the DUT test reference, primarily `board` plus `test`

Operational meaning:
- one task corresponds to one DUT test selected from inventory
- examples in the current default suite include:
  - `esp32c6_gpio_signature_with_meter`
  - `rp2040_gpio_signature`
  - `stm32f103_gpio_signature`
  - `stm32f103_uart_banner`

### Worker

A worker is the runtime executor for one task.

A worker is responsible for:
- starting and running its task
- repeating it if iteration count is greater than one
- claiming and releasing resource locks
- emitting worker-safe status lines
- returning structured iteration results

Operational meaning:
- a worker is the unit that actually progresses through repeated verification
- independent board progress is implemented by running multiple workers at once

### How a default verification run is organized

At a high level:
1. load the default verification setting
2. normalize steps into tasks
3. build a suite object
4. choose execution policy
5. run each task through a worker
6. aggregate results into suite-level output

Inside a `parallel` suite, workers are started together and finish in whatever order real execution produces.

## 4. Parallel Execution Model

The default suite now runs in parallel because the bench is not accurately modeled by a purely serial chain.

Confirmed current behavior:
- `verify-default run` starts all suite workers immediately when the execution policy is `parallel`
- workers finish independently
- task completion order may differ from task declaration order

What “independent worker progress” means:
- one worker can finish and begin its next iteration without waiting for unrelated workers to finish the same iteration number
- slower workers do not define a synchronized suite round boundary for faster workers

What is parallelized:
- task execution across workers
- repeated iterations across workers when using worker-level repeat mode

What is not parallelized:
- access to claimed shared resources
- execution inside a single worker iteration
- operations intentionally serialized for correctness, such as certain archive updates

Why outer shell-loop repetition is not the preferred model:
- `for i in ...; python3 -m ael verify-default run; done` repeats the suite as a whole
- the next suite invocation waits for the previous suite process to exit
- this prevents fast workers from making progress while slow workers are still finishing the previous suite pass

Operationally, the preferred meaning of “run the default verification N times” is:
- repeat per worker, not per whole-suite process

## 5. Repetition Model

There are several distinct command shapes, and they do not mean the same thing.

### `python3 -m ael verify-default run`

Meaning:
- execute one suite pass

Operational behavior:
- build the suite from the current config
- start all workers according to the suite execution policy
- each worker runs one iteration
- return a single suite result

Use it when:
- you want a fresh baseline check now
- you want one set of current evidence for each task

### `python3 -m ael verify-default repeat --limit N`

Meaning:
- repeat each worker up to `N` times in the worker-level repeat engine

Confirmed current behavior:
- each worker owns its own iteration counter
- a fast worker may complete multiple iterations while a slower worker is still on an earlier one
- workers stop after their own failure when stop-on-failure behavior is enabled

Use it when:
- you want repeated baseline validation with independent board progress
- you want the most meaningful stability signal from the current architecture

### `python3 -m ael verify-default repeat-until-fail --limit N`

Meaning:
- compatibility alias for the same worker-level repeat behavior

Operational guidance:
- supported for continuity
- `repeat` is the preferred form

### Outer shell loops around `verify-default run`

Example:

```bash
for i in $(seq 1 10); do
  python3 -m ael verify-default run
done
```

Meaning:
- repeat whole-suite invocations, not worker timelines

Operational consequences:
- no independent per-worker progression across suite boundaries
- the next suite run waits for the full previous suite to finish
- slower tasks become pacing items for the outer loop even if unrelated workers already finished

Preferred operational model:
- worker-level repetition is the preferred repeated-baseline model

## 6. Resource Locking Model

Parallel verification needs locks because “parallel” is only correct for unrelated work.

Without explicit locking, parallel workers can:
- claim the same physical probe simultaneously
- collide on the same serial port
- misuse the same instrument endpoint
- produce misleading pass/fail outcomes that are actually resource races

The locking model exists to serialize only where real bench sharing exists.

### Resource classes currently represented

The current model derives lock keys from the task context and may serialize on:
- DUT identity
- probe endpoint
- probe binding or explicit probe config path
- explicit flash serial port
- instrument endpoint

Archive and evidence append correctness is also treated as a serialization concern where needed.

### Why these resources matter

#### DUT identity

Two workers should not act on the same target board concurrently.

#### Probe endpoint / probe binding

If two tasks share the same physical probe or probe endpoint, they must not drive it at the same time.

#### Explicit flash serial port

Serial flashing is exclusive at the port level.

#### Instrument endpoint

If a task depends on a meter or instrument reachable through one endpoint, concurrent conflicting use may corrupt the measurement or the session.

#### Archive / evidence append path

Concurrent writers to shared archive state can corrupt output or produce incomplete records.

### Guiding principle

Parallelize unrelated work. Serialize only on real shared resources.

That principle is the core safety rule for the whole execution model.

## 7. Logging and Archive Safety

Concurrency made previously acceptable implementation shortcuts unsafe.

### Why process-global stdout swapping was unsafe

In a serial model, temporary global output redirection can appear to work.
In a concurrent model, it can cause:
- worker logs to interleave unpredictably
- log destinations to be swapped at the wrong time
- writes to closed or wrong file handles
- misleading output attribution

### Why worker-safe logging was needed

Worker-safe logging provides:
- thread-safe line emission
- correct per-worker log routing
- cleaner status signals such as `[START]`, `[DONE]`, and failure reasons

Correctness problems prevented:
- corrupted mixed logs
- lost or misattributed status lines
- concurrency-induced closed-file failures

### Why archive and evidence appends must be serialized

Concurrent workers may all finish near the same time and try to append archive or evidence information concurrently.

Without serialization, this can produce:
- partial writes
- race-dependent archive ordering
- invalid JSON or incomplete report state
- misleading evidence history

Confirmed architectural intent:
- archive/evidence update paths that are effectively shared must preserve correctness over maximum concurrency

## 8. Probe Binding and Fallback Policy

Probe selection is not only a convenience issue. It directly affects scheduling correctness and bench modeling.

### Explicit probe binding

Explicit binding means:
- the board or task names the actual probe instance or probe config to use

Benefits:
- resource ownership is visible
- locking reflects real hardware
- stage explanation can report the actual bench model

### Legacy implicit fallback

Legacy fallback means:
- if a board does not name an instance or probe config, older policy may fall back to a shared default probe

Why this is dangerous:
- it can introduce false shared-resource assumptions
- it can serialize unrelated tasks for the wrong reason
- it can mislead debugging by making the reported bench model differ from the intended one

### Boards that disable legacy fallback

Some boards may allow probe-required semantics while still disabling implicit fallback to the old shared probe.

Operational meaning:
- “probe required” and “inherit the legacy default probe” are not the same thing
- a board can require correct bench modeling without accepting a false implicit binding

### Meaning of “no implicit probe binding”

This means:
- if no explicit probe instance or probe config applies, the execution model should not invent one through legacy fallback

Architectural consequence:
- execution and stage explanation should reflect the real intended bench path, even if that means “no probe binding selected”

Current preferred wording:
- user-facing and architecture-facing output should prefer `control_instrument`
- legacy `probe*` fields may still remain as compatibility aliases in some payloads
- runtime and explanation payloads should prefer the canonical split:
  - `selected_dut`
  - `selected_board_profile`
  - `selected_bench_resources`

## 9. Operational Guidance

### When to use `verify-default run`

Use it when:
- you want one fresh full baseline pass
- you want current evidence for each default task
- you want to confirm present bench state before deeper diagnosis

### When to use `verify-default repeat`

Use it when:
- you want repeated baseline validation
- you care about per-worker progression
- you want to see whether failures emerge only after iteration count increases

This is the preferred repeated-run mode.

### Why to avoid outer shell loops for repeated per-board progression

Avoid outer loops when the goal is independent board progress because:
- they repeat the suite process, not the workers
- they reintroduce whole-suite waiting between repetitions
- they hide the worker-level timing behavior that the architecture is designed to expose

### How to think about failures in this model

Interpret failures at the right layer:
- if unrelated workers keep progressing, do not immediately blame the scheduler
- if one worker fails repeatedly while others remain stable, bias diagnosis toward that board path
- if blocking occurs, ask whether a real shared resource explains it before assuming architecture regression

## 10. Known Validated Results

### Confirmed architecture behavior

Recent live and code-level validation support these statements:
- the default suite parallel execution path is functioning
- workers inside a suite start independently
- worker independence inside a suite is functioning
- worker-level repeat mode produces independent per-worker progression
- RP2040 and STM32F103 appeared stable in observed repeated runs
- probe/resource locking is active and influences execution where resources are actually shared
- worker-safe logging and serialized archive behavior were needed and materially improved correctness
- runtime/report payloads now separate:
  - DUT identity via `selected_dut`
  - board policy via `selected_board_profile`
  - bound bench resources via `selected_bench_resources`

### Current working interpretation of bench-side instability

Do not overstate certainty.

Current working interpretation:
- the remaining intermittent issue appears localized to the ESP32-C6 bench path
- current evidence does not clearly implicate the worker architecture as the primary remaining problem

Observed failure classes have included:
- ESP32-C6 meter reachability problems
- ESP32-C6 verify-stage failures after earlier stages succeeded

This is an interpretation of current evidence, not a final closed diagnosis.

## 11. Limitations and Open Questions

Current limitations and unresolved questions include:
- ESP32-C6 still shows intermittent failures under some repeated live runs
- it remains unresolved how much of that behavior is due to:
  - host-side meter reachability
  - DUT boot/run-state instability
  - verify-window or measurement intermittence
  - longer-run recovery behavior
- observability for repeated-run degradation may still be thinner than ideal
- some legacy probe config forms are still accepted for compatibility, which means policy clarity remains important

Open engineering questions:
- what additional evidence should be captured automatically for repeated-run intermittent failures?
- should more recovery actions become first-class instead of manual?
- how much more bench-state telemetry is needed before changing verification thresholds or execution policy again?

## 12. Related Files / Commands

### Core files

- [ael/default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
- [ael/verification_model.py](/nvme1t/work/codex/ai-embedded-lab/ael/verification_model.py)
- [ael/resource_locks.py](/nvme1t/work/codex/ai-embedded-lab/ael/resource_locks.py)
- [ael/config_resolver.py](/nvme1t/work/codex/ai-embedded-lab/ael/config_resolver.py)
- [ael/probe_binding.py](/nvme1t/work/codex/ai-embedded-lab/ael/probe_binding.py)
- [ael/pipeline.py](/nvme1t/work/codex/ai-embedded-lab/ael/pipeline.py)
- [ael/stage_explain.py](/nvme1t/work/codex/ai-embedded-lab/ael/stage_explain.py)
- [configs/default_verification_setting.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/default_verification_setting.yaml)
- [configs/boards/esp32c6_devkit.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/boards/esp32c6_devkit.yaml)
- [docs/default_verification.md](/nvme1t/work/codex/ai-embedded-lab/docs/default_verification.md)

### Key commands

```bash
python3 -m ael verify-default run
python3 -m ael verify-default repeat --limit 10
python3 -m ael verify-default repeat-until-fail --limit 10
python3 -m ael instruments doctor --id esp32s3_dev_c_meter
python3 -m ael instruments describe --id esp32s3_dev_c_meter --format text
```

### Related concepts

- default verification suite
- worker-level repetition
- real shared-resource locking
- worker-safe logging
- explicit vs legacy probe binding
- bench-model correctness
