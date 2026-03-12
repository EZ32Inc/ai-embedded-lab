# Generated Example Runtime Setup Completeness Review

## Purpose

Provide a reusable workflow for deciding whether a generated example is blocked
by missing runtime setup rather than by a generation-model defect.

## Use this when

- a generated example is plan/build valid
- the next question is whether a live run is meaningful to attempt
- the likely issue is missing bench provisioning rather than missing formal
  connection data

## Required distinction

Keep these separate:

- formal connection completeness
- runtime setup completeness
- runtime validation status

A generated example can be formally complete and still not be runtime-ready.

## Review method

1. run `inventory describe-test`
2. run `explain-stage --stage plan`
3. confirm the formal connection contract is complete enough for normal
   retrieval
4. ask whether the required runtime bench path actually exists now
5. if not, classify the example as blocked by missing bench setup

## Typical blockers

- no UART path actually wired/provisioned for the DUT
- host serial port in the plan does not correspond to the intended DUT on the
  current bench
- required external source or peripheral counterpart has not been provisioned

## Notes

- Do not treat missing bench setup as a retrieval-model failure.
- Do not promote runtime-validation claims just because the generated example
  looks complete on paper.
