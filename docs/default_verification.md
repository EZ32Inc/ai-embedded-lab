# Default Verification Notes

Use default verification to run the baseline golden sequence:

```bash
python3 -m ael verify-default run
```

Expected sequence:

1. `esp32s3_golden_gpio`
2. `rp2040_golden_gpio_signature`

## Manual Hardware Smoke Checklist

Use this quick manual checklist after hardware/path changes:

1. Preflight-only smoke (probe + monitor + LA):

```bash
python3 -m ael verify-default set --preset preflight_only
python3 -m ael verify-default run
```

2. Full default sequence:

```bash
python3 -m ael verify-default set --preset esp32s3_then_rp2040
python3 -m ael verify-default run
```

## RP2040 Flash Warning

During RP2040 flash via BMDA/GDB, you may see log lines such as:

- `warning: Remote failure reply: E01`
- `Could not read registers; remote failure reply 'FF'`
- `Flash: warning - remote failure reply after load; skipping continue retry`

These are currently treated as non-fatal when load succeeds and downstream verify passes.
The run should be considered healthy if the final result is `PASS: Run verified`.
