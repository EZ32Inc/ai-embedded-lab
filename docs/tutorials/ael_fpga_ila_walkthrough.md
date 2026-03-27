# AEL FPGA ILA Walkthrough — PA35T StarLite LED Project

**Date:** 2026-03-27
**Board:** PA35T StarLite (Xilinx Artix-7 xc7a35tfgg484-2)
**Project path:** `/nvme1t/work/PA35T_StarLite/1_FPGA/3_3_PZ_LED`
**Tool:** Vivado 2021.1 (`/tools/Xilinx/Vivado/2021.1/bin/vivado`)

---

## Summary

Starting from an existing Vivado LED blink project, we completed a full AEL FPGA bring-up and verification workflow in three phases:

1. **AEL Command-Line Onboarding** — replaced Vivado GUI dependency with batch-mode `build.tcl` / `program.tcl` scripts so AEL can build and program without human interaction.

2. **External LA Probe Outputs** — added four physical output pins (`la_ch_in[3:0]`) carrying counter bits `cnt[4:1]` for measurement by ESP32JTAG logic analyzer and oscilloscope.

3. **Xilinx ILA Integration** — embedded an ILA debug core into the design, automated its insertion via `build.tcl`, captured 1024 samples over the Digilent USB JTAG cable with `ila_capture.tcl`, exported the waveform to CSV and VCD, and verified frequencies with `parse_ila_csv.py` / GTKWave.

**Key discovery:** The board input clock is **200 MHz** (`CLK_P_200M` on pin R4), not 100 MHz as originally commented. This caused all frequency analysis to report half the true values until corrected.

**Final verified frequencies (ILA + scope + ESP32JTAG all agree):**

| Signal | Net | Frequency |
|--------|-----|-----------|
| `la_ch_in[0]` / `ila_probe[0]` | `cnt[1]` | 50 MHz |
| `la_ch_in[1]` / `ila_probe[1]` | `cnt[2]` | 25 MHz |
| `la_ch_in[2]` / `ila_probe[2]` | `cnt[3]` | 12.5 MHz |
| `la_ch_in[3]` / `ila_probe[3]` | `cnt[4]` | 6.25 MHz |

---

## Phase 1 — AEL Brownfield Onboarding

### Starting Point

The project contained a working but GUI-only LED blink design:
- `LED.v` — blink two LEDs using a 32-bit free-running counter
- `XDC.xdc` — pin constraints for clock, reset, LEDs
- Pre-built bitstream in `Test_LED.runs/impl_1/LED.bit`

The Verilog originally had a hardcoded magic number `50_000_000` for the blink period with no way to change it from outside.

### Changes Made

**`LED.v` — Parameterize blink period**

```verilog
// Before
always@(posedge clk)
    if(cnt < 50_000_000 - 1) ...

// After
module LED #(
    parameter BLINK_PERIOD = 50_000_000  // clock cycles per LED step
)(
    ...
);
```

This makes the blink speed a one-line edit without hunting magic numbers.

**`build.tcl` — Full batch-mode build script (created)**

```
vivado -mode batch -nolog -nojournal -source build.tcl
```

Performs: `reset_run synth_1` → `launch_runs synth_1` → `wait_on_run` → progress check → `reset_run impl_1` → `launch_runs impl_1 -to_step write_bitstream` → `wait_on_run` → bitstream existence check. Exits with code 1 on any failure.

**`program.tcl` — Batch-mode JTAG programming script (created)**

```
vivado -mode batch -nolog -nojournal -source program.tcl
```

Opens `hw_manager` → `connect_hw_server -allow_non_jtag` → `get_hw_targets` → `open_hw_target` → sets `PROGRAM.FILE` → `program_hw_devices` → `refresh_hw_device`.

### Verification

Build and program confirmed working on hardware. AEL can now build and flash without GUI.

---

## Phase 2 — External LA Probe Outputs

### Goal

Expose counter bits as physical FPGA output pins so the ESP32JTAG logic analyzer (connected via JM1 connector) and an oscilloscope can independently verify signal frequencies.

### Changes Made

**`LED.v` — Add `la_ch_in` output port**

```verilog
output       [3:0]la_ch_in   // LA probe: cnt[4:1]

assign la_ch_in = cnt[4:1];
// [0]=cnt[1]=50MHz  [1]=cnt[2]=25MHz  [2]=cnt[3]=12.5MHz  [3]=cnt[4]=6.25MHz
```

**`XDC.xdc` — Pin constraints for JM1 connector**

```tcl
set_property -dict {PACKAGE_PIN F13 IOSTANDARD LVCMOS33} [get_ports {la_ch_in[0]}]
set_property -dict {PACKAGE_PIN F14 IOSTANDARD LVCMOS33} [get_ports {la_ch_in[1]}]
set_property -dict {PACKAGE_PIN D14 IOSTANDARD LVCMOS33} [get_ports {la_ch_in[2]}]
set_property -dict {PACKAGE_PIN D15 IOSTANDARD LVCMOS33} [get_ports {la_ch_in[3]}]
```

### Verification

ESP32JTAG logic analyzer and oscilloscope both confirmed the four frequencies on the JM1 pins.

---

## Phase 3 — Xilinx ILA Integration

### Goal

Capture the same signals (`cnt[4:1]`) internally using a Xilinx ILA (Integrated Logic Analyzer) core, retrieve the waveform over the existing Digilent USB JTAG cable, and produce both a frequency-verified CSV and a GTKWave-viewable VCD file — all automated, no GUI interaction required.

### Architecture

```
FPGA (xc7a35t)
├── LED.v
│   ├── cnt[31:0]  — free-running counter at 200 MHz
│   ├── la_ch_in[3:0] = cnt[4:1]  → JM1 physical pins → ESP32JTAG / scope
│   └── ila_probe[3:0] = cnt[4:1] — (* mark_debug = "true" *) → ILA core
│
└── u_ila  (ILA, 1024 samples)
    ├── clk  ← clk (IBUFDS output, 200 MHz)
    └── probe0[3:0] ← ila_probe[3:0]

Digilent USB JTAG cable ──── bitstream programming (program.tcl)
                        └─── ILA data retrieval   (ila_capture.tcl)
```

### Step 3a — Mark Debug Nets in Verilog

The `(* mark_debug = "true" *)` attribute tells Vivado synthesis to preserve these nets (prevents optimization away) and marks them for automatic ILA probe connection.

```verilog
// ILA internal probe — mirrors la_ch_in; mark_debug preserves nets through synthesis
(* mark_debug = "true" *) wire [3:0] ila_probe;
assign ila_probe = cnt[4:1];
```

### Step 3b — ILA Insertion in `build.tcl`

The ILA is inserted **after synthesis, before implementation**, using the post-synthesis netlist:

```tcl
puts "=== AEL BUILD: inserting ILA debug core ==="
open_run synth_1 -name synth_1

# Create ILA core — 1024 samples
create_debug_core u_ila ila
set_property C_DATA_DEPTH      1024  [get_debug_cores u_ila]
set_property C_TRIGIN_EN       false [get_debug_cores u_ila]
set_property C_TRIGOUT_EN      false [get_debug_cores u_ila]
set_property C_INPUT_PIPE_STAGES 0   [get_debug_cores u_ila]

# Connect clock
set_property port_width 1 [get_debug_ports u_ila/clk]
connect_debug_port u_ila/clk [get_nets clk]

# Connect all mark_debug nets to probe0
set probe_nets [lsort [get_nets -hierarchical -filter {MARK_DEBUG == 1}]]
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila/probe0]
set_property port_width [llength $probe_nets] [get_debug_ports u_ila/probe0]
connect_debug_port u_ila/probe0 $probe_nets

# IMPORTANT: save_design is required before implement_debug_core in Vivado 2021.1
save_design
implement_debug_core

# Write probes description file (needed by ila_capture.tcl and hw_manager)
set ltx [file join $script_dir debug_probes.ltx]
write_debug_probes -force $ltx

close_design
```

**Pitfall encountered and fixed:** `implement_debug_core` fails with `"Design needs to be saved"` unless `save_design` is called first. This is a Vivado 2021.1 requirement not clearly documented.

Implementation then runs normally: `reset_run impl_1` → `launch_runs impl_1 -to_step write_bitstream`.

### Step 3c — Programming with Probes File (`program.tcl`)

`program.tcl` was extended to load `debug_probes.ltx` before programming, so hw_manager associates probe names with the bitstream:

```tcl
set ltx [file join $script_dir debug_probes.ltx]
...
if {[file exists $ltx]} {
    set_property PROBES.FILE      $ltx $dev
    set_property FULL_PROBES.FILE $ltx $dev
}
program_hw_devices $dev
refresh_hw_device $dev
```

Vivado confirmed: `"Device xc7a35t programmed with a design that has 1 ILA core(s)."`

### Step 3d — ILA Capture (`ila_capture.tcl`)

**Critical design decision:** The FPGA board has only one JTAG interface — the USB-connected Digilent cable. This is used for **both** bitstream programming and ILA data retrieval. The ESP32JTAG device does support XVC (Xilinx Virtual Cable) protocol, but it is **not** connected to the FPGA JTAG chain; it is only used as an external logic analyzer via its P0/PA port. Using XVC to ESP32JTAG for ILA retrieval is incorrect.

**Correct approach — same `get_hw_targets` / `open_hw_target` as `program.tcl`:**

```tcl
connect_hw_server -allow_non_jtag

set targets [get_hw_targets]
open_hw_target [lindex $targets 0]
# → localhost:3121/xilinx_tcf/Digilent/210251020965
```

**Trigger configuration — Vivado 2021.1 specifics:**

Two properties that appear in tutorials are **read-only** in Vivado 2021.1 and must not be set:
- `CONTROL.TRIGGER_MODE` — read-only
- `CONTROL.CAPTURE_MODE` — read-only

Settable properties:
```tcl
set_property CONTROL.TRIGGER_POSITION 0 $ila

set probe0 [lindex [get_hw_probes -of_objects $ila] 0]
set_property TRIGGER_COMPARE_VALUE eq4'bXXXX $probe0  ;# don't-care = immediate trigger
```

**Wait for capture — Vivado 2021.1 specifics:**

`wait_on_hw_ila $ila -timeout 10` fails with `"hw_ila does not have a STATUS.STATE property"` in Vivado 2021.1. The ILA triggers immediately at position 0 with a don't-care pattern, so a fixed `after 2000` (2-second Tcl delay) is sufficient for 1024 samples at 200 MHz:

```tcl
run_hw_ila $ila
after 2000   ;# STATUS.STATE unavailable in Vivado 2021.1; 1024 samples @ 200 MHz = 5.12 µs

set ila_data [upload_hw_ila_data $ila]
write_hw_ila_data -csv_file $csv_out $ila_data
```

### Step 3e — CSV Analysis (`parse_ila_csv.py`)

**Vivado 2021.1 CSV format is different from older versions:**

```
Sample in Buffer,Sample in Window,TRIGGER,ila_probe[3:0]
Radix - UNSIGNED,UNSIGNED,UNSIGNED,HEX     ← metadata row (must be skipped)
0,0,1,7                                    ← hex bus value, not separate bit columns
1,1,0,8
...
```

The bus column `ila_probe[3:0]` contains a hex integer. Individual bit lanes are extracted by bit-masking:

```python
val = int(row[bus_col].strip(), 16)
for probe_idx in range(4):
    bits[probe_idx].append((val >> probe_idx) & 1)
```

Frequency calculation (rising edges only):
```python
def freq_from_rising_edges(rising_edges, total_samples, clock_hz):
    duration_s = total_samples / clock_hz
    return rising_edges / duration_s
```

### Step 3f — Clock Frequency Discovery (200 MHz, not 100 MHz)

**Symptom:** ILA reported 25/12.5/6.25/3.125 MHz. Oscilloscope and ESP32JTAG both reported 50/25/12.5/6.25 MHz — exactly **2× the ILA results**.

**Root cause investigation:**

The XDC file had no `create_clock` constraint specifying the input clock frequency. The Verilog comment said `100MHz`. However, the XDC debug hub line contained:
```tcl
set_property C_CLK_INPUT_FREQ_HZ 300000000 [get_debug_cores dbg_hub]
```
This hinted the assumed clock was not 100 MHz.

Checking the schematic confirmed: **pin R4 is labeled `CLK_P_200M`** — the board has a 200 MHz LVDS differential clock, not 100 MHz.

**Consequence:** All frequency calculations in `parse_ila_csv.py` and `csv_to_vcd.py` were using `CLOCK_HZ = 100_000_000`. Corrected to `200_000_000`.

**Verification after fix:** All four probes pass at 0.000% error:
```
ila_probe[0]: measured=50.0000 MHz  expected=50.0000 MHz  error=0.000%  [PASS]
ila_probe[1]: measured=25.0000 MHz  expected=25.0000 MHz  error=0.000%  [PASS]
ila_probe[2]: measured=12.5000 MHz  expected=12.5000 MHz  error=0.000%  [PASS]
ila_probe[3]: measured=6.2500 MHz  expected=6.2500 MHz  error=0.000%  [PASS]
=== OVERALL: PASS ===
```

Also corrected frequency comments in `LED.v` and `XDC.xdc`, and the `BLINK_PERIOD` comment (`200MHz -> 0.25s`, not `100MHz -> 0.5s`).

### Step 3g — GTKWave Waveform Viewer (`csv_to_vcd.py`)

For visual waveform inspection without Vivado GUI, a Python converter produces a VCD file viewable in GTKWave:

```bash
python3 csv_to_vcd.py ila_capture.csv ila_capture.vcd
gtkwave ila_capture.vcd
```

The VCD uses 1 ns timescale; at 200 MHz each sample = 5 ns. The converter handles the same Vivado 2021.1 bus format and Radix row as `parse_ila_csv.py`.

In GTKWave: expand `ila` in the SST panel → select all signals → Append → zoom to fit.

---

## File Summary

| File | Role |
|------|------|
| `Test_LED.srcs/sources_1/new/LED.v` | Top-level Verilog: counter, LED blink, `la_ch_in`, `ila_probe` |
| `Test_LED.srcs/constrs_1/new/XDC.xdc` | Pin constraints + ILA core definitions |
| `build.tcl` | Vivado batch build: synth → ILA insert → impl → bitstream |
| `program.tcl` | Vivado batch program: open hw_manager → load probes → flash |
| `ila_capture.tcl` | Vivado batch ILA capture: arm → wait → upload → CSV export |
| `debug_probes.ltx` | ILA probe descriptions (generated by `build.tcl`) |
| `parse_ila_csv.py` | Parse Vivado 2021.1 ILA CSV, verify frequencies, PASS/FAIL |
| `csv_to_vcd.py` | Convert ILA CSV → VCD for GTKWave |
| `ila_capture.csv` | Captured 1024-sample ILA data |
| `ila_capture.vcd` | GTKWave waveform (5 ns/sample) |

---

## Complete AEL Workflow (End-to-End)

```bash
# 1. Build (synth + ILA insert + impl + bitstream)
/tools/Xilinx/Vivado/2021.1/bin/vivado -mode batch -nolog -nojournal -source build.tcl

# 2. Program FPGA
/tools/Xilinx/Vivado/2021.1/bin/vivado -mode batch -nolog -nojournal -source program.tcl

# 3. Capture ILA waveform (1024 samples @ 200 MHz via Digilent USB JTAG)
/tools/Xilinx/Vivado/2021.1/bin/vivado -mode batch -nolog -nojournal -source ila_capture.tcl

# 4. Verify frequencies
python3 parse_ila_csv.py ila_capture.csv

# 5. View waveform in GTKWave
python3 csv_to_vcd.py ila_capture.csv ila_capture.vcd
gtkwave ila_capture.vcd &
```

---

## Lessons Learned / Pitfalls

| # | Issue | Fix |
|---|-------|-----|
| 1 | `implement_debug_core` fails: "Design needs to be saved" | Call `save_design` before `implement_debug_core` in Vivado 2021.1 |
| 2 | `CONTROL.TRIGGER_MODE` is read-only | Remove — do not set this property in Vivado 2021.1 |
| 3 | `wait_on_hw_ila` fails: `STATUS.STATE` not found | Replace with `after 2000`; ILA captures immediately at position 0 |
| 4 | ILA capture attempted via ESP32JTAG XVC | Wrong — ESP32JTAG XVC is not on the FPGA JTAG chain; use Digilent cable for everything |
| 5 | CSV parser: `WARNING: could not match probe column names` | Vivado 2021.1 exports a bus column `ila_probe[3:0]` (HEX) + Radix row, not per-bit columns |
| 6 | All frequencies exactly half of scope/ESP32JTAG readings | Board clock is 200 MHz (`CLK_P_200M` on R4), not 100 MHz; always verify clock from schematic |

---

## Hardware Reference

| Item | Value |
|------|-------|
| FPGA | Xilinx Artix-7 xc7a35tfgg484-2 |
| Board | PA35T StarLite |
| Input clock | 200 MHz differential LVDS (`CLK_P_200M`, pin R4 / T4) |
| Clock standard | DIFF_SSTL15 |
| JTAG cable | Digilent USB (S/N 210251020965) |
| LA probe connector | JM1 (F13, F14, D14, D15), LVCMOS33 |
| ILA depth | 1024 samples |
| ILA sample period | 5 ns (200 MHz) |
| Capture window | 5.12 µs |
