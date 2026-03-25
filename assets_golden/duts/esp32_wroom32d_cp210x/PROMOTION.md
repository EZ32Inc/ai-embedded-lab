# Promotion Record

source_draft:       esp32_wroom32d_cp210x
source_namespace:   branch
promoted_to:        esp32_wroom32d_cp210x
promoted_at:        2026-03-25T17:55:58Z

## Evidence at Promotion

  lifecycle_stage:    merge_candidate
  compile_validation: passed

## Bench Validation (2026-03-25)

All future gate criteria satisfied:

  - flash procedure validated (board successfully flashed via CP210x, reset_strategy=rts)
  - 12 isolated test programs (truth layer) each compiled, flashed, and ran to PASS
  - test_full_suite convenience binary: AEL_SUITE_FULL DONE passed=12 failed=0
  - run_id: 2026-03-25_17-51-56_esp32_wroom32d_cp210x_test_full_suite

Board is now bench-validated. Added to default_verification_setting.yaml
as optional parallel step.
