# AEL Night Tasks

This file defines autonomous tasks for Codex to execute sequentially.

Each task must:
- modify code
- run validation
- commit if successful

---

# Task 1 — Implement AIP HTTP Adapter

Status: [x] DONE (205393e)

Goal

Create a new adapter that implements the AEL Instrument Protocol (AIP).

File:

ael/adapters/instrument_aip_http.py

Responsibilities:

- call instrument HTTP endpoint:
  POST /aip/v0.1/call

- translate AEL step inputs → AIP request

- parse response

- write evidence artifacts under:

run/artifacts/

Example evidence files:

instrument_voltage.json
instrument_digital.json

Validation

python3 -m py_compile ael/adapters/instrument_aip_http.py

---

# Task 2 — Manifest Loader

Status: [x] DONE (21f01a1)

Add support for loading instrument manifests.

File:

ael/instrument_manifest.py

Responsibilities

Load manifest:

configs/instruments/<instrument_id>.json

Expose:

load_manifest(instrument_id)

Return manifest dict.

Validation

python3 -m py_compile ael/instrument_manifest.py

---

# Task 3 — Adapter Registry Integration

Status: [x] DONE (1ca6155)

Update:

ael/adapter_registry.py

Add support:

instrument.aip_http

Mapping:

capability → adapter

Example:

measure.voltage
measure.digital
selftest
control.reset_target

Validation

python3 -m py_compile ael/adapter_registry.py

---

# Task 4 — Evidence Writer Helper

Status: [x] DONE (93d5066)

Create helper:

ael/evidence.py

Function:

write_evidence(run_dir, filename, payload)

Rules

Write to:

run_dir/artifacts/

JSON format
UTF-8
indent=2

Validation

python3 -m py_compile ael/evidence.py

---

# Task 5 — Instrument Contract Validator

Status: [x] DONE (b7ba7a4)

Create tool:

tools/check_instrument_contract.py

Responsibilities

For each instrument manifest:

verify:

- protocol == aip/0.1
- capabilities defined
- evidence path defined

Output:

OK or detailed error list.

Validation

python3 tools/check_instrument_contract.py
