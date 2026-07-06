# CoreWeaver RP2040 Golden Reference Front Door

Date: 2026-07-06

## Problem

RP2040 flashing through ESP32JTAG/CoreWeaver can appear to succeed but leave the target halted until a board power cycle. We already solved this class of problem in the RP2040 S3JTAG Golden Suite, so new CoreWeaver/RP2040 work must reuse that known-good flash sequence instead of assembling ad hoc GDB commands.

## Required Entry Point

Before any detect/flash/debug task for a known MCU family, resolve the Golden Reference:

```bash
python3 -m ael golden-reference --target rp2040 --instrument coreweaver
```

For CoreWeaver, this resolves through the `esp32jtag` instrument family. The selected RP2040 reference is:

- Board config: `configs/boards/rp2040_pico_s3jtag.yaml`
- Pack: `packs/rp2040_s3jtag_full.json`
- Skill doc: `docs/skills/rp2040_s3jtag_standard_suite_skill_2026-03-26.md`
- Source run: `pack_runs/2026-03-26_22-24-16_rp2040_s3jtag_full_rp2040_pico_s3jtag`

## Verified Flash Sequence

The RP2040 ESP32JTAG/CoreWeaver sequence must be copied from the Golden Reference:

```yaml
flash:
  timeout_s: 120
  gdb_remote_timeout_s: 15
  allowed_strategies:
    - normal
  reset_available: false
  target_id: 1
  gdb_launch_cmds:
    - "monitor frequency 1000"
    - "monitor swd_scan"
    - "file {firmware}"
    - "attach {target_id}"
    - "load"
    - "monitor reset run"
    - "continue"
    - "detach"
```

`allowed_strategies: ["normal"]` is important. It prevents the generic BMDA resilience ladder from changing a known-good RP2040 sequence into connect-under-reset, reduced-speed, or reconnect variants.

## Current CoreWeaver AF81 Channel 2 Instance

For the CoreWeaver board on `esp32jtag_AF81`, RP2040 is on channel 2:

- Instrument config: `configs/instrument_instances/coreweaver_af81_ch2.yaml`
- Board config: `configs/boards/rp2040_pico_coreweaver_af81_ch2.yaml`
- Test wrapper: `tests/plans/rp2040_minimal_runtime_mailbox_coreweaver_ch2.json`
- GDB endpoint: `192.168.4.1:4244`

The wrapper disables the LA/web preflight because this setup only needs SWDIO, SWCLK, GND, and visual GPIO25 LED observation.

## Live Verification

Command:

```bash
python3 -m ael run --test tests/plans/rp2040_minimal_runtime_mailbox_coreweaver_ch2.json --board rp2040_pico_coreweaver_af81_ch2
```

Result:

- PASS
- Run ID: `2026-07-06_19-33-15_rp2040_pico_coreweaver_af81_ch2_rp2040_minimal_runtime_mailbox_coreweaver_ch2`
- Flash used only `attempt 1 (normal) -> OK`
- No connect-under-reset or reduced-speed fallback was used

## Rule

For RP2040 on CoreWeaver, ESP32JTAG, or another ESP32-based SWD/JTAG instrument, the operator or AI agent must:

1. Resolve Golden Reference first.
2. Reuse the referenced board flash config.
3. Change only transport binding details such as IP address, GDB port, and channel.
4. Keep the RP2040 flash sequence fixed unless the Golden Reference itself is intentionally updated after a successful verified run.
5. Record any new successful variant as a new reference, so future tasks start from code and evidence instead of memory.
