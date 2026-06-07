# Security And Public-Repo Hygiene

Last updated: 2026-06-07

This project is intended to be usable as a public repository. AEL also works
with real hardware benches, local instruments, serial devices, and raw run
logs. Those details need deliberate handling before they are committed.

## What Must Not Be Published

Do not commit:

- credentials, API keys, private keys, certificates, or tokens
- Wi-Fi SSIDs or passwords
- raw interactive transcripts that include local bench details
- private hostnames or user names
- serial numbers when they identify a specific private device
- absolute local paths such as `/home/<user>/...` or `/nvme...`
- private LAN addresses when they identify a real local bench
- logs that include full environment dumps
- unreviewed generated reports from live hardware runs

## Values To Replace

Use placeholders when exact values are not essential:

| Real value type | Public replacement |
|---|---|
| Private bench IP | `<bench-host-ip>` or `<probe-ip>` |
| Serial device | `<serial-port>` |
| Absolute repo path | `<repo-root>` |
| User home path | `<user-home>` |
| USB serial number | `<usb-serial>` |
| Wi-Fi SSID | `<ssid>` |
| Token or key | Do not include it |

Examples:

```text
target extended-remote <probe-ip>:4242
idf.py -p <serial-port> flash
cd <repo-root>
```

## Raw Logs And Transcripts

Raw transcripts are high risk because they often include:

- private IP addresses
- local paths
- serial-port names
- pasted terminal output
- generated command lines
- user conversation fragments
- failed attempts that were never summarized

Policy:

1. Keep raw transcripts outside the public repo by default.
2. If the evidence matters, write a dated summary under `docs/reports/`.
3. Include only the minimal commands and observations needed to reproduce or
   understand the result.
4. Replace local values with placeholders.
5. Store the full transcript only outside public branches unless it has been
   explicitly sanitized.

`docs/reports/raw/` is reserved for reviewed raw material. It should normally
contain only a README on public branches.

## Hardware Bench Details

It is acceptable to document hardware topology when it is generic:

```text
ESP32JTAG probe exposes GDB on <probe-ip>:4242.
UART console is available on <serial-port> at 115200 baud.
```

It is not acceptable to publish unnecessary bench-specific details:

```text
ESP32JTAG probe at 192.168.x.x connected to my local Wi-Fi.
UART console is /dev/serial/by-id/usb-...
```

Use exact values only when they are public examples, not live private
infrastructure.

## Before Committing Docs

Run targeted checks before committing documentation:

```bash
rg -n "192\\.168\\.|10\\.|172\\.(1[6-9]|2[0-9]|3[0-1])\\." docs
rg -n "/home/|/nvme|/dev/tty(ACM|USB)[0-9]+|/dev/serial/by-id" docs
rg -n "BEGIN .*PRIVATE|PRIVATE KEY|password\\s*[:=]|secret\\s*[:=]|token\\s*[:=]|ssid\\s*[:=]" docs
git diff --check
```

Review every hit. Some hits are legitimate examples, but they should be
intentional and generic.

## Before Pushing Publicly

Use this checklist:

- `git status --short` is clean.
- New docs do not include real private IPs, local paths, serials, tokens, or
  raw transcript content.
- Large generated artifacts are not staged.
- `docs/README.md` and `docs/DOCS_INDEX.md` point to current entry points.
- Historical reports are clearly marked as historical evidence.
- Raw logs are summarized or removed.
- `git diff --check` passes.

## If Sensitive Data Was Committed

If a secret, token, private key, or credential was committed, do not only delete
it in a later commit. Treat it as compromised:

1. Rotate or revoke the credential.
2. Remove it from current files.
3. Decide whether repository history needs to be rewritten before public push.
4. Document the cleanup without repeating the sensitive value.

For non-secret local details such as private IPs or paths, normal follow-up
commits are usually sufficient before the branch is pushed publicly.
