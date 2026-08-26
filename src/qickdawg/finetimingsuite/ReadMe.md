# Fine Timing Suite  
Sub-nanosecond control of MW/RF pulse sequences for NV center spin experiments (~200 ps resolution)

## Overview  
This folder contains fine-timing sequence scripts for high-resolution MW/RF pulse control in NV experiments. Timing is implemented via instruction-level offset calculations, enabling precise pulse placement without reinitialization between pulses, or changes to the FPGA gateware.

A companion notebook, `fine_timing_counting_demo.ipynb`, demonstrates practical usage for:
- PODMR  
- Rabi  
- CPMG-XY (used to implement Ramsey and Hahn Echo)  
- T1  

Within this framework:
- Ramsey → CPMG with **Nπ = 0**  
- Hahn Echo → CPMG with **Nπ = 1**  

Standalone Ramsey, Hahn Echo, and Counting Duration classes are also provided but are not covered in the notebook.

---

## Available Sequences  

| File Name | Purpose | Key Sweep | Notes |
|----------|---------|-----------|------|
| PODMR | Frequency-domain ODMR | MW frequency | — |
| Rabi | Pulse calibration | MW duration | — |
| Ramsey | T₂* dephasing time | τ | Also available via CPMG (Nπ = 0) |
| Hahn Echo | Spin echo decay | τ | Also available via CPMG (Nπ = 1) |
| CPMG-XY | Coherence & spectroscopy | τ (interpulse delay) | Primary reference implementation |
| T1 | Spin relaxation | MW–readout delay | — |
| Counting Duration | Readout timing | — | Sweep is performed externally (reinit required) |

---

## Sequence Conventions  

- CPMG-based Ramsey/Hahn Echo use the pulse pattern:  
  **−Y π/2 → (X π)\* → −Y π/2**

- τ is defined as the **delay from the end of one pulse to the start of the next**  
  (not center-to-center)

- The **CPMG-XY implementation is heavily commented** and serves as the best reference for:
  - Fine-timing mechanics  
  - Register-based pulse placement  
  - Extending to more complex sequences (e.g., phase cycling)

---

## Timing Resolution and Constraints  

- Fine timing resolution: **~200 ps** via `ftsamp` offsets  
- Minimum interpulse delay: **~50 ns or less**, determinable via an oscilloscope (based on the instruction overhead)

This lower bound depends on FPGA execution time and becomes relevant for long sequences when pulse positions are computed dynamically.

**Practical guidelines:**
- Most arithmetic/load instructions ≈ **1 FPGA cycle** (except multiply/divide)  
- Instructions may be buffered or executed early  
- `wait` stalls execution; `sync` does not  

These are approximate guidelines.

---

## Key Features  

- ~200 ps timing resolution  
- No pulse reinitialization (register-level control)  
- Shared readout via `ReadoutHelpers`  
- Optional MW-off normalization shots  

---

## Getting Started  

1. Open `fine_timing_counting_demo.ipynb`  
2. Start with PODMR, Rabi or Ramsey for basic usage  
3. See **cpmg_xy_fine_res.py** for in-depth comments

---

## Author  

Victor Marcenac  
📧 victorsm@uw.edu  

For questions, implementation details, or extensions, feel free to reach out.
