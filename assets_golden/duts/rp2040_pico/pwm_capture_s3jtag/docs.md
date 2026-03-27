# pwm_capture_s3jtag

RP2040 PWM capture asset for the S3JTAG bench.

- flash/debug path: `S3JTAG` over SWD
- observe path: `TARGETIN` on the S3JTAG ESP32-S3 (`GPIO15`)
- required bench wire: `GPIO18/PWM_OUT` -> `TARGETIN`
- expected signal: steady PWM around `1 kHz` at `50%` duty
