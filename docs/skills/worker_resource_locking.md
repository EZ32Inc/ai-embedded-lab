# Worker Resource Locking

## 1. Purpose

This document explains how worker resource locking should be understood and reviewed in AEL default verification.

Its job is to keep parallel execution safe without falsely serializing unrelated work.

## 2. Scope

Use this document when:
- explaining why workers ran in parallel or waited
- reviewing task resource keys
- checking whether a blocking relationship is real
- interpreting default verification repeat behavior

## 3. Background

Default verification now runs as a parallel suite where each task is executed by a worker.

Parallel execution is only correct when workers do not contend for the same real resource.
Resource locks are therefore used to serialize only the parts of execution that share real bench dependencies.

## 4. Failure / Issue Classes

### A. Correct serialization on a real shared resource

Examples:
- same DUT
- same probe endpoint
- same explicit flash port
- same instrument endpoint

Meaning:
- waiting is expected and correct

### B. Independent workers incorrectly thought to be blocked

Typical cause:
- log interpretation error
- outer suite-loop repetition mistaken for worker blocking

Meaning:
- no real shared-resource issue may exist

### C. False serialization caused by bad configuration

Typical cause:
- accidental legacy binding
- incorrect resource-key derivation

Meaning:
- architecture or configuration should be corrected

## 5. Required Observations

Before explaining worker blocking, collect:
- command used
- worker names
- task resource keys
- whether the workers share DUT identity
- whether they share probe endpoint or probe path
- whether they share serial port
- whether they share instrument endpoint
- whether the observed waiting happened inside a suite or across repeated suite invocations

## 6. Diagnosis Workflow

1. Confirm whether the observed behavior is inside one parallel suite run or across repeated suite runs.

2. Extract the task resource keys for the workers in question.

3. Identify which key, if any, is shared.

4. If no real shared key exists, do not explain the waiting as resource locking.

5. If a shared key exists, confirm that it corresponds to a real bench dependency.

6. Distinguish intentional serialization from accidental configuration-driven serialization.

## 7. Interpretation Guide

- Shared lock key present:
  - workers should serialize on that resource

- Different lock keys:
  - workers should be able to progress independently

- Repeat mode with worker-level progression:
  - a faster worker may continue iterating while an unrelated slower worker is still behind

- Outer shell loop around suite runs:
  - apparent waiting may simply be whole-suite pacing, not lock contention

## 8. Recommended Output Format

When reporting worker locking behavior, include:
- workers involved
- shared-resource classification:
  - `real_shared_resource`
  - `no_shared_resource`
  - `false_or_unclear_sharing`
- resource keys that matter
- whether the observed serialization is expected
- next action if the blocking relationship looks wrong

## 9. Current Known Conclusions

- The guiding rule is: parallelize unrelated work, serialize only on real shared resources.
- Default verification task keys already model several important resource classes.
- Independent worker progression is the desired behavior when no real shared key exists.
- Shared-resource waiting alone is not a bug; false shared-resource assumptions are the real problem.

## 10. Unresolved Questions

- Which contention scenarios still need stronger automated coverage?
- Should future reporting expose claimed lock keys more directly in runtime output?

## 11. Related Files

- [ael/default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
- [ael/verification_model.py](/nvme1t/work/codex/ai-embedded-lab/ael/verification_model.py)
- [ael/resource_locks.py](/nvme1t/work/codex/ai-embedded-lab/ael/resource_locks.py)
- [tests/test_default_verification.py](/nvme1t/work/codex/ai-embedded-lab/tests/test_default_verification.py)
- [docs/default_verification_execution_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/default_verification_execution_model.md)

## 12. Notes

- A blocking explanation should always be backed by an actual shared resource.
- Do not confuse suite-level pacing with worker-level locking.
