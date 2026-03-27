# AI-Driven FPGA Development with AEL

## 1. Introduction

This tutorial documents our first complete example of bringing a **Xilinx Vivado FPGA project** under **AEL (AI Embedded Lab)** management.  
The project itself is intentionally simple, but the result is important because it proves something much larger:

> **AEL can be used for real FPGA development, and it can close the full engineering loop.**

We started with a very small LED blink design. The point was not to build a sophisticated FPGA application on day one. The point was to validate the entire workflow:

1. AEL takes over an existing Vivado-managed project
2. Build and program the project from the command line without relying on the Vivado IDE
3. Modify the RTL source
4. Rebuild and reprogram the design
5. Verify that the external hardware behavior changes as expected
6. Move beyond visual inspection by using **ESP32JTAG** to capture FPGA output signals and verify them automatically

That is the core of this tutorial:

> **Moving from “the project can build and download” to “the project can be modified, rebuilt, reprogrammed, measured, and verified under AEL.”**

---

## 2. The key milestone: It works

The most important milestone in this tutorial can be summarized in two words:

> **It works.**

But here, “It works” has a very specific meaning. It means all three of the following steps succeeded.

### Step 1: AEL successfully onboarded the Vivado project
The first task we gave AEL was essentially this:

> We have a simple LED blink project managed by Vivado. Please move it under AEL management.

AEL quickly analyzed the project and successfully established:

- command-line build
- command-line bitstream programming
- JTAG connection and target detection

This proved that the FPGA brownfield project could already be driven by AEL rather than by the Vivado IDE.

### Step 2: AEL modified the RTL to make the LED blink at half speed
We did not stop at “build/program works.” Instead, we immediately gave AEL a small but real engineering task:

> Please reduce the LED blink frequency to half of its original speed so that I can see the difference with my eyes.

AEL located the relevant divider logic in the RTL, modified the source code, rebuilt the project, reprogrammed the FPGA, and the LED behavior changed exactly as expected.

This proved that:

- AEL is not only able to inspect the project
- AEL is not only able to program an existing bitstream
- AEL can make a real RTL change and produce a real hardware behavior change

### Step 3: Replace visual inspection with ESP32JTAG-based measurement
The final step was to upgrade verification from human observation to instrumentation:

- connect four FPGA output lines to ESP32JTAG
- let ESP32JTAG capture those signals
- let AEL analyze the captured data
- verify that the output frequencies and ratios match the design intent

AEL then completed:

- automatic capture
- automatic frequency calculation
- automatic divide-ratio checking
- automatic PASS/FAIL conclusion

At that point, the FPGA project had entered a real AEL engineering loop:

> **modify → build → program → capture → verify**

---

## 3. Project background

### 3.1 Project type
The example in this tutorial is a **Xilinx Vivado 2021 project** implementing a very simple function:

- a basic LED blink design
- after programming the FPGA board, LEDs blink periodically

### 3.2 Project path
The project path is:

```bash
/nvme1t/work/PA35T_StarLite/1_FPGA/3_3_PZ_LED
```

### 3.3 Target device
The target FPGA device is:

```text
xc7a35tfgg484-2
```

That is an **Artix-7 35T** device.

### 3.4 Toolchain
The toolchain used in this project includes:

- Vivado 2021.1
- a working JTAG programming path
- ESP32JTAG as the external capture instrument for verification

---

## 4. Tutorial objectives

This tutorial is organized around three levels of goals.

### Goal A: Bring an existing Vivado project under AEL control
In other words, onboard a brownfield FPGA project into AEL.

### Goal B: Let AEL modify the design and run it
Not just build/program, but actually edit the RTL, regenerate the bitstream, and run the updated design.

### Goal C: Let AEL verify the design automatically with instrumentation
Move beyond “it seems correct” and bring the FPGA project into a measurement-driven verification flow using ESP32JTAG.

---

## 5. Step 1: Bring the Vivado project under AEL management

### 5.1 The first prompt given to AEL
At the beginning, the request to AEL was essentially:

> We have an LED blink FPGA project managed by Vivado. Please move it under AEL management. Start from the command line rather than the IDE. Verify that it can build and download. Then we can modify the source, rebuild, reprogram, and check the result.

This is an excellent starting point because it focuses on the most important part of brownfield onboarding:

- do not rush into logic changes first
- first identify the engineering entry points
- first make sure AEL can drive build and program

### 5.2 What AEL did in this stage
At this stage, AEL completed the following tasks:

1. inspected the project directory structure
2. located the `.xpr` project file
3. identified top-level RTL and constraints
4. confirmed that the Vivado command-line tool was available
5. checked that the existing bitstream could be found
6. verified that the JTAG chain was working
7. created `build.tcl` and `program.tcl`

### 5.3 Why this stage matters
In many FPGA projects, the Vivado IDE hides a lot of the real flow.  
If AEL can only read the source code but cannot drive build and program, it cannot actually take control of the project.

So the real purpose of step one is not to understand the design in depth. The purpose is to establish the most important capability:

> **Make AEL the actual execution layer of the project.**

### 5.4 What counted as success in this stage
Success in this stage meant:

- `build.tcl` runs correctly
- `program.tcl` runs correctly
- the bitstream can be generated or reused
- the FPGA is correctly detected over JTAG
- the device can be programmed successfully
- the board LEDs start blinking as expected

Once these conditions are met, we can say:

> **AEL has successfully converted the project from IDE-driven to script-driven execution.**

---

## 6. Step 2: Let AEL modify the RTL and reduce the blink speed by half

### 6.1 Why this was the right second step
Once onboarding was successful, the easiest mistake would be to stop at “build/program PASS.”  
But the real engineering question is:

> Can AEL modify the design and make the real hardware behavior change in the expected way?

So the second task was deliberately chosen to be simple but meaningful:

> Reduce the LED blink speed to half of its original rate.

This is an ideal minimal closed-loop test because it has several advantages:

- the change point is clear
- the risk is low
- the design structure does not need large changes
- the result is easy to observe
- success or failure is easy to judge

### 6.2 How AEL completed the change
AEL read `LED.v` and identified that the blink behavior was controlled by a counter-based divider.  
To slow the blinking down by a factor of two, AEL doubled the relevant count thresholds.

In practical terms, what used to advance every 0.5 seconds now advanced every 1 second.

### 6.3 The full loop in this step
AEL completed the full loop here:

1. read the RTL source
2. identify the frequency control point
3. modify the count comparison values
4. rebuild the project
5. reprogram the FPGA
6. let the user visually confirm that the LED is now blinking at half speed

When the LED really blinks more slowly, this proves that AEL is doing more than calling the toolchain:

> **It is making a real RTL change and verifying the result on real hardware.**

### 6.4 Why this step matters
This step is critical because it moves the project from “manageable” to “iterable.”

In other words, AEL can now participate in the classic FPGA engineering loop:

- modify RTL
- build
- program
- inspect behavior
- modify again

That means AEL is no longer just an assistant around the project. It is participating in the actual development process.

---

## 7. Step 3: Use ESP32JTAG to capture FPGA outputs and verify them automatically

### 7.1 Why visual inspection was no longer enough
Watching an LED blink is a great first validation method, but it has obvious limitations:

- it only works for very low-frequency and highly visible behavior
- it does not measure frequency accurately
- it does not verify duty cycle
- it does not verify multi-channel relationships
- it does not support automatic PASS/FAIL decisions

So the natural third step was:

> Replace visual checking with instrumentation-driven verification using AEL + ESP32JTAG.

### 7.2 Physical connection
At this stage, four FPGA output signals were connected to ESP32JTAG inputs.  
This allowed ESP32JTAG to act as a lightweight external logic capture instrument.

The key idea here is:

> **Bring FPGA verification into the AEL measurement framework.**

### 7.3 What AEL did in this stage
AEL completed the following tasks:

1. created or updated the DUT asset
2. configured the relationship between the FPGA board and ESP32JTAG
3. created or updated the frequency verification script
4. captured data from four output channels
5. calculated each signal frequency automatically
6. measured duty cycle automatically
7. checked divide-ratio relationships automatically
8. produced a final PASS/FAIL conclusion

### 7.4 Real engineering issues encountered
This stage was not an idealized pure-math exercise. It was a real hardware measurement task, and AEL had to reason about two useful engineering effects.

#### Issue 1: systematic frequency offset
Measurements showed that all four channels had approximately the same frequency offset, around **0.56% to 0.59%**.  
AEL correctly identified that this was not a design bug. Instead, it was due to the systematic difference between:

- the FPGA oscillator
- and the ESP32JTAG reference clock

This is a normal real-world hardware effect and should not be misclassified as a logic failure.

#### Issue 2: duty-cycle quantization error at high frequency
For a 50 MHz signal, the available sampling rate only provides a limited number of samples per period.  
That means duty-cycle measurement becomes quantization-limited.

AEL adjusted the tolerances accordingly so that the verification remained realistic and trustworthy.

### 7.5 Final result
After applying reasonable tolerances, AEL completed all stages of the verification and produced:

```text
OVERALL: PASS
```

That means:

- frequency accuracy checks passed
- duty-cycle checks passed
- divide-ratio checks passed

### 7.6 Why this step matters
This is the most important upgrade in the entire tutorial, because it means AEL moved from:

- build/program capability

into:

- **measurement-backed verification**

In other words, AEL is no longer just “loading code and seeing whether the board lights up.” It can now:

- capture signals
- measure frequencies
- compare them to expectations
- produce quantitative conclusions

That is what brings FPGA projects into a real engineering quality-control loop.

---

## 8. Why this example matters

This is our first FPGA development example with AEL, and its importance goes far beyond a small LED blink design.

### 8.1 It proves that AEL can take over FPGA brownfield projects
This was not a brand-new project created just to showcase AI. It was an existing Vivado project.  
AEL successfully took it over, which proves the method is suitable for brownfield projects.

### 8.2 It proves that AEL can drive the full FPGA engineering loop
In this project, AEL did not just inspect the code. It completed:

- project discovery
- build
- program
- RTL modification
- instrument-based capture
- automatic verification

That is a complete engineering loop.

### 8.3 It proves that FPGA can be brought into the same AI engineering framework
Previously, AEL had been demonstrated mainly on MCU and ESP32 workflows.  
This tutorial now shows:

> **The AEL working model applies not only to MCUs, but also to FPGA development.**

What changes are the toolchain, the instrumentation, and the verification method. The core loop remains the same.

---

## 9. The standard AEL-driven FPGA workflow

Based on this example, we can now summarize a clear FPGA workflow template.

### 9.1 Phase 1: onboard the project
- identify the Vivado entry point
- confirm the toolchain version
- locate `.xpr`, RTL, and constraints
- identify the bitstream output path
- confirm JTAG connectivity

### 9.2 Phase 2: establish command-line flow
- create `build.tcl`
- create `program.tcl`
- test command-line build
- test command-line program

### 9.3 Phase 3: make a minimal visible change
- choose a simple observable function
- modify the RTL
- rebuild
- reprogram
- verify the behavior change

### 9.4 Phase 4: add instrumentation-based verification
- choose the signals to capture
- connect ESP32JTAG or another instrument
- capture waveform/frequency data
- analyze the data automatically
- report PASS/FAIL

### 9.5 Phase 5: form the long-term loop
- modify logic
- rebuild
- reprogram
- capture and verify
- record closeout results
- accumulate reusable skills and patterns

---

## 10. What this suggests for future FPGA projects

Even though this tutorial is based on a simple LED project, it already points toward a much wider roadmap.

A key observation from this work is that **AI becomes more valuable as FPGA projects grow more complex** — not less. Simple tasks are still easy for a human to finish manually. But large designs with many source files, long build loops, and interactions across subsystems are exactly where an AI-driven engineering loop creates disproportionate leverage.

The highest-priority directions identified for AEL FPGA development are:

1. **Add simulation to the loop** — integrate Verilator or Icarus Verilog, let AEL generate and refine testbenches, and compare simulation results against real hardware measurements.
2. **Add internal observability via Xilinx ILA / XVC** — move beyond board-level signal capture into internal FPGA signal visibility, using ESP32JTAG's XVC support as the transport.
3. **Teach AEL to read and act on timing, utilization, and DRC reports** — move from "timing passes" to active timing optimization, report-driven RTL changes, and floorplanning guidance.

Further directions include parameter sweeps for design-space exploration, CDC / reset topology review, and eventually a goal-driven agent that iterates until a target Fmax, area, or verification objective is met.

For the full roadmap and detailed discussion of each direction, see:
→ [AEL FPGA Roadmap Memo](ael_fpga_next_steps_memo_en.md)

In other words, LED blink is only the entry point, not the destination.

---

## 11. Core conclusions

The key conclusions from this work can be summarized as follows.

### Conclusion 1
AEL can successfully take over a Xilinx Vivado brownfield FPGA project.

### Conclusion 2
AEL can perform build and program from the command line without depending on the IDE.

### Conclusion 3
AEL can modify RTL and produce the expected behavior change on real hardware.

### Conclusion 4
AEL can use ESP32JTAG to capture FPGA outputs and verify them automatically.

### Conclusion 5
AEL now has a complete FPGA development loop:

> **inspect → modify → build → program → capture → verify**

That is the most important value of this tutorial.

---

## 12. Advice for your first AEL + FPGA attempt

If you want to reproduce this kind of workflow from scratch, the most practical approach is:

1. choose the simplest possible Vivado project
2. first establish command-line build/program
3. then make one minimal source change
4. first verify it visually or in the simplest possible way
5. then bring in instrumentation for automated verification
6. finally turn the flow into a reusable AEL skill

This is far more robust than jumping into a complex design immediately, and it helps build confidence quickly.

---

## 13. Closing remarks

This is our first complete FPGA development example under AEL.  
It starts from a very small LED blink project, but it represents a very large step:

> **AEL is not only able to help understand FPGA projects. It is already able to drive the real FPGA engineering loop.**

From here, the question is no longer whether this can be done. The real question is how far we can scale it, how many FPGA projects we can bring in, and how systematic we can make the workflow.

That is the real meaning of this tutorial.
