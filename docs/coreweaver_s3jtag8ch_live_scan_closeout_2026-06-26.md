# CoreWeaver S3JTAG8CH Live Scan Closeout

Date: 2026-06-26

## Scope

Validated the CoreWeaver board using the same first-stage pattern previously
used for S3JTAG/RP2040 bring-up:

1. Join the S3JTAG Wi-Fi/AP network.
2. Confirm TCP reachability to the Black Magic GDB remote ports.
3. Run `monitor swd_scan` on each S3JTAG8CH channel.
4. Treat socket channels as empty unless a DUT is installed.
5. Treat board-mounted CPUs as expected present targets.

Connection source:

- CoreWeaver/S3JTAG host: `192.168.4.1`
- Host-side Wi-Fi interface: `wlxf0090d36d617`
- Host-side IP: `192.168.4.2`
- Active AP profile: `esp32jtag_AFA9`

## Channel Matrix

| Channel | Port | CoreWeaver target | Expected | Observed |
|---:|---:|---|---|---|
| 0 | 4242 | S1 socket | empty | SWD scan failed |
| 1 | 4243 | S2 socket | empty | SWD scan failed |
| 2 | 4244 | S3 socket | empty | SWD scan failed |
| 3 | 4245 | S4 socket | empty | SWD scan failed |
| 4 | 4246 | STM32H503 | present | `STM32H5 M33` |
| 5 | 4247 | V305 | present | `CH32V (unknown variant) QingKe V4` |
| 6 | 4248 | RP2350 | present | `RP2350 M33`; `RP2350 M33` |
| 7 | 4249 | CH32V006 | present | SWD scan failed |

All eight TCP ports `4242..4249` were open.

The RP2350 channel required a lower SWD frequency. At the default path it was
intermittent, but with `monitor frequency 100000` Black Magic reported both
RP2350 M33 cores.

## Reusable Command

A reusable scan helper now lives at:

```bash
tools/coreweaver_s3jtag_scan.py
```

Run:

```bash
python3 tools/coreweaver_s3jtag_scan.py --host 192.168.4.1 --frequency 100000
```

Current result:

```text
[COREWEAVER_SCAN] OK: ch0 port=4242 S1/socket expect=absent observed=swd-scan-failed
[COREWEAVER_SCAN] OK: ch1 port=4243 S2/socket expect=absent observed=swd-scan-failed
[COREWEAVER_SCAN] OK: ch2 port=4244 S3/socket expect=absent observed=swd-scan-failed
[COREWEAVER_SCAN] OK: ch3 port=4245 S4/socket expect=absent observed=swd-scan-failed
[COREWEAVER_SCAN] OK: ch4 port=4246 STM32H503 expect=STM32H5 observed=STM32H5 M33
[COREWEAVER_SCAN] OK: ch5 port=4247 V305 expect=CH32V observed=CH32V (unknown variant) QingKe V4
[COREWEAVER_SCAN] OK: ch6 port=4248 RP2350 expect=RP2350 observed=RP2350 M33; RP2350 M33
[COREWEAVER_SCAN] FAIL: ch7 port=4249 CH32V006 expect=CH32V observed=swd-scan-failed
```

## Interpretation

Validated:

- S3JTAG8CH firmware is reachable over Wi-Fi.
- All eight GDB server ports are listening.
- The four socket channels are currently empty or have no SWD target installed.
- STM32H503 SWD routing works.
- V305 WCH RVSWD/SWD routing works.
- RP2350 SWD routing works at reduced clock.

Open issue:

- CH32V006 on channel 7 did not respond to SWD scan at tested frequencies from
  about 20 kHz through about 1.8 MHz effective clock.

Likely next checks:

- Confirm CH32V006 package/debug pins match CoreWeaver nets `SWCLK=GPIO46`,
  `SWDIO=GPIO45`.
- Confirm CH32V006 reset line `CH32V006_PA7_NRST` is released high.
- Confirm whether this Black Magic firmware supports CH32V006 specifically.
  Current bundled WCH target support is focused on CH32V103/V203/V208/V303/
  V305/V307.
- Confirm CH32V006 power rail and boot/debug strap requirements on the PCB.
