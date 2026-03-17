# STLinkInstrument — Known Issues

## USB permission denied (Linux)

**Symptom:** `st-flash` or `st-info` fails with "LIBUSB_ERROR_ACCESS" or "Permission denied".

**Fix:** Install udev rules from the stlink source tree:
```bash
sudo cp instruments/STLinkInstrument/upstream/stlink/config/udev/rules.d/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```
Replug the ST-Link after applying rules.

---

## connect-under-reset required on some STM32 targets

**Symptom:** `st-flash` times out or fails to connect on targets with broken firmware or low-power modes.

**Fix:** Add `--connect-under-reset` flag:
```bash
st-flash --connect-under-reset write firmware.bin 0x08000000
```
Or set `EXTRA_ARGS="--connect-under-reset"` when calling `flash.sh`.

---

## st-util incompatible with some GDB versions

**Symptom:** arm-none-eabi-gdb hangs or reports protocol errors when connecting to st-util.

**Workaround:** Use `--multi` flag with st-util, or switch to OpenOCD as GDB server.
The AEL BMDA path (via ESP32JTAG) is unaffected by this.

---

## Submodule not initialised after clone

**Symptom:** `upstream/stlink/` directory is empty, build fails.

**Fix:**
```bash
git submodule update --init --recursive
```

---

## Multiple ST-Link devices connected

**Symptom:** st-flash writes to wrong target when multiple ST-Links are connected.

**Fix:** Use `--serial <serial>` flag to target a specific device.
Serial numbers visible via `st-info --probe`.
