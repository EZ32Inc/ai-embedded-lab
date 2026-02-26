# ai-embedded-lab

Run:

```bash
python orchestrator.py run --probe configs/esp32jtag.yaml --board configs/boards/rp2040_pico.yaml --wiring "swd=P3 reset=P2.0 verify=P0.1"
```

Logic Analyzer Verify (standalone):

```bash
python3 tools/la_verify.py --host 192.168.4.1 --user admin --password admin \
  --mode instant --window-s 0.2 --bit 1 --min-edges 4
```

Dry-run (no hardware):

```bash
python3 tools/la_verify.py --host 0.0.0.0 --dry-run
```
