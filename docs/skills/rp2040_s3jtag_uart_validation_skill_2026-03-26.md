# RP2040 S3JTAG UART Validation Skill

## Purpose

Capture the reusable workflow for validating an `RP2040` target through the `S3JTAG` instrument path when the target is flashed over SWD and its UART banner is observed through the ESP32-S3 internal Web UART bridge.

This skill exists because the successful bench pattern was not just "run the UART pack again". The working pattern was layered:
- prove SWD flash still works
- prove the RP2040 UART signal reaches `GPIO7`
- prove the ESP32-S3 UART driver decodes bytes
- prove the websocket bridge emits those bytes
- then run the formal AEL pack

## Trigger / When To Use

Use this skill when:
- the instrument is `S3JTAG` or another generic `esp32s3_devkit`-class probe
- the target is flashed over `192.168.4.1:4242`
- the expected console is on the ESP32-S3 internal Web UART path
- UART pack runs fail with `bytes=0` or `expected UART patterns missing`
- you need to separate wiring problems from UART-driver problems from websocket-forwarding problems

## Validated Scope

Validated bench shape:
- `S3JTAG SWCLK GPIO4` -> target `SWCLK`
- `S3JTAG SWDIO GPIO5` -> target `SWDIO`
- target `UART TX` -> `S3JTAG UART1 RX GPIO7`
- target `UART RX` -> `S3JTAG UART1 TX GPIO6`
- common ground

Validated target on 2026-03-26:
- `RP2040 Pico`
- target UART: `UART0`
- TX pin: `GPIO0`
- RX pin: `GPIO1`
- expected repeated banner: `AEL_READY RP2040 UART`
- validated formal pack: `packs/uart_rp2040_s3jtag.json`
- validated successful run id: `2026-03-26_18-44-40_rp2040_pico_s3jtag_uart_rp2040_uart_banner_with_s3jtag`

## Why This Skill Matters

The easy false conclusion is that `bytes=0` means the target is not sending. On this bench that is too weak.

The reusable rule is:
- treat UART debugging as a chain of four boundaries
- verify each boundary directly before blaming the next layer

For this bench those boundaries are:
1. target TX reaches `GPIO7`
2. ESP32-S3 UART driver receives bytes
3. websocket bridge forwards bytes
4. AEL capture helper records those bytes

## Preconditions

Required host and bench assumptions:
- host is joined to `esp32jtag_0F91`
- instrument web API is reachable at `https://192.168.4.1`
- BMP/GDB remote is reachable at `192.168.4.1:4242`
- RP2040 SWD wiring is intact
- RP2040 `GPIO0/UART0_TX` is wired to `GPIO7`
- RP2040 `GPIO1/UART0_RX` is wired to `GPIO6`

Required firmware state:
- ESP32-S3 devkit UART image is flashed
- AP defaults are `esp32jtag` / `esp32jtag`
- first-boot `pc_cfg` default bug is fixed so the GDB server comes up

## Core Flow

1. Confirm the host is on the S3 AP and `monitor swd_scan` still finds the RP2040.
2. Build and flash the RP2040 UART banner firmware over SWD.
3. If UART capture is empty, do not immediately assume the target is silent.
4. Sample `GPIO7` as a raw input with `test_uart_rxd_detect`.
5. If `GPIO7` toggles, check the ESP32-S3 USB console for `uart_websocket: From UART`.
6. If the UART driver sees bytes, connect a direct websocket client to `wss://192.168.4.1/ws`.
7. If the direct client receives banners, call the exact AEL helper `_capture_via_esp32jtag_web_uart(...)`.
8. Only after those layers pass, rerun `packs/uart_rp2040_s3jtag.json`.

## Canonical Commands

Probe SWD health:

```bash
arm-none-eabi-gdb -q \
  -ex 'target extended-remote 192.168.4.1:4242' \
  -ex 'monitor swd_scan' \
  -ex 'quit'
```

Run the firmware-side RX pin diagnostic:

```bash
curl -k -sS -u admin:admin -H 'Content-Type: application/json' \
  -d '{"test_type":"test_uart_rxd_detect"}' \
  https://192.168.4.1/test/start

curl -k -sS -u admin:admin https://192.168.4.1/test/result
```

Expected result shape:

```json
{"test":"test_uart_rxd_detect","result":"pass","pin":7,"state":"toggle"}
```

Check the ESP32-S3 USB console for decoded UART bytes:

```bash
stty -F /dev/ttyACM0 115200 raw -echo -echoe -echok -echoctl -echoke
timeout 12 cat /dev/ttyACM0
```

Direct websocket proof:

```python
import ssl, time, websocket
ws = websocket.create_connection(
    "wss://192.168.4.1/ws",
    timeout=5,
    sslopt={"cert_reqs": ssl.CERT_NONE},
)
ws.settimeout(1)
end = time.time() + 6
while time.time() < end:
    try:
        print(repr(ws.recv()))
    except Exception:
        pass
ws.close()
```

Exact AEL helper proof:

```python
from ael.adapters.observe_uart_log import _capture_via_esp32jtag_web_uart
print(_capture_via_esp32jtag_web_uart("https://192.168.4.1:443", 6.0, 0.0))
```

Formal pack:

```bash
python3 -m ael pack --pack packs/uart_rp2040_s3jtag.json
```

## Recovery Rules

If the host is no longer on the AP:
- run `nmcli connection up esp32jtag_0F91 ifname wlx90de80a53084`

If `192.168.4.1:4242` is down:
- check first for the ESP32-S3 first-boot `pc_cfg` bug or a bad firmware image
- do not start UART debugging until SWD health is restored

If the AP disappears entirely:
- inspect the ESP32-S3 USB console first
- if you see `BROWNOUT_RST` or `DOWNLOAD(USB/UART0)`, fix board power or boot state before touching AEL

If `bytes=0` but `GPIO7` toggles:
- move to the ESP32-S3 USB console and websocket bridge checks
- do not rework RP2040 firmware first

If the direct websocket client works but the formal pack does not:
- compare against the exact AEL helper call
- then inspect AEL run-time timing, preflight, and capture sequencing

## Non-Goals

This skill is not for:
- validating FPGA-backed capture
- proving analog signal integrity
- decoding arbitrary binary protocols
- replacing a proper UART analyzer for framing-quality work

## Success Criteria

This skill has succeeded when:
- the RP2040 image is flashed over SWD
- `GPIO7` raw sampling proves the signal reaches the ESP32-S3
- the ESP32-S3 USB console logs `From UART: len=23, data: AEL_READY RP2040 UART`
- a direct websocket client receives repeated `AEL_READY RP2040 UART\r\n`
- the AEL helper `_capture_via_esp32jtag_web_uart(...)` returns banner bytes
- the formal pack reaches `PASS: Run verified`

## Why This Was Easy To Miss

Each layer in the chain can fail with the same high-level symptom: "no UART text in the pack result".

The better rule is:
- debug outward from the pin, not inward from the pack verdict

That prevents burning time on the wrong layer when:
- the target is sending but the AP is gone
- the pin toggles but UART framing is not proven yet
- the UART driver sees bytes but the websocket session is not active
- the websocket bridge works but the automation is observing at the wrong moment

## Runtime Notes

AEL-side change required for the formal pack path:
- `610a3ab` `Unblock S3JTAG UART preflight and websocket capture`

Firmware-side supporting changes and diagnostics:
- `6af4936` `Fix first-boot gdb server defaults`
- `5a140ca` `Add UART RX GPIO diagnostic hook`
