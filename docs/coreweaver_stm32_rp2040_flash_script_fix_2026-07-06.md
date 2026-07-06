# CoreWeaver STM32 and RP2040 Flash Script Fix

Date: 2026-07-06

## Summary

The CoreWeaver ESP32-S3 JTAG board can program STM32 and RP2040 targets through
the same Black Magic GDB remote transport, but the post-load run sequence is not
the same for both families.

The symptom was the same in both cases:

- `load` completed
- flash readback or compare looked correct
- the LED firmware did not always run immediately after flashing
- the firmware started after a target or board power cycle

The root cause was not bad SWD wiring or bad target power. It was the final GDB
sequence used after programming flash.

## STM32 Fix

For STM32 targets on CoreWeaver, the working post-load sequence is:

```text
monitor swd_scan
file <firmware.elf>
attach 1
load
compare-sections
attach 1
detach
```

This was validated on the CoreWeaver STM32 channels where the LED starts
blinking immediately after flash without a power cycle. The important behavior
is the final `attach 1` followed by `detach`; this leaves the STM32 running
after the Black Magic remote releases the target.

Do not replace the STM32 sequence with a generic reset/run sequence unless it is
validated on that exact board:

```text
monitor reset
monitor reset run
continue
```

Those commands have previously produced valid flash contents but left the user
firmware stopped until a power cycle.

## RP2040 Fix

RP2040 is different. The STM32-style final attach/detach sequence can leave the
Pico halted even though the image was written correctly. The working RP2040
sequence matches the successful 2026-03-26 S3JTAG golden run shape:

```text
set remotetimeout 15
target extended-remote 192.168.4.1:4244
monitor frequency 1000
monitor swd_scan
file <firmware.elf>
attach 1
load
monitor reset run
continue
detach
```

The validated CoreWeaver channel 2 run reports `Remote failure reply: E01` and
then `FF` during the post-load `continue`/detach path. That is acceptable for
this reset-not-wired RP2040 setup and matches the older golden run behavior. The
target starts running after GDB detaches.

Do not insert `compare-sections` between `load` and the RP2040 post-load resume
sequence. In this setup, the compare step proved that flash contents were valid,
but it disturbed the run-state handling enough that the LED only started after a
full board power cycle.

## Why Speed Still Matters

The current CoreWeaver channel 2 RP2040 did not reliably enumerate at the
default scan speed. Lowering the requested debug frequency before `swd_scan`
made discovery and flashing stable:

```text
monitor frequency 1000
monitor swd_scan
```

On the ESP32JTAG firmware used here, the reported actual frequency was about
1999 Hz. The requested number is therefore a knob for selecting a low-speed
divider, not the exact physical TCK/SWCLK frequency.

## AEL Implementation

The board profile `configs/boards/rp2040_pico_s3jtag.yaml` now carries the
RP2040-specific launch sequence:

```yaml
flash:
  timeout_s: 120
  gdb_remote_timeout_s: 15
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

The BMDA GDB adapter now accepts `gdb_remote_timeout_s` and emits
`set remotetimeout <N>` before `target extended-remote`. This prevents slow
ESP32JTAG/RP2040 remote connections from failing before the channel-specific
scan commands run.

## Rule of Thumb

Use the target-family-specific final sequence:

| Target family | Post-load sequence |
| --- | --- |
| STM32 | `compare-sections`, then `attach 1`, then `detach` |
| RP2040 | `monitor reset run`, then `continue`, then `detach` |

The shared lesson is that successful flash programming is not enough. The flash
script also has to explicitly leave the target in the expected run state.
