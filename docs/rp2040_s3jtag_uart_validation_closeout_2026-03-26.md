## RP2040 S3JTAG UART Validation Closeout

Date: 2026-03-26

Scope:
- Instrument instance: `configs/instrument_instances/s3jtag_rp2040_lab.yaml`
- Board profile: `configs/boards/rp2040_pico_s3jtag_uart.yaml`
- Pack: `packs/uart_rp2040_s3jtag.json`
- Test plan: `tests/plans/rp2040_uart_banner_with_s3jtag.json`
- Golden firmware: `assets_golden/duts/rp2040_pico/uart_banner_s3jtag/firmware`
- Supporting firmware-side diagnostic hook: `test_uart_rxd_detect` on the `esp32s3_devkit` board profile

Bench setup validated:
- `S3JTAG SWCLK GPIO4` -> `RP2040 SWCLK`
- `S3JTAG SWDIO GPIO5` -> `RP2040 SWDIO`
- `RP2040 UART0 TX GPIO0` -> `S3JTAG UART1 RX GPIO7`
- `RP2040 UART0 RX GPIO1` -> `S3JTAG UART1 TX GPIO6`
- `S3JTAG GND` -> `RP2040 GND`
- Host Wi-Fi joined the `esp32jtag_0F91` AP and reached the instrument at `192.168.4.1`

Result summary:
- RP2040 UART golden firmware build: PASS
- RP2040 flash via `S3JTAG` BMP/GDB remote: PASS
- RP2040 UART banner observed through the `S3JTAG` internal Web UART bridge: PASS
- formal AEL pack `packs/uart_rp2040_s3jtag.json`: PASS
- successful formal run id: `2026-03-26_18-44-40_rp2040_pico_s3jtag_uart_rp2040_uart_banner_with_s3jtag`

Key evidence:
- RP2040 UART golden firmware built successfully at `artifacts/build_rp2040_uart_banner_s3jtag/pico_uart_banner_s3jtag.elf`
- ESP32-S3 USB console confirmed the UART driver was receiving the expected banner repeatedly:

```text
I (...) uart_websocket: From UART: len=23, data: AEL_READY RP2040 UART
```

- A direct websocket client against `wss://192.168.4.1/ws` received repeated banner frames:

```text
recv 'AEL_READY RP2040 UART\r\n'
recv 'AEL_READY RP2040 UART\r\n'
```

- The exact AEL helper `_capture_via_esp32jtag_web_uart('https://192.168.4.1:443', 6.0, 0.0)` returned banner bytes successfully.
- Final formal run artifacts:
  - `runs/2026-03-26_18-44-40_rp2040_pico_s3jtag_uart_rp2040_uart_banner_with_s3jtag/result.json`
  - `runs/2026-03-26_18-44-40_rp2040_pico_s3jtag_uart_rp2040_uart_banner_with_s3jtag/artifacts/verify_result.json`
  - `runs/2026-03-26_18-44-40_rp2040_pico_s3jtag_uart_rp2040_uart_banner_with_s3jtag/uart_observe.json`

## Why UART Looked Broken

The early symptom was always the same: formal UART runs ended with `bytes=0` or `expected UART patterns missing`.

That symptom came from multiple different failures at different times, not from a single broken UART implementation.

The main overlapping causes were:
- AEL initially could not reliably reach the ESP32-S3 Web UART endpoint because preflight parsed `https://192.168.4.1:443` incorrectly.
- Even after endpoint parsing was fixed, the websocket handshake timeout was too short, so some runs failed before a stream was established.
- At another point the ESP32-S3 dropped into `BROWNOUT_RST` and `DOWNLOAD(USB/UART0)` boot mode, which removed the AP entirely and made all UART/network checks fail together.
- While the bench state was unstable, the same high-level pack symptom (`bytes=0`) appeared again, which made it easy to incorrectly assume the RP2040 was not transmitting.

So the correct reading of the early failures is:
- sometimes the host was not really connected to the transport
- sometimes the ESP32-S3 application was not even running normally
- only after those were cleared did it make sense to ask whether the UART signal itself was present

## Root Cause and Fix Breakdown

There was no single root cause. The real fix was staged.

1. Transport reachability fix in AEL
- `_tcp_ping()` in AEL preflight treated `https://192.168.4.1:443` as a raw `host:port` string instead of parsing the URL first.
- That made preflight falsely report the UART web endpoint as unreachable.
- Fixed in [preflight.py](/nvme1t/work/codex/ai-embedded-lab/ael/adapters/preflight.py).

2. Websocket handshake timing fix in AEL
- The websocket client timeout in AEL was too short for this bench.
- The helper could fail during TLS/websocket setup before any UART data could be observed.
- Fixed in [observe_uart_log.py](/nvme1t/work/codex/ai-embedded-lab/ael/adapters/observe_uart_log.py) by increasing the connection timeout.

3. ESP32-S3 control-path stability fix
- On fresh boards, first-boot NVS initialization incorrectly seeded `pc_cfg=0`, which prevented the GDB server task from starting.
- That was not a UART bug directly, but it blocked the entire RP2040-over-S3JTAG flow and made the bench look unhealthy.
- Fixed in `esp32jtag_firmware` commit `6af4936 Fix first-boot gdb server defaults`.

4. Bench-state recovery
- The ESP32-S3 temporarily entered repeated brownout / ROM download mode.
- In that state the AP was gone, so all UART transport tests failed regardless of target behavior.
- This was resolved by restoring board power and boot state before continuing software validation.

5. Signal-path proof instead of guessing
- To avoid guessing whether the RP2040 was actually transmitting, a temporary firmware-side GPIO sampler was added.
- That diagnostic sampled `GPIO7` directly as a raw input and proved the RP2040 TX waveform was physically reaching the ESP32-S3 RX pin.
- Added in `esp32jtag_firmware` commit `5a140ca Add UART RX GPIO diagnostic hook`.

## What Actually Proved the UART Path Was Fine

The decisive debugging strategy was to split the UART path into layers and prove each layer separately.

1. RP2040 firmware behavior
- The RP2040 golden firmware was checked directly.
- It does not print the banner once and stop.
- It prints `AEL_READY RP2040 UART` once after boot and again every second after that.
- That means a totally empty capture should be treated as a transport or observation problem first, not as evidence that the target firmware is silent.

2. Raw electrical arrival at the ESP32-S3 RX pin
- The `test_uart_rxd_detect` hook sampled `GPIO7` directly.
- Result:

```json
{"test":"test_uart_rxd_detect","result":"pass","pin":7,"state":"toggle","samples":9401,"high":9355,"low":46,"transitions":42,"estimated_hz":84}
```

- Additional repeated sampling showed `GPIO7` spent most windows idle-high and only occasionally burst, which is exactly what a periodic UART banner should look like.
- This proved the problem was not "wire open" or "target TX dead".

3. UART driver decode inside the ESP32-S3
- The existing console log in `uart_websocket.c` showed repeated decoded text:

```text
I (...) uart_websocket: From UART: len=23, data: AEL_READY RP2040 UART
```

- That proved the signal was not only reaching the pin, but was being correctly decoded by the ESP32-S3 UART driver.
- At that point, wiring and baud mismatch were no longer the primary suspects.

4. Network-side websocket forwarding
- A manual websocket client connected to `wss://192.168.4.1/ws` and received repeated banner frames.
- The exact AEL helper `_capture_via_esp32jtag_web_uart(...)` was then called directly and also returned the expected bytes.
- That proved the ESP32-S3 network bridge was functioning correctly too.

Once all four layers were proven healthy, rerunning the formal pack resulted in immediate `PASS`.

## What Failed First and Why

- The ESP32-S3 firmware had drifted to the wrong default AP naming convention for this bench (`esp-openocd`), which made recovery and connection assumptions inconsistent with the saved host profile.
- On fresh boards, first-boot NVS initialization seeded `pc_cfg=0`, which prevented the `gdb_server` task from starting and made `192.168.4.1:4242` look dead until the storage default bug was fixed.
- After the generic devkit baseline was restored, the UART pack still failed in multiple distinct ways over time:
  - `preflight` could not reach `https://192.168.4.1:443` because `_tcp_ping()` was parsing scheme-bearing endpoints incorrectly
  - websocket handshake sometimes timed out because the client timeout was too short
  - later runs still showed `bytes=0`, which at first looked like missing UART traffic but was actually a moving bench-state problem while the board and wiring were being recovered
- A separate bench interruption pulled the ESP32-S3 into repeated brownout and `DOWNLOAD(USB/UART0)` boot mode, which temporarily removed the AP entirely and made UART investigation impossible until power and wiring were stabilized.

## Evidence That Separated False Leads From the Real Path

- RP2040 was never silent. The golden firmware prints `AEL_READY RP2040 UART` once after boot and again every second after that, so a totally empty capture should be treated as a transport problem, not a target-firmware problem.
- Direct GPIO sampling on `GPIO7` with the firmware-side `test_uart_rxd_detect` hook proved the RP2040 TX waveform was physically reaching the ESP32-S3 RX pin:

```json
{"test":"test_uart_rxd_detect","result":"pass","pin":7,"state":"toggle","samples":9401,"high":9355,"low":46,"transitions":42,"estimated_hz":84}
```

- ESP32-S3 USB console then proved the UART driver was decoding real bytes, which eliminated wiring and baud mismatch as the primary blocker.
- A manual websocket client finally proved the network-side bridge was also working, which narrowed the remaining suspicion back to pack timing and transient bench state rather than a fundamental firmware bridge defect.
- Once the board was stable and the bench wiring was corrected, the unchanged formal pack moved straight to `PASS`.

## Last-Known-Good Recovery Steps

- Rejoin the host to the instrument AP if needed:
  - `nmcli connection up esp32jtag_0F91 ifname wlx90de80a53084`
- Confirm control path health before chasing UART:
  - `arm-none-eabi-gdb -q -ex 'target extended-remote 192.168.4.1:4242' -ex 'monitor swd_scan' -ex 'quit'`
- If UART looks empty, separate the chain in this order:
  1. prove RP2040 TX is reaching `GPIO7` with `test_uart_rxd_detect`
  2. prove ESP32-S3 UART driver sees bytes on USB console
  3. prove `wss://192.168.4.1/ws` yields banner frames with a direct client
  4. prove the exact AEL helper returns the same bytes
  5. only then retry the formal AEL pack
- If the ESP32-S3 falls into ROM download mode or brownout loop, recover power and boot state before doing any AEL-side debugging.

AEL-side fixes required for the formal pack path:
- `610a3ab` `Unblock S3JTAG UART preflight and websocket capture`

Related firmware-side fixes and diagnostics:
- `6af4936` `Fix first-boot gdb server defaults`
- `5a140ca` `Add UART RX GPIO diagnostic hook`

Conclusion:
- The `S3JTAG` pattern is now validated for `RP2040` as a combined SWD flash + internal Web UART bridge instrument path.
- This path is now proven both through ad hoc live diagnostics and through a formal AEL pack run.
- The decisive debugging sequence for this bench was layered:
  - signal reaches the RX pin
  - UART driver decodes bytes
  - websocket bridge emits frames
  - AEL helper captures the same bytes
  - formal AEL pack captures the expected banner
