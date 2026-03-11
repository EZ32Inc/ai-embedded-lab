# rp2350_pico2

Wiring expectations:
- SWD via ESP32JTAG P3
- Verify pin uses LA CH1 (P0.0)

Generation basis:
- official Pico SDK board support: `pico2`
- local AEL reference: `rp2040_pico`

Notes:
- Uses target-local firmware in `firmware/targets/rp2350_pico2/`.
- Validation is not claimed yet beyond structural generation until bench stages are run.
