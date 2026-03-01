# ESP32JTAG AI Usage Notes

## Safe defaults
- Use 5MHz logic capture unless test specifies otherwise
- Default threshold 1.6V

## Required sequence
- After flash → wait 300ms before UART observe

## Common failures
Flash sync fail:
→ retry once
→ then power cycle DUT

No logic edges:
→ extend capture
→ check threshold
→ verify wiring

## Safety
- Do not exceed 3.6V input
- Common ground required
